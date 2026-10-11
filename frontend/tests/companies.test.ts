import { afterEach, describe, expect, it, vi } from "vitest";
import { MOCK_COMPANIES, resolveTicker } from "@/lib/companies";

const results = [
  { ticker: "AAPL", company: "Apple Inc." },
  { ticker: "APLE", company: "Apple Hospitality REIT, Inc." },
];

describe("resolveTicker", () => {
  it("uses an exact ticker match, even if it isn't first", () => {
    expect(resolveTicker("aple", results)).toBe("APLE");
  });
  it("falls back to the top suggestion for a company name", () => {
    expect(resolveTicker("apple", results)).toBe("AAPL");
  });
  it("uses the raw text, uppercased, when there are no suggestions", () => {
    expect(resolveTicker("  amc ", [])).toBe("AMC");
  });
});

describe("searchCompanies (mock mode)", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  async function load() {
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "true");
    vi.resetModules();
    return import("@/lib/companies");
  }

  it("matches ticker prefixes and names, case-insensitively", async () => {
    const { searchCompanies } = await load();
    expect((await searchCompanies("in")).map((c) => c.ticker)).toEqual(["INTU", "VZ"]); // ticker, then "INC." in a name
    expect((await searchCompanies("oracle")).map((c) => c.ticker)).toEqual(["ORCL"]);
    expect((await searchCompanies("intuit")).map((c) => c.ticker)).toEqual(["INTU"]);
    expect((await searchCompanies("verizon")).map((c) => c.ticker)).toEqual(["VZ"]);
  });
  it("returns nothing for blank input", async () => {
    const { searchCompanies } = await load();
    expect(await searchCompanies("   ")).toEqual([]);
  });
  it("only offers the placeholder demo companies", async () => {
    const { searchCompanies } = await load();
    const all = await searchCompanies("o");
    expect(all.every((c) => MOCK_COMPANIES.some((m) => m.ticker === c.ticker))).toBe(true);
  });
});
