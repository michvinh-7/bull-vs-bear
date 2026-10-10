import { describe, expect, it } from "vitest";
import { speakingTimeMs } from "@/lib/audio";

describe("speakingTimeMs", () => {
  it("never goes below 1.5 s", () => {
    expect(speakingTimeMs("Hi")).toBe(1500);
  });
  it("scales with word count (~160 words per minute)", () => {
    const twenty = Array(20).fill("word").join(" ");
    expect(speakingTimeMs(twenty)).toBe(20 * 375);
  });
});
