// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  addToTotals,
  formatTokens,
  formatUsd,
  getApiKey,
  getModel,
  getTotals,
  looksLikeKey,
  priceLine,
  resetTotals,
  setApiKey,
  setModel,
} from "@/lib/settings";
import { mockModels, mockUsage } from "@/lib/mock/models";
import type { Usage } from "@/lib/types";

const KEY = "AIzaUserOwnKey_0123456789abcdef";
const usage = (over: Partial<Usage> = {}): Usage => ({
  model: "gemini-3.6-flash", calls: 10, input_tokens: 30_000, output_tokens: 2_000, thinking_tokens: 500, voice_chars: 1_500, cost_usd: 0.03, ...over,
});

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
});

describe("model and key storage", () => {
  it("remembers the chosen model in this browser", () => {
    expect(getModel()).toBeNull();
    setModel("gemini-3.5-flash-lite");
    expect(getModel()).toBe("gemini-3.5-flash-lite");
  });

  it("keeps the API key in this tab only, never in long-term storage", () => {
    setApiKey(`  ${KEY}  `);
    expect(getApiKey()).toBe(KEY);
    expect(sessionStorage.getItem("bvb-gemini-key")).toBe(KEY);
    expect(JSON.stringify({ ...localStorage })).not.toContain(KEY);
  });

  it("removes the key when cleared or blank", () => {
    setApiKey(KEY);
    setApiKey(null);
    expect(getApiKey()).toBeNull();
    setApiKey("   ");
    expect(getApiKey()).toBeNull();
  });

  it("tells components when settings change", () => {
    const heard = vi.fn();
    window.addEventListener("bvb-settings-change", heard);
    setModel("gemini-3.6-flash");
    setApiKey(KEY);
    expect(heard).toHaveBeenCalledTimes(2);
  });

  it("checks the key's shape loosely", () => {
    expect(looksLikeKey(KEY)).toBe(true);
    expect(looksLikeKey("short")).toBe(false);
    expect(looksLikeKey("has spaces in the middle of it oops")).toBe(false);
  });
});

describe("running totals", () => {
  it("adds a finished debate once, even if it's seen again", () => {
    expect(addToTotals("d1", usage())).toBe(true);
    expect(addToTotals("d1", usage())).toBe(false);
    addToTotals("d2", usage({ cost_usd: 0.02, calls: 5 }));
    const t = getTotals();
    expect(t.debates).toBe(2);
    expect(t.calls).toBe(15);
    expect(t.cost_usd).toBeCloseTo(0.05);
    expect(t.thinking_tokens).toBe(1000);
  });

  it("keeps unpriced debates out of the cost but counts their tokens", () => {
    addToTotals("d1", usage({ cost_usd: null }));
    const t = getTotals();
    expect(t.cost_usd).toBe(0);
    expect(t.unpriced_debates).toBe(1);
    expect(t.input_tokens).toBe(30_000);
  });

  it("resets to zero and forgets which debates were counted", () => {
    addToTotals("d1", usage());
    resetTotals();
    expect(getTotals().debates).toBe(0);
    expect(addToTotals("d1", usage())).toBe(true);
  });

  it("survives corrupted storage", () => {
    localStorage.setItem("bvb-usage-total", "{not json");
    expect(getTotals().debates).toBe(0);
  });
});

describe("formatting", () => {
  it("shortens token counts", () => {
    expect(formatTokens(950)).toBe("950");
    expect(formatTokens(1_500)).toBe("1.5k");
    expect(formatTokens(42_000)).toBe("42k");
    expect(formatTokens(3_200_000)).toBe("3.2M");
  });

  it("keeps enough digits for fractions of a cent", () => {
    expect(formatUsd(0)).toBe("$0.00");
    expect(formatUsd(0.0042)).toBe("$0.0042");
    expect(formatUsd(1.234)).toBe("$1.23");
    expect(formatUsd(null)).toBe("unknown");
  });

  it("describes a model's price", () => {
    expect(priceLine(mockModels.models[0])).toBe("$0.75 in / $3.75 out per 1M tokens");
  });
});

describe("mock usage", () => {
  it("grows as lines are played and prices by the chosen model", () => {
    const a = mockUsage("gemini-3.6-flash", 1);
    const b = mockUsage("gemini-3.6-flash", 4, true);
    expect(b.calls).toBeGreaterThan(a.calls);
    expect(b.cost_usd!).toBeGreaterThan(a.cost_usd!);
    expect(mockUsage("gemini-3.1-pro-preview", 4).cost_usd!).toBeGreaterThan(mockUsage("gemini-3.5-flash-lite", 4).cost_usd!);
  });
});
