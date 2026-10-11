import type { CommitteeBrief, Debate, ModelsResponse } from "./types";
import { mockDebate } from "./mock";
import { mockModels } from "./mock/models";
import { demoId, demoRecordings, isDemoId, loadDemo } from "./demo";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "true";

export function wsUrl(debateId: string) {
  return `${API_URL.replace(/^http/, "ws")}/ws/debates/${debateId}`;
}

/** The backend's own error message (FastAPI puts it in `detail`), or a fallback. */
export async function errorFrom(res: Response, fallback: string): Promise<Error> {
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") return new Error(body.detail);
  } catch {}
  return new Error(`${fallback} (${res.status})`);
}

export interface StartOptions {
  model?: string | null; // a ModelOption id; server default if omitted
  apiKey?: string | null; // the user's own Gemini key, sent only to our backend
}

export async function startDebate(ticker: string, opts: StartOptions = {}): Promise<string> {
  if (USE_MOCK) {
    // Mock mode plays a real recorded debate when there is one, else the Northwind sample.
    const recorded = (await demoRecordings()).some((r) => r.ticker === ticker.trim().toUpperCase());
    return recorded ? demoId(ticker.trim()) : "mock";
  }
  const res = await fetch(`${API_URL}/debates`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ticker,
      ...(opts.model ? { model: opts.model } : {}),
      ...(opts.apiKey ? { gemini_api_key: opts.apiKey } : {}),
    }),
  });
  if (!res.ok) throw await errorFrom(res, "Couldn’t start the debate");
  return (await res.json()).debate_id;
}

export async function getModels(): Promise<ModelsResponse> {
  if (USE_MOCK) return mockModels;
  const res = await fetch(`${API_URL}/models`);
  if (!res.ok) throw await errorFrom(res, "Couldn’t load models");
  return res.json();
}

export async function getDebate(id: string): Promise<Debate> {
  if (isDemoId(id)) return loadDemo(id); // recordings never need the backend
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
