import { afterEach, describe, expect, it, vi } from "vitest";
import { idFrom } from "@/lib/history";

describe("idFrom (open a debate by ID or pasted link)", () => {
  it("accepts a bare id", () => expect(idFrom("  aac5836d5ccf ")).toBe("aac5836d5ccf"));
  it("accepts brief and debate links, with or without query or trailing slash", () => {
    expect(idFrom("https://bull-vs-bear-three.vercel.app/brief/aac5836d5ccf")).toBe("aac5836d5ccf");
    expect(idFrom("https://bull-vs-bear-three.vercel.app/debate/aac5836d5ccf?replay=1")).toBe("aac5836d5ccf");
    expect(idFrom("/debate/demo-VZ/")).toBe("demo-VZ");
  });
});

describe("getHistory", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
    vi.resetModules();
  });

  it("reads GET /debates in real mode", async () => {
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "false");
    const urls: string[] = [];
    vi.stubGlobal("fetch", async (u: string) => (urls.push(u), new Response(JSON.stringify([{ id: "a", ticker: "VZ" }]), { status: 200 })));
    vi.resetModules();
    const { getHistory } = await import("@/lib/api");
    expect((await getHistory()).map((r) => r.id)).toEqual(["a"]);
    expect(urls[0]).toMatch(/\/debates$/);
  });

  it("lists the recorded fallback debates in mock mode", async () => {
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "true");
    const debate = { id: "demo-VZ", lines: [{ turn: 1, claims: [{ label: "verified" }, { label: "verified" }] }], fact_sheet: { as_of: "FY2025" } };
    vi.stubGlobal("fetch", async (u: string) =>
      new Response(JSON.stringify(u.endsWith("index.json") ? [{ ticker: "VZ", company: "Verizon", lines: 1 }] : debate), { status: 200 }),
    );
    vi.resetModules();
    const { getHistory } = await import("@/lib/api");
    const [row] = await getHistory();
    expect(row).toMatchObject({ id: "demo-VZ", ticker: "VZ", company: "Verizon", lines: 1, is_demo: true, labels: { verified: 2 } });
  });
});
