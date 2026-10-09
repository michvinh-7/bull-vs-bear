// Typed access to the example data (refresh the JSON with `npm run sync-shapes`).
import type { CommitteeBrief, Debate, FactSheet, LineMessage, Positions } from "../types";
import factSheet from "./fact_sheet.json";
import positions from "./positions.json";
import lines from "./line_messages.json";
import brief from "./committee_brief.json";

export const mockDebate: Debate = {
  id: "mock",
  ticker: "NWRC",
  status: "done",
  max_turns: 4,
  fact_sheet: factSheet as FactSheet,
  positions: positions as Positions,
  lines: lines as LineMessage[],
  brief: brief as CommitteeBrief,
};
