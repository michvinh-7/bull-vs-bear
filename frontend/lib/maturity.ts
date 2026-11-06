import type { DebtInstrument, FactSheet } from "./types";

/** One bar of the maturity wall: a single year, or a span of later years grouped together. */
export interface MaturityBucket {
  label: string; // "2028" or "2035–39"
  from: number;
  to: number;
  fixed_usd: number;
  floating_usd: number;
  total_usd: number;
  instruments: DebtInstrument[];
}

export interface MaturityWall {
  buckets: MaturityBucket[];
  total_usd: number;
  start_year: number;
  /** Debt due in the first three years (start_year through start_year + 2). */
  near_term_usd: number;
  near_term_pct: number;
  /** The year with the most debt due, i.e. the top of the wall. */
  peak: MaturityBucket | null;
}

/** Years shown one by one before later maturities are grouped into five-year spans. */
export const YEARLY_SPAN = 10;
const GROUP_SPAN = 5;
const NEAR_TERM_YEARS = 3;

/**
 * The first year that can still come due. "FY2025" means the filing covers 2025,
 * so the wall starts in 2026. Falls back to the earliest maturity when as_of has no year.
 */
export function startYear(asOf: string, debt: DebtInstrument[]): number {
  const m = asOf.match(/(19|20)\d{2}/);
  if (m) return Number(m[0]) + 1;
  return Math.min(...debt.map((d) => d.maturity_year));
}

/**
 * Groups a fact sheet's debt by the year it comes due. Every year in the first ten is shown,
 * empty ones included, because a gap before a big year is part of the story. Later maturities
 * are grouped into five-year spans, and only spans with debt in them are kept.
 * Anything already past due is counted in the first year.
 */
export function maturityWall(sheet: Pick<FactSheet, "as_of" | "debt">): MaturityWall | null {
  const debt = sheet.debt.filter((d) => d.amount_usd > 0);
  if (debt.length === 0) return null;

  const start = startYear(sheet.as_of, debt);
  const yearlyEnd = start + YEARLY_SPAN - 1;
  const buckets = new Map<number, MaturityBucket>();

  const bucketFor = (year: number): MaturityBucket => {
    const y = Math.max(year, start);
    const from = y <= yearlyEnd ? y : yearlyEnd + 1 + Math.floor((y - yearlyEnd - 1) / GROUP_SPAN) * GROUP_SPAN;
    const to = from <= yearlyEnd ? from : from + GROUP_SPAN - 1;
    let b = buckets.get(from);
    if (!b) {
      const label = from === to ? String(from) : `${from}–${String(to).slice(-2)}`;
      b = { label, from, to, fixed_usd: 0, floating_usd: 0, total_usd: 0, instruments: [] };
      buckets.set(from, b);
    }
    return b;
  };

  const last = Math.max(...debt.map((d) => d.maturity_year));
  for (let y = start; y <= Math.min(yearlyEnd, Math.max(last, start)); y++) bucketFor(y);

  for (const d of debt) {
    const b = bucketFor(d.maturity_year);
    if (d.rate_type === "floating") b.floating_usd += d.amount_usd;
    else b.fixed_usd += d.amount_usd;
    b.total_usd += d.amount_usd;
    b.instruments.push(d);
  }

  const sorted = [...buckets.values()].sort((a, b) => a.from - b.from);
  for (const b of sorted) b.instruments.sort((a, c) => c.amount_usd - a.amount_usd);

  const total = debt.reduce((s, d) => s + d.amount_usd, 0);
  const nearTerm = debt
    .filter((d) => d.maturity_year < start + NEAR_TERM_YEARS)
    .reduce((s, d) => s + d.amount_usd, 0);
  const peak = sorted.reduce<MaturityBucket | null>((p, b) => (!p || b.total_usd > p.total_usd ? b : p), null);

  return {
    buckets: sorted,
    total_usd: total,
    start_year: start,
    near_term_usd: nearTerm,
    near_term_pct: (nearTerm / total) * 100,
    peak,
  };
}

/** "$416M", "$1.6B": the same style as the metric cards. */
export function formatUsd(v: number): string {
  if (v >= 1e9) return `$${(v / 1e9).toFixed(1)}B`;
  if (v >= 1e6) return `$${Math.round(v / 1e6)}M`;
  return `$${Math.round(v / 1e3)}K`;
}
