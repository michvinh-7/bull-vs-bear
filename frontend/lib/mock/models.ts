import type { ModelsResponse, Usage } from "../types";

// Mock-mode copy of GET /models. The real list and prices live in backend/app/usage.py.
export const mockModels: ModelsResponse = {
  default: "gemini-3.6-flash",
  prices_checked: "2026-10-10",
  models: [
    { id: "gemini-3.6-flash", label: "Flash", note: "Balanced speed and quality. Recommended.", input_per_m: 0.75, output_per_m: 3.75, price_note: "Introductory price through Dec 31, 2026 ($1.50 / $7.50 after)." },
    { id: "gemini-3.5-flash-lite", label: "Flash-Lite", note: "Fastest and cheapest. Shorter, simpler arguments.", input_per_m: 0.3, output_per_m: 2.5, price_note: "" },
    { id: "gemini-3.1-pro-preview", label: "Pro (preview)", note: "Most capable, but slower. Needs an API key with Pro access.", input_per_m: 2, output_per_m: 12, price_note: "Prompts up to 200k tokens." },
  ],
};

/** Plausible running usage after `lines` lines, so the Settings panel has numbers in mock mode. */
export function mockUsage(model: string, lines: number, done = false): Usage {
  const price = mockModels.models.find((m) => m.id === model) ?? mockModels.models[0];
  const calls = 2 + lines + (done ? 1 : 0); // positions (2) + one per line + brief
  const input = calls * 3200;
  const output = calls * 180;
  const voice = lines * 190;
  return {
    model: price.id,
    calls,
    input_tokens: input,
    output_tokens: output,
    thinking_tokens: 0,
    voice_chars: voice,
    cost_usd: (input * price.input_per_m + output * price.output_per_m) / 1e6,
  };
}
