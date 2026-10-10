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
