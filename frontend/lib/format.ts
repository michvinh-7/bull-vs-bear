import type { FactSheet, Metric } from "./types";

export function formatMetric(m: Metric): string {
  switch (m.unit) {
    case "x":
      return `${m.value.toFixed(1)}x`;
    case "pct":
      return `${Math.round(m.value)}%`;
    case "usd":
      return m.value >= 1e9 ? `$${(m.value / 1e9).toFixed(1)}B` : `$${Math.round(m.value / 1e6)}M`;
    case "year":
      return String(m.value);
  }
}

export function findSource(sheet: FactSheet | null, id: string | null) {
  return id ? sheet?.sources.find((s) => s.id === id) : undefined;
}

// Words that mean a line is talking about a metric. Keyed by Metric.name;
// unknown metrics fall back to their own label.
const METRIC_WORDS: Record<string, string[]> = {
  leverage: ["leverage", "debt to ebitda", "debt-to-ebitda", "turns of"],
  interest_coverage: ["coverage", "interest burden"],
  floating_rate_pct: ["float", "variable rate", "variable-rate", "rate shock", " bp "],
  next_maturity_year: ["maturit", "matures", "comes due", "refinanc"],
  liquidity_usd: ["liquidity", "cash", "revolver", "runway"],
};

/** Which metrics a line refers to, so their cards can light up while it's spoken. */
export function metricsMentioned(metrics: Metric[], text: string): Set<string> {
  const t = ` ${text.toLowerCase()} `;
  return new Set(
    metrics
      .filter((m) => {
        const words = METRIC_WORDS[m.name] ?? [m.label.toLowerCase()];
        return words.some((w) => t.includes(w)) || t.includes(formatMetric(m).toLowerCase());
      })
      .map((m) => m.name),
  );
}
