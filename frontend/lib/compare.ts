import type { FactSheet, Metric } from "./types";

/**
 * Which way each metric reads as a stronger credit, from a lender's point of view.
 * Metrics left out (liquidity in dollars, say) aren't comparable across companies of
 * different sizes, so neither side is marked.
 */
export const STRONGER: Record<string, { dir: "lower" | "higher"; why: string }> = {
  leverage: { dir: "lower", why: "Less debt for each dollar of earnings" },
  interest_coverage: { dir: "higher", why: "More earnings to cover each dollar of interest" },
  floating_rate_pct: { dir: "lower", why: "Less of the debt reprices when rates rise" },
  next_maturity_year: { dir: "higher", why: "More time before a big refinancing" },
  capex_to_cash_flow: { dir: "lower", why: "More operating cash left after capital spending" },
};

export interface MetricRow {
  name: string;
  label: string;
  a?: Metric;
  b?: Metric;
  /** The side whose number reads as the stronger credit; null when equal, missing or not comparable. */
  stronger: "a" | "b" | null;
  why?: string;
}

/**
 * The two fact sheets' metrics lined up by name, in the first sheet's order, then any
 * metric only the second sheet has. Comparing is done here in code, not by the AI.
 */
export function compareMetrics(a: FactSheet | null, b: FactSheet | null): MetricRow[] {
  const am = a?.metrics ?? [];
  const bm = b?.metrics ?? [];
  const names = [...am.map((m) => m.name), ...bm.map((m) => m.name).filter((n) => !am.some((m) => m.name === n))];

  return names.map((name) => {
    const ma = am.find((m) => m.name === name);
    const mb = bm.find((m) => m.name === name);
    const rule = STRONGER[name];
    let stronger: MetricRow["stronger"] = null;
    if (rule && ma && mb && ma.unit === mb.unit && ma.value !== mb.value) {
      const aWins = rule.dir === "lower" ? ma.value < mb.value : ma.value > mb.value;
      stronger = aWins ? "a" : "b";
    }
    return { name, label: (ma ?? mb)!.label, a: ma, b: mb, stronger, why: rule?.why };
  });
}

/** The /compare link for two debates. */
export const compareHref = (a: string, b: string) => `/compare?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`;
