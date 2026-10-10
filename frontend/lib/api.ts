import type { CommitteeBrief, Debate } from "./types";
import { mockDebate } from "./mock";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "true";

export function wsUrl(debateId: string) {
  return `${API_URL.replace(/^http/, "ws")}/ws/debates/${debateId}`;
}

/** The backend's own error message (FastAPI puts it in `detail`), or a fallback. */
async function errorFrom(res: Response, fallback: string): Promise<Error> {
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") return new Error(body.detail);
  } catch {}
  return new Error(`${fallback} (${res.status})`);
}

export async function startDebate(ticker: string): Promise<string> {
  if (USE_MOCK) return "mock";
  const res = await fetch(`${API_URL}/debates`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticker }),
  });
  if (!res.ok) throw await errorFrom(res, "Couldn’t start the debate");
  return (await res.json()).debate_id;
}

export async function getDebate(id: string): Promise<Debate> {
  if (USE_MOCK) return mockDebate;
  const res = await fetch(`${API_URL}/debates/${id}`);
  if (!res.ok) throw await errorFrom(res, "Debate not found");
  return res.json();
}

export async function getBrief(id: string): Promise<CommitteeBrief> {
  if (USE_MOCK) return mockDebate.brief!;
  const res = await fetch(`${API_URL}/debates/${id}/brief`);
  if (!res.ok) throw await errorFrom(res, "Brief not ready");
  return res.json();
}
