import type { CommitteeBrief, Debate } from "./types";
import { mockDebate } from "./mock";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "true";

export function wsUrl(debateId: string) {
  return `${API_URL.replace(/^http/, "ws")}/ws/debates/${debateId}`;
}

export async function startDebate(ticker: string): Promise<string> {
  if (USE_MOCK) return "mock";
  const res = await fetch(`${API_URL}/debates`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticker }),
  });
  if (!res.ok) throw new Error(`Start failed: ${res.status}`);
  return (await res.json()).debate_id;
}

export async function getDebate(id: string): Promise<Debate> {
  if (USE_MOCK) return mockDebate;
  const res = await fetch(`${API_URL}/debates/${id}`);
  if (!res.ok) throw new Error(`Debate not found: ${res.status}`);
  return res.json();
}

export async function getBrief(id: string): Promise<CommitteeBrief> {
  if (USE_MOCK) return mockDebate.brief!;
  const res = await fetch(`${API_URL}/debates/${id}/brief`);
  if (!res.ok) throw new Error(`Brief not ready: ${res.status}`);
  return res.json();
}
