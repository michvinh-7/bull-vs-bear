import { API_URL, USE_MOCK } from "./api";

export interface DemoCompany {
  ticker: string;
  company: string;
  tagline?: string;
}

// The three demo companies (same as DEMO_COMPANIES in backend/app/companies.py). Shown before
// GET /companies answers and if it fails. In mock mode each one plays the Northwind sample debate.
export const MOCK_COMPANIES: DemoCompany[] = [
  { ticker: "AMZN", company: "Amazon.com, Inc.", tagline: "AI spending spree vs. a fortress balance sheet" },
  { ticker: "VZ", company: "Verizon Communications Inc.", tagline: "Steady subscriber cash vs. a giant debt load" },
  { ticker: "AMC", company: "AMC Entertainment Holdings, Inc.", tagline: "Box office comeback vs. a mountain of debt" },
];

export async function getCompanies(): Promise<DemoCompany[]> {
  if (USE_MOCK) return MOCK_COMPANIES;
  try {
    const res = await fetch(`${API_URL}/companies`);
    if (!res.ok) throw new Error();
    return await res.json();
  } catch {
    return MOCK_COMPANIES;
  }
}

/** Type-ahead suggestions: demo companies first, then SEC's full list (backend). */
export async function searchCompanies(q: string, signal?: AbortSignal): Promise<DemoCompany[]> {
  const query = q.trim();
  if (!query) return [];
  if (USE_MOCK) {
    const Q = query.toUpperCase();
    return MOCK_COMPANIES.filter((c) => c.ticker.startsWith(Q) || c.company.toUpperCase().includes(Q));
  }
  const res = await fetch(`${API_URL}/companies/search?q=${encodeURIComponent(query)}`, { signal });
  if (!res.ok) return [];
  return res.json();
}

/** What "Start debate" means for typed text: an exact ticker, else the top suggestion, else the raw text. */
export function resolveTicker(query: string, results: DemoCompany[]): string {
  const q = query.trim().toUpperCase();
  return (results.find((r) => r.ticker === q) ?? results[0])?.ticker ?? q;
}
