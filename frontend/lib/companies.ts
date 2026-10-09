import { API_URL, USE_MOCK } from "./api";

export interface DemoCompany {
  ticker: string;
  company: string;
  tagline?: string;
}

// Placeholder demo companies until Person 1 picks the real three.
// In mock mode every one of them plays the Northwind sample debate.
export const MOCK_COMPANIES: DemoCompany[] = [
  { ticker: "NWRC", company: "Northwind Retail Corp", tagline: "Store closures vs. floating-rate debt" },
  { ticker: "CTSO", company: "Contoso Airlines", tagline: "Fuel costs vs. aircraft collateral" },
  { ticker: "FBKM", company: "Fabrikam Steel", tagline: "Cyclical cash flow vs. 2027 maturity wall" },
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
