import { describe, expect, it } from "vitest";
import { formatUsd, maturityWall, startYear } from "@/lib/maturity";
import { mockDebate } from "@/lib/mock";
import type { DebtInstrument } from "@/lib/types";

const loan = (maturity_year: number, amount_usd: number, rate_type: DebtInstrument["rate_type"] = "fixed"): DebtInstrument => ({
  name: `Loan ${maturity_year}`,
  amount_usd,
  seniority: "senior_unsecured",
  rate_type,
  rate: "5%",
  maturity_year,
  source_id: "S1",
});

describe("startYear", () => {
  it("starts the year after the fiscal year in as_of", () => {
    expect(startYear("FY2025", [loan(2030, 1)])).toBe(2026);
    expect(startYear("2024-12-31", [loan(2030, 1)])).toBe(2025);
  });
  it("falls back to the earliest maturity", () => {
    expect(startYear("latest", [loan(2031, 1), loan(2029, 1)])).toBe(2029);
  });
});

describe("maturityWall", () => {
  it("returns null with no debt", () => {
    expect(maturityWall({ as_of: "FY2025", debt: [] })).toBeNull();
    expect(maturityWall({ as_of: "FY2025", debt: [loan(2028, 0)] })).toBeNull();
  });

  it("splits fixed and floating, and keeps empty years before the last maturity", () => {
    const wall = maturityWall(mockDebate.fact_sheet!)!;
    expect(wall.start_year).toBe(2026);
    expect(wall.buckets.map((b) => b.label)).toEqual(["2026", "2027", "2028", "2029", "2030"]);
    const y2029 = wall.buckets.find((b) => b.from === 2029)!;
    expect(y2029.floating_usd).toBe(700_000_000);
    expect(y2029.fixed_usd).toBe(0);
    expect(wall.total_usd).toBe(1_800_000_000);
    expect(wall.peak?.label).toBe("2029");
  });

  it("counts the first three years as near term", () => {
    const wall = maturityWall({ as_of: "FY2025", debt: [loan(2026, 100), loan(2028, 100), loan(2029, 200)] })!;
    expect(wall.near_term_usd).toBe(200);
    expect(wall.near_term_pct).toBe(50);
  });

  it("puts past-due debt in the first year", () => {
    const wall = maturityWall({ as_of: "FY2025", debt: [loan(2024, 50), loan(2027, 10)] })!;
    expect(wall.buckets[0]).toMatchObject({ from: 2026, total_usd: 50 });
  });

  it("groups maturities past ten years into five-year spans, dropping empty spans", () => {
    const wall = maturityWall({ as_of: "FY2025", debt: [loan(2033, 2), loan(2036, 1), loan(2039, 1), loan(2055, 3)] })!;
    const labels = wall.buckets.map((b) => b.label);
    expect(labels.slice(0, 10)).toEqual(Array.from({ length: 10 }, (_, i) => String(2026 + i)));
    expect(labels.slice(10)).toEqual(["2036–40", "2051–55"]);
    expect(wall.buckets.find((b) => b.label === "2036–40")!.total_usd).toBe(2);
    expect(wall.buckets.find((b) => b.label === "2036–40")!.instruments).toHaveLength(2);
  });

  it("sorts each bar's instruments biggest first", () => {
    const wall = maturityWall({ as_of: "FY2025", debt: [loan(2027, 10), loan(2027, 30, "floating")] })!;
    expect(wall.buckets[1].instruments.map((d) => d.amount_usd)).toEqual([30, 10]);
  });
});

describe("formatUsd", () => {
  it("matches the metric card style", () => {
    expect(formatUsd(1_600_000_000)).toBe("$1.6B");
    expect(formatUsd(416_000_000)).toBe("$416M");
    expect(formatUsd(25_000)).toBe("$25K");
  });
});
