// The shared data shapes. Must match backend/app/schemas.py (the source of truth).
// Any change here gets announced to the whole team.

export type Speaker = "bull" | "bear" | "moderator";
export type Side = "bull" | "bear";
export type Label = "verified" | "contested" | "unsupported" | "pending";

// ---- Fact sheet ----

export interface Source {
  id: string; // "S3" filings, "N1" news
  kind: "10-K" | "10-Q" | "8-K" | "news" | "other";
  label: string; // what the citation chip shows
  url: string;
  excerpt: string; // exact document text the fact-checker read
}

export interface Metric {
  name: string;
  label: string;
  value: number;
  unit: "x" | "pct" | "usd" | "year";
  formula: string; // Python's working, e.g. "$310M EBITDA / $163M interest"
  source_ids: string[];
}

export interface DebtInstrument {
  name: string;
  amount_usd: number;
  seniority: "senior_secured" | "senior_unsecured" | "subordinated";
  rate_type: "fixed" | "floating";
  rate: string;
  maturity_year: number;
  source_id: string;
}

export interface FactSheet {
  company: string;
  ticker: string;
  as_of: string;
  sources: Source[];
  metrics: Metric[];
  debt: DebtInstrument[];
}

// ---- Positions (side panels) ----

export interface Position {
  thesis: string;
  points: { text: string; source_id: string | null }[];
}

export interface Positions {
  bull: Position;
  bear: Position;
}

// ---- Line message ----

export interface Claim {
  id: string; // "t2c1"
  text: string;
  source_id: string | null; // null = unsupported
  label: Label;
}

export interface LineMessage {
  turn: number;
  speaker: Speaker;
  from_user: boolean;
  text: string;
  claims: Claim[];
  audio_url: string;
}

// ---- Committee brief ----

export interface CommitteeBrief {
  agreed: { text: string; claim_ids: string[] }[];
  disputed: { topic: string; bull: string; bear: string; claim_ids: string[] }[];
  unsupported: { claim_id: string; speaker: Side; text: string }[];
  open_questions: { question: string; where_to_look: string }[];
}

// ---- API / WebSocket ----

export interface Debate {
  id: string;
  ticker: string;
  status: "running" | "done" | "error";
  max_turns: number;
  fact_sheet: FactSheet | null;
  positions: Positions | null;
  lines: LineMessage[];
  brief: CommitteeBrief | null;
}

export type ServerMessage =
  | { type: "fact_sheet"; data: FactSheet }
  | { type: "positions"; data: Positions }
  | { type: "turn_start"; turn: number; speaker: Speaker; max_turns: number }
  | { type: "line"; data: LineMessage }
  | { type: "brief"; data: CommitteeBrief }
  | { type: "error"; message: string };

export type ClientMessage = { type: "interrupt"; question: string };

export const DISCLAIMER = "This summarizes the debate. It is not investment advice.";
