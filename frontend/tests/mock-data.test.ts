import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { mockDebate } from "@/lib/mock";

const shared = (name: string) => JSON.parse(readFileSync(new URL(`../../shared/examples/${name}`, import.meta.url), "utf8"));
const local = (name: string) => JSON.parse(readFileSync(new URL(`../lib/mock/${name}`, import.meta.url), "utf8"));

describe("mock data", () => {
  it.each(["fact_sheet.json", "positions.json", "line_messages.json", "committee_brief.json"])(
    "%s matches shared/examples (run `npm run sync-shapes` if this fails)",
    (name) => expect(local(name)).toEqual(shared(name)),
  );

  it("every claim cites a real source or none", () => {
    const ids = new Set(mockDebate.fact_sheet!.sources.map((s) => s.id));
    for (const line of mockDebate.lines) for (const c of line.claims) expect(c.source_id === null || ids.has(c.source_id)).toBe(true);
  });

  it("every brief item points at a claim that exists", () => {
    const claims = new Set(mockDebate.lines.flatMap((l) => l.claims.map((c) => c.id)));
    const b = mockDebate.brief!;
    for (const id of [...b.agreed.flatMap((a) => a.claim_ids), ...b.disputed.flatMap((d) => d.claim_ids), ...b.unsupported.map((u) => u.claim_id)])
      expect(claims.has(id)).toBe(true);
  });

  it("has a sample clip for every line", () => {
    for (const l of mockDebate.lines) {
      expect(l.audio_url).toMatch(/^\/mock-audio\/\d\d-(bull|bear|moderator)\.m4a$/);
      expect(() => readFileSync(new URL(`../public${l.audio_url}`, import.meta.url))).not.toThrow();
    }
  });
});
