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
  // Sample clips made with macOS `say` (public/mock-audio) so the audio queue can be tested.
  lines: (lines as LineMessage[]).map((l) => ({
    ...l,
    audio_url: `/mock-audio/${String(l.turn).padStart(2, "0")}-${l.speaker}.m4a`,
  })),
  brief: brief as CommitteeBrief,
};
