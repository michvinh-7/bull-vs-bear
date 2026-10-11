import type { Debate } from "./types";

/**
 * Recorded debates in public/demo/ (made with `npm run demo:save`), the stage fallback.
 * Any debate id "demo-<TICKER>" plays the recording, even on the live site with the
 * backend down: /debate/demo-AMC. In mock mode the demo cards play them too.
 */
export const DEMO_PREFIX = "demo-";

export interface DemoRecording {
  ticker: string;
  company: string;
  lines: number;
  recorded_from: string;
}

export const isDemoId = (id: string) => id.startsWith(DEMO_PREFIX);
export const demoTicker = (id: string) => id.slice(DEMO_PREFIX.length).toUpperCase();
export const demoId = (ticker: string) => `${DEMO_PREFIX}${ticker.toUpperCase()}`;

let index: Promise<DemoRecording[]> | null = null;

/** Which recordings exist (public/demo/index.json); empty if none or unreachable. */
export function demoRecordings(): Promise<DemoRecording[]> {
  index ??= fetch("/demo/index.json")
    .then((r) => (r.ok ? r.json() : []))
    .catch(() => []);
  return index;
}

export async function loadDemo(id: string): Promise<Debate> {
  const res = await fetch(`/demo/${demoTicker(id)}/debate.json`);
  if (!res.ok) throw new Error(`No recorded debate for ${demoTicker(id)}`);
  return res.json();
}
