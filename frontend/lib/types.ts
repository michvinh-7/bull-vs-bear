// The 3 shared data shapes. Must match shared/schemas/*.json and backend/app/schemas.py.
// Any change here gets announced to the whole team.

export type Speaker = "bull" | "bear" | "moderator";
export type Label = "verified" | "contested" | "unsupported" | "pending";

export interface Metric {
  name: string;
  value: number;
  source: string;
}

export interface FactSheet {
  company: string;
  ticker: string;
  metrics: Metric[];
  debt_details: Record<string, unknown>[];
  news: { headline: string; url: string }[];
}

export interface Claim {
  text: string;
  label: Label;
  source: string;
  passage: string;
}

export interface LineMessage {
  turn: number;
  speaker: Speaker;
  text: string;
  claims: Claim[];
  audio_url: string;
}

export interface CommitteeBrief {
  agreed: string[];
  disputed: { bull: string; bear: string }[];
  unsupported: string[];
  open_questions: string[];
}

export interface Debate {
  id: string;
  ticker: string;
  status: "running" | "done" | "error";
  fact_sheet: FactSheet | null;
  lines: LineMessage[];
  brief: CommitteeBrief | null;
}

// WebSocket envelopes
export type ServerMessage =
  | { type: "fact_sheet"; data: FactSheet }
  | { type: "line"; data: LineMessage }
  | { type: "brief"; data: CommitteeBrief }
  | { type: "error"; message: string };

export type ClientMessage = { type: "interrupt"; question: string };

export const DISCLAIMER = "This summarizes the debate. It is not investment advice.";
