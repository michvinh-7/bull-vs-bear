import { describe, expect, it } from "vitest";
import { errorFrom } from "@/lib/api";

const json = (status: number, body: unknown) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

describe("errorFrom", () => {
  it("uses the backend's detail message", async () => {
    const err = await errorFrom(json(404, { detail: "No public company with ticker ZZZZQ" }), "Couldn’t start");
    expect(err.message).toBe("No public company with ticker ZZZZQ");
  });
  it("falls back when detail isn't a string (FastAPI validation errors)", async () => {
    const err = await errorFrom(json(422, { detail: [{ msg: "field required" }] }), "Couldn’t start");
    expect(err.message).toBe("Couldn’t start (422)");
  });
  it("falls back when the body isn't JSON", async () => {
    const err = await errorFrom(new Response("Bad Gateway", { status: 502 }), "Debate not found");
    expect(err.message).toBe("Debate not found (502)");
  });
});

describe("startDebate", () => {
  const ok = () => new Response(JSON.stringify({ debate_id: "abc" }), { status: 200 });

  it("sends the model and the user's key only when set", async () => {
    const { startDebate } = await import("@/lib/api");
    const calls: RequestInit[] = [];
    const fetchMock = async (_: unknown, init?: RequestInit) => (calls.push(init!), ok());
    const real = globalThis.fetch;
    globalThis.fetch = fetchMock as typeof fetch;
    try {
      await startDebate("nwrc");
      await startDebate("nwrc", { model: "gemini-3.5-flash-lite", apiKey: "AIzaUserOwnKey_0123456789abcdef" });
    } finally {
      globalThis.fetch = real;
    }
    expect(JSON.parse(calls[0].body as string)).toEqual({ ticker: "nwrc" });
    expect(JSON.parse(calls[1].body as string)).toEqual({
      ticker: "nwrc",
      model: "gemini-3.5-flash-lite",
      gemini_api_key: "AIzaUserOwnKey_0123456789abcdef",
    });
  });
});
