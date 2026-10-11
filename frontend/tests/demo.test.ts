import { existsSync, readFileSync, readdirSync } from "node:fs";
import { afterEach, describe, expect, it, vi } from "vitest";
import { demoId, demoTicker, isDemoId } from "@/lib/demo";
import type { Debate } from "@/lib/types";

const pub = (p: string) => new URL(`../public${p}`, import.meta.url);
const index = JSON.parse(readFileSync(pub("/demo/index.json"), "utf8")) as { ticker: string; lines: number }[];

describe("demo ids", () => {
  it("round-trips a ticker", () => {
    expect(demoId("amc")).toBe("demo-AMC");
    expect(isDemoId("demo-AMC")).toBe(true);
    expect(isDemoId("bb1a1f4abade")).toBe(false);
    expect(demoTicker("demo-vz")).toBe("VZ");
  });
});

describe("recorded debates (stage fallback)", () => {
  it("index lists exactly the recordings on disk", () => {
    const onDisk = readdirSync(pub("/demo/")).filter((d) => existsSync(pub(`/demo/${d}/debate.json`))).sort();
    expect(index.map((r) => r.ticker)).toEqual(onDisk);
    expect(onDisk.length).toBeGreaterThan(0);
  });

  it.each(index.map((r) => r.ticker))("%s plays with no backend: finished, every clip on disk, ids resolve", (t) => {
    const d = JSON.parse(readFileSync(pub(`/demo/${t}/debate.json`), "utf8")) as Debate;
    expect(d.id).toBe(`demo-${t}`);
    expect(d.status).toBe("done");
    expect(d.fact_sheet && d.positions && d.brief).toBeTruthy();
    expect(d.lines.length).toBe(index.find((r) => r.ticker === t)!.lines);
    for (const l of d.lines) {
      expect(l.audio_url.startsWith(`/demo/${t}/`), `turn ${l.turn} must use a local clip`).toBe(true);
      expect(existsSync(pub(l.audio_url)), `missing ${l.audio_url}`).toBe(true);
    }
    const sources = new Set(d.fact_sheet!.sources.map((s) => s.id));
    const claims = new Set(d.lines.flatMap((l) => l.claims.map((c) => c.id)));
    for (const l of d.lines) for (const c of l.claims) expect(c.source_id === null || sources.has(c.source_id)).toBe(true);
    for (const id of [...d.brief!.agreed.flatMap((a) => a.claim_ids), ...d.brief!.unsupported.map((u) => u.claim_id)])
      expect(claims.has(id)).toBe(true);
  });
});

describe("mock mode start", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
    vi.resetModules();
  });

  it("plays a recording when one exists, else the sample", async () => {
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "true");
    vi.stubGlobal("fetch", async () => new Response(JSON.stringify([{ ticker: "AMC" }]), { status: 200 }));
    vi.resetModules();
    const { startDebate } = await import("@/lib/api");
    expect(await startDebate("amc")).toBe("demo-AMC");
    expect(await startDebate("AMZN")).toBe("mock");
  });
});
