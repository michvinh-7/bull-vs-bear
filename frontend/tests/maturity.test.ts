import { describe, expect, it } from "vitest";
import { formatUsd, maturityWall, startYear } from "@/lib/maturity";
import { mockDebate } from "@/lib/mock";
import type { DebtInstrument, FactSheet } from "@/lib/types";

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

describe("maturityWall with a maturity schedule", () => {
  // Verizon FY2025: the debt table lists $16.5B of long-dated notes, the schedule all $155.9B
  const vz = {
    as_of: "FY2025",
    debt: [loan(2033, 2_000e6), loan(2055, 3_250e6), loan(2036, 2_250e6, "floating")],
    maturities: [
      { year: 2026, amount_usd: 17_267e6 },
      { year: 2027, amount_usd: 9_569e6 },
      { year: 2028, amount_usd: 13_032e6 },
      { year: 2029, amount_usd: 8_115e6 },
      { year: 2030, amount_usd: 11_081e6 },
    ],
    maturities_thereafter_usd: 96_753e6,
  };

  it("takes bar heights from the schedule, so 2026 isn't empty", () => {
    const wall = maturityWall(vz)!;
    expect(wall.from_schedule).toBe(true);
    expect(wall.buckets.map((b) => b.label)).toEqual(["2026", "2027", "2028", "2029", "2030", "2031+"]);
    expect(wall.buckets[0]).toMatchObject({ total_usd: 17_267e6, unlisted_usd: 17_267e6, instruments: [] });
  });

  it("is complete with a thereafter amount, and adds up to all the debt", () => {
    const wall = maturityWall(vz)!;
    expect(wall.complete).toBe(true);
    expect(wall.total_usd).toBe(155_817e6);
    expect(wall.near_term_usd).toBe(17_267e6 + 9_569e6 + 13_032e6);
  });

  it("splits the thereafter bar with the instruments due after the schedule", () => {
    const later = maturityWall(vz)!.buckets.at(-1)!;
    expect(later).toMatchObject({ thereafter: true, total_usd: 96_753e6, fixed_usd: 5_250e6, floating_usd: 2_250e6 });
    expect(later.unlisted_usd).toBe(96_753e6 - 7_500e6);
    expect(later.instruments.map((d) => d.amount_usd)).toEqual([3_250e6, 2_250e6, 2_000e6]);
  });

  it("never names the thereafter bar as the peak year", () => {
    expect(maturityWall(vz)!.peak?.label).toBe("2026");
  });

  it("puts instruments due in a schedule year into that year's split", () => {
    const wall = maturityWall({ ...vz, debt: [loan(2027, 1_000e6, "floating")] })!;
    expect(wall.buckets[1]).toMatchObject({ floating_usd: 1_000e6, unlisted_usd: 8_569e6, total_usd: 9_569e6 });
  });

  it("drops a zero thereafter bar and is still complete", () => {
    const wall = maturityWall({ ...vz, debt: [], maturities_thereafter_usd: 0 })!;
    expect(wall.buckets.map((b) => b.label)).toEqual(["2026", "2027", "2028", "2029", "2030"]);
    expect(wall.complete).toBe(true);
  });

  it("without a thereafter amount, later years are only the listed instruments and it isn't complete", () => {
    const wall = maturityWall({ ...vz, maturities_thereafter_usd: null })!;
    expect(wall.complete).toBe(false);
    expect(wall.buckets.at(-1)).toMatchObject({ thereafter: true, total_usd: 7_500e6, unlisted_usd: 0 });
  });

  it("fills years missing from the schedule with nothing due", () => {
    const wall = maturityWall({ as_of: "FY2025", debt: [], maturities: [{ year: 2027, amount_usd: 50 }, { year: 2029, amount_usd: 1_500 }] })!;
    expect(wall.buckets.map((b) => [b.label, b.total_usd])).toEqual([["2026", 0], ["2027", 50], ["2028", 0], ["2029", 1_500]]);
  });

  it("falls back to the debt table when the schedule is empty or all zero", () => {
    expect(maturityWall({ ...vz, maturities: [] })!.from_schedule).toBe(false);
    expect(maturityWall({ ...vz, maturities: [{ year: 2026, amount_usd: 0 }] })!.from_schedule).toBe(false);
  });

  it("uses the schedule in the VZ demo", async () => {
    const demo = (await import("../public/demo/VZ/debate.json")).default as { fact_sheet: FactSheet };
    const wall = maturityWall(demo.fact_sheet)!;
    expect(wall.buckets[0]).toMatchObject({ label: "2026", total_usd: 17_267e6 });
    expect(wall.complete).toBe(true);
  });
});

describe("formatUsd", () => {
  it("matches the metric card style", () => {
    expect(formatUsd(1_600_000_000)).toBe("$1.6B");
    expect(formatUsd(416_000_000)).toBe("$416M");
    expect(formatUsd(25_000)).toBe("$25K");
  });
});
