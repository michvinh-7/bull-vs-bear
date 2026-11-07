import { describe, expect, it } from "vitest";
import { compareHref, compareMetrics } from "@/lib/compare";
import type { FactSheet, Metric } from "@/lib/types";

const metric = (name: string, value: number, unit: Metric["unit"] = "x"): Metric => ({
  name,
  label: name.toUpperCase(),
  value,
  unit,
  formula: "",
  source_ids: [],
});
const sheet = (metrics: Metric[]): FactSheet => ({ company: "C", ticker: "C", as_of: "FY2025", sources: [], metrics, debt: [] });

describe("compareMetrics", () => {
  it("marks lower leverage and higher coverage as stronger", () => {
    const rows = compareMetrics(
      sheet([metric("leverage", 3.3), metric("interest_coverage", 7.1)]),
      sheet([metric("leverage", 13.6), metric("interest_coverage", 0.64)]),
    );
    expect(rows.map((r) => [r.name, r.stronger])).toEqual([
      ["leverage", "a"],
      ["interest_coverage", "a"],
    ]);
  });

  it("marks a later next maturity and less floating debt as stronger", () => {
    const rows = compareMetrics(
      sheet([metric("next_maturity_year", 2026, "year"), metric("floating_rate_pct", 21, "pct")]),
      sheet([metric("next_maturity_year", 2027, "year"), metric("floating_rate_pct", 49.9, "pct")]),
    );
    expect(rows.map((r) => r.stronger)).toEqual(["b", "a"]);
  });

  it("marks neither side for ties, dollar amounts, or a metric only one side has", () => {
    const rows = compareMetrics(
      sheet([metric("leverage", 2), metric("liquidity_usd", 3e10, "usd"), metric("capex_to_cash_flow", 40, "pct")]),
      sheet([metric("leverage", 2), metric("liquidity_usd", 4e8, "usd")]),
    );
    expect(rows.map((r) => [r.name, r.stronger])).toEqual([
      ["leverage", null],
      ["liquidity_usd", null],
      ["capex_to_cash_flow", null],
    ]);
    expect(rows[2].b).toBeUndefined();
  });

  it("keeps the first sheet's order and adds the second sheet's extra metrics at the end", () => {
    const rows = compareMetrics(sheet([metric("b_metric", 1), metric("a_metric", 1)]), sheet([metric("c_metric", 1), metric("a_metric", 2)]));
    expect(rows.map((r) => r.name)).toEqual(["b_metric", "a_metric", "c_metric"]);
    expect(rows[2]).toMatchObject({ label: "C_METRIC", a: undefined });
  });

  it("handles a missing fact sheet", () => {
    expect(compareMetrics(null, sheet([metric("leverage", 1)]))).toHaveLength(1);
    expect(compareMetrics(null, null)).toEqual([]);
  });
});

describe("compareHref", () => {
  it("links both debates", () => {
    expect(compareHref("demo-VZ", "abc 1")).toBe("/compare?a=demo-VZ&b=abc%201");
  });
});
