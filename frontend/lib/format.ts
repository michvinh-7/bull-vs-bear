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
