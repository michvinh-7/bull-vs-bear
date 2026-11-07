// Server only (reads files from disk): used by the brief's metadata and preview image.
import { readFile } from "node:fs/promises";
import path from "node:path";
import { API_URL, USE_MOCK } from "./api";
import { demoTicker, isDemoId } from "./demo";
import { mockDebate } from "./mock";
import type { Debate } from "./types";

/**
 * A debate for server-side rendering (link previews). Recordings are read from
 * public/demo on disk; live debates come from the backend. Returns null rather than
 * throwing, so a missing debate or a slow backend only costs the preview, never the page.
 */
export async function loadDebateOnServer(id: string): Promise<Debate | null> {
  try {
    if (isDemoId(id)) {
      const ticker = demoTicker(id).replace(/[^A-Z0-9.-]/g, "");
      const file = path.join(process.cwd(), "public", "demo", ticker, "debate.json");
      return JSON.parse(await readFile(file, "utf8"));
    }
    if (USE_MOCK) return mockDebate;
    const res = await fetch(`${API_URL}/debates/${encodeURIComponent(id)}`, {
      next: { revalidate: 300 },
      signal: AbortSignal.timeout(4000),
    });
    return res.ok ? await res.json() : null;
  } catch {
    return null;
  }
}
