"use client";

import { useCallback, useEffect, useState } from "react";
import type { ModelOption, Usage } from "./types";

/**
 * Per-browser settings: which Gemini model to use, the user's own API key, and
 * a running total of usage across every debate started from this browser.
 *
 * The key lives in sessionStorage (this tab only, gone when it closes) and is
 * only ever sent to our backend with "start debate". Everything else is a
 * per-viewer convenience in localStorage. Storage can be blocked (private
 * windows), so every read/write is wrapped and the app works without it.
 */

const MODEL_KEY = "bvb-model";
const API_KEY = "bvb-gemini-key";
const TOTALS_KEY = "bvb-usage-total";
const COUNTED_KEY = "bvb-usage-counted"; // debate ids already added, so a replay never double-counts
const EVENT = "bvb-settings-change";

export interface Totals {
  debates: number;
  calls: number;
  input_tokens: number;
  output_tokens: number;
  thinking_tokens: number;
  voice_chars: number;
  cost_usd: number;
  unpriced_debates: number; // debates whose model had no known price (cost excluded)
}

export const EMPTY_TOTALS: Totals = {
  debates: 0,
  calls: 0,
  input_tokens: 0,
  output_tokens: 0,
  thinking_tokens: 0,
  voice_chars: 0,
  cost_usd: 0,
  unpriced_debates: 0,
};

function read(store: "local" | "session", key: string): string | null {
  try {
    return (store === "local" ? localStorage : sessionStorage).getItem(key);
  } catch {
    return null;
  }
}

function write(store: "local" | "session", key: string, value: string | null) {
  try {
    const s = store === "local" ? localStorage : sessionStorage;
    if (value === null) s.removeItem(key);
    else s.setItem(key, value);
  } catch {}
  if (typeof window !== "undefined") window.dispatchEvent(new Event(EVENT));
}

export function getModel(): string | null {
  return read("local", MODEL_KEY);
}
export function setModel(id: string) {
  write("local", MODEL_KEY, id);
}

export function getApiKey(): string | null {
  return read("session", API_KEY);
}
export function setApiKey(key: string | null) {
  write("session", API_KEY, key && key.trim() ? key.trim() : null);
}

/** Loose shape check before sending; the backend checks again. */
export function looksLikeKey(key: string): boolean {
  const k = key.trim();
  return k.length >= 20 && k.length <= 200 && !/\s/.test(k);
}

export function getTotals(): Totals {
  try {
    return { ...EMPTY_TOTALS, ...JSON.parse(read("local", TOTALS_KEY) ?? "{}") };
  } catch {
    return EMPTY_TOTALS;
  }
}

/** Add a finished debate's usage to the browser total, once per debate id. */
export function addToTotals(debateId: string, u: Usage): boolean {
  let counted: string[] = [];
  try {
    counted = JSON.parse(read("local", COUNTED_KEY) ?? "[]");
  } catch {}
  if (counted.includes(debateId)) return false;
  const t = getTotals();
  const next: Totals = {
    debates: t.debates + 1,
    calls: t.calls + u.calls,
    input_tokens: t.input_tokens + u.input_tokens,
    output_tokens: t.output_tokens + u.output_tokens,
    thinking_tokens: t.thinking_tokens + u.thinking_tokens,
    voice_chars: t.voice_chars + u.voice_chars,
    cost_usd: t.cost_usd + (u.cost_usd ?? 0),
    unpriced_debates: t.unpriced_debates + (u.cost_usd === null ? 1 : 0),
  };
  write("local", TOTALS_KEY, JSON.stringify(next));
  write("local", COUNTED_KEY, JSON.stringify([...counted, debateId].slice(-200)));
  return true;
}

export function resetTotals() {
  write("local", TOTALS_KEY, null);
  write("local", COUNTED_KEY, null);
}

/** Live view of the settings; every component using it updates together. */
export function useSettings() {
  const [state, setState] = useState({ model: null as string | null, hasKey: false, totals: EMPTY_TOTALS });
  const refresh = useCallback(() => setState({ model: getModel(), hasKey: !!getApiKey(), totals: getTotals() }), []);
  useEffect(() => {
    refresh();
    window.addEventListener(EVENT, refresh);
    window.addEventListener("storage", refresh); // other tabs
    return () => {
      window.removeEventListener(EVENT, refresh);
      window.removeEventListener("storage", refresh);
    };
  }, [refresh]);
  return state;
}

// ---- Formatting ----

export function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(n >= 10_000_000 ? 0 : 1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(n >= 10_000 ? 0 : 1)}k`;
  return String(n);
}

/** Small amounts keep enough digits to be meaningful (a debate costs fractions of a cent). */
export function formatUsd(n: number | null): string {
  if (n === null) return "unknown";
  if (n === 0) return "$0.00";
  if (n < 0.01) return `$${n.toFixed(4)}`;
  return `$${n.toFixed(2)}`;
}

export function priceLine(m: ModelOption): string {
  return `$${m.input_per_m.toFixed(2)} in / $${m.output_per_m.toFixed(2)} out per 1M tokens`;
}
