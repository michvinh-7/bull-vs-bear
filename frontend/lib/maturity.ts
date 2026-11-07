import type { DebtInstrument, FactSheet } from "./types";

/** One bar of the maturity wall: a single year, or a span of later years grouped together. */
export interface MaturityBucket {
  label: string; // "2028", "2035–39", or "2031+" for the schedule's "thereafter"
  from: number;
  to: number; // Infinity for "thereafter"
  /** Fixed and floating come from the debt table's instruments, so they can add up to less than the bar. */
  fixed_usd: number;
  floating_usd: number;
  /** Due that year per the maturity schedule but not among the instruments in the debt table. */
  unlisted_usd: number;
  total_usd: number;
  instruments: DebtInstrument[];
  /** Everything after the schedule's last year, lumped together; may be spread over decades. */
  thereafter: boolean;
}

export interface MaturityWall {
  buckets: MaturityBucket[];
  total_usd: number;
  /** Bar heights come from the 10-K's maturity schedule rather than the debt table alone. */
  from_schedule: boolean;
  /** The bars add up to all of the company's debt, not only the instruments listed. */
  complete: boolean;
  start_year: number;
  /** Debt due in the first three years (start_year through start_year + 2). */
  near_term_usd: number;
  near_term_pct: number;
  /** The year with the most debt due, i.e. the top of the wall. Never the "thereafter" bucket. */
  peak: MaturityBucket | null;
  /** Instruments in the debt table, the ones the fixed/floating split comes from. */
  instrument_count: number;
}

/** Years shown one by one before later maturities are grouped into five-year spans. */
export const YEARLY_SPAN = 10;
const GROUP_SPAN = 5;
const NEAR_TERM_YEARS = 3;

type WallSheet = Pick<FactSheet, "as_of" | "debt"> &
  Partial<Pick<FactSheet, "maturities" | "maturities_thereafter_usd">>;

/**
 * The first year that can still come due. "FY2025" means the filing covers 2025,
 * so the wall starts in 2026. Falls back to the earliest maturity when as_of has no year.
 */
export function startYear(asOf: string, years: number[] | DebtInstrument[]): number {
  const m = asOf.match(/(19|20)\d{2}/);
  if (m) return Number(m[0]) + 1;
  return Math.min(...years.map((y) => (typeof y === "number" ? y : y.maturity_year)));
}

const emptyBucket = (label: string, from: number, to: number, thereafter = false): MaturityBucket => ({
  label,
  from,
  to,
  fixed_usd: 0,
  floating_usd: 0,
  unlisted_usd: 0,
  total_usd: 0,
  instruments: [],
  thereafter,
});

const addInstrument = (b: MaturityBucket, d: DebtInstrument) => {
  if (d.rate_type === "floating") b.floating_usd += d.amount_usd;
  else b.fixed_usd += d.amount_usd;
  b.instruments.push(d);
};

/**
 * Groups a fact sheet's debt by the year it comes due.
 *
 * With a maturity schedule (`maturities`), each year's bar is the schedule's amount, which
 * covers all the debt; the debt table's instruments only split it into fixed and floating,
 * and whatever the instruments don't cover is "unlisted". Everything after the schedule's
 * last year is one "thereafter" bar.
 *
 * Without one, bars are built from the instruments alone: every year in the first ten is
 * shown, empty ones included, because a gap before a big year is part of the story. Later
 * maturities are grouped into five-year spans, and only spans with debt in them are kept.
 *
 * Either way, anything already past due is counted in the first year.
 */
export function maturityWall(sheet: WallSheet): MaturityWall | null {
  const debt = sheet.debt.filter((d) => d.amount_usd > 0);
  const schedule = (sheet.maturities ?? []).filter((m) => m.amount_usd >= 0);
  if (schedule.some((m) => m.amount_usd > 0)) return fromSchedule(sheet, schedule, debt);
  if (debt.length === 0) return null;
  return fromInstruments(sheet.as_of, debt);
}

function fromSchedule(sheet: WallSheet, schedule: { year: number; amount_usd: number }[], debt: DebtInstrument[]): MaturityWall {
  const start = startYear(sheet.as_of, schedule.map((m) => m.year));
  const last = Math.max(start, ...schedule.map((m) => m.year));
  const thereafterUsd = sheet.maturities_thereafter_usd;
  const complete = thereafterUsd != null;

  const years: MaturityBucket[] = [];
  for (let y = start; y <= last; y++) years.push(emptyBucket(String(y), y, y));
  // past-due rows (a schedule rarely has them) go in the first year, like past-due instruments
  for (const m of schedule) years[Math.max(m.year, start) - start].total_usd += m.amount_usd;

  const later = emptyBucket(`${last + 1}+`, last + 1, Infinity, true);
  for (const d of debt) addInstrument(d.maturity_year > last ? later : years[Math.max(d.maturity_year, start) - start], d);
  // without a "thereafter" amount, the listed instruments are all we know about later years
  later.total_usd = complete ? thereafterUsd : later.fixed_usd + later.floating_usd;

  const buckets = later.total_usd > 0 ? [...years, later] : years;
  for (const b of buckets) {
    b.unlisted_usd = Math.max(0, b.total_usd - b.fixed_usd - b.floating_usd);
    b.instruments.sort((a, c) => c.amount_usd - a.amount_usd);
  }

  const total = buckets.reduce((s, b) => s + b.total_usd, 0);
  const nearTerm = years.filter((b) => b.from < start + NEAR_TERM_YEARS).reduce((s, b) => s + b.total_usd, 0);
  return {
    buckets,
    total_usd: total,
    from_schedule: true,
    complete,
    start_year: start,
    near_term_usd: nearTerm,
    near_term_pct: total > 0 ? (nearTerm / total) * 100 : 0,
    peak: peakOf(years),
    instrument_count: debt.length,
  };
}

function fromInstruments(asOf: string, debt: DebtInstrument[]): MaturityWall {
  const start = startYear(asOf, debt);
  const yearlyEnd = start + YEARLY_SPAN - 1;
  const buckets = new Map<number, MaturityBucket>();

  const bucketFor = (year: number): MaturityBucket => {
    const y = Math.max(year, start);
    const from = y <= yearlyEnd ? y : yearlyEnd + 1 + Math.floor((y - yearlyEnd - 1) / GROUP_SPAN) * GROUP_SPAN;
    const to = from <= yearlyEnd ? from : from + GROUP_SPAN - 1;
    let b = buckets.get(from);
    if (!b) {
      b = emptyBucket(from === to ? String(from) : `${from}–${String(to).slice(-2)}`, from, to);
      buckets.set(from, b);
    }
    return b;
  };

  const last = Math.max(...debt.map((d) => d.maturity_year));
  for (let y = start; y <= Math.min(yearlyEnd, Math.max(last, start)); y++) bucketFor(y);

  for (const d of debt) {
    const b = bucketFor(d.maturity_year);
    addInstrument(b, d);
    b.total_usd += d.amount_usd;
  }

  const sorted = [...buckets.values()].sort((a, b) => a.from - b.from);
  for (const b of sorted) b.instruments.sort((a, c) => c.amount_usd - a.amount_usd);

  const total = debt.reduce((s, d) => s + d.amount_usd, 0);
  const nearTerm = debt
    .filter((d) => d.maturity_year < start + NEAR_TERM_YEARS)
    .reduce((s, d) => s + d.amount_usd, 0);

  return {
    buckets: sorted,
    total_usd: total,
    from_schedule: false,
    complete: false,
    start_year: start,
    near_term_usd: nearTerm,
    near_term_pct: (nearTerm / total) * 100,
    peak: peakOf(sorted),
    instrument_count: debt.length,
  };
}

function peakOf(buckets: MaturityBucket[]): MaturityBucket | null {
  return buckets.reduce<MaturityBucket | null>((p, b) => (b.total_usd > 0 && (!p || b.total_usd > p.total_usd) ? b : p), null);
}

/** "$416M", "$1.6B": the same style as the metric cards. */
export function formatUsd(v: number): string {
  if (v >= 1e9) return `$${(v / 1e9).toFixed(1)}B`;
  if (v >= 1e6) return `$${Math.round(v / 1e6)}M`;
  return `$${Math.round(v / 1e3)}K`;
}
