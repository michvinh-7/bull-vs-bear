import { describe, expect, it } from "vitest";
import { findSource, formatMetric, metricsMentioned } from "@/lib/format";
import { mockDebate } from "@/lib/mock";
import type { Metric } from "@/lib/types";

const sheet = mockDebate.fact_sheet!;
const metric = (unit: Metric["unit"], value: number): Metric => ({ name: "m", label: "M", value, unit, formula: "", source_ids: [] });

describe("formatMetric", () => {
  it("formats each unit", () => {
    expect(formatMetric(metric("x", 5.8))).toBe("5.8x");
    expect(formatMetric(metric("x", 2))).toBe("2.0x");
    expect(formatMetric(metric("pct", 61.6))).toBe("62%");
    expect(formatMetric(metric("year", 2028))).toBe("2028");
  });
  it("shows millions below a billion, billions above", () => {
    expect(formatMetric(metric("usd", 410_000_000))).toBe("$410M");
    expect(formatMetric(metric("usd", 1_800_000_000))).toBe("$1.8B");
  });
});

describe("findSource", () => {
  it("finds a source by id", () => {
    expect(findSource(sheet, "S3")?.label).toBe("10-Q · Liquidity, p. 31");
  });
  it("returns undefined for a missing, unknown, or null id", () => {
    expect(findSource(sheet, null)).toBeUndefined();
    expect(findSource(sheet, "S99")).toBeUndefined();
    expect(findSource(null, "S3")).toBeUndefined();
  });
});

describe("metricsMentioned", () => {
  const lit = (text: string) => [...metricsMentioned(sheet.metrics, text)].sort();

  it("lights the right cards for each mock line", () => {
    const [bull1, bear2, mod3, bull4] = mockDebate.lines;
    expect(lit(bull1.text)).toEqual(["leverage"]);
    expect(lit(bear2.text)).toEqual(["floating_rate_pct", "interest_coverage"]);
    expect(lit(mod3.text)).toEqual([]);
    expect(lit(bull4.text)).toEqual([]); // "covered" is not "coverage"
  });
  it("matches a metric by its displayed value", () => {
    expect(lit("Liquidity aside, $410M is thin")).toContain("liquidity_usd");
    expect(lit("we sit at 5.8x")).toEqual(["leverage"]);
  });
  it("is case-insensitive", () => {
    expect(lit("LEVERAGE is fine")).toEqual(["leverage"]);
  });
  it("falls back to the label for metrics it doesn't know", () => {
    const extra: Metric = { name: "capex_ratio", label: "Capex ratio", value: 0.4, unit: "x", formula: "", source_ids: [] };
    expect([...metricsMentioned([extra], "The capex ratio is rising")]).toEqual(["capex_ratio"]);
  });
});
