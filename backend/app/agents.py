"""Gemini agents: bull, bear, moderator. Owner: Person 2.

Ground rules baked into every prompt:
  - Argue only from the fact sheet. Never compute new numbers.
  - Every claim cites a source from the fact sheet.
  - No buy/sell/verdict, ever.
"""
import json
from pathlib import Path

from .schemas import CommitteeBrief, FactSheet, LineMessage

EXAMPLES = Path(__file__).resolve().parents[2] / "shared" / "examples"

SYSTEM_PROMPTS = {
    "bull": "You are the bull analyst on a credit committee. Argue the strongest honest case that this company's debt is sound...",
    "bear": "You are the bear analyst on a credit committee. Argue the strongest honest case that this company's debt is risky...",
    "moderator": "You are the portfolio manager moderating the debate. Ask sharp questions; never give a verdict...",
}


def generate_turn(
    fact_sheet: FactSheet,
    history: list[LineMessage],
    speaker: str,
    turn: int,
    question: str | None = None,
) -> LineMessage:
    """TODO(Person 2): call Gemini with SYSTEM_PROMPTS[speaker], the fact sheet,
    the history and (for moderator turns) the user's question. Use structured
    JSON output with LineMessage as the response schema.

    Stub: replays the example lines so the frontend has something to show.
    """
    if speaker == "moderator" and question:
        return LineMessage(turn=turn, speaker="moderator", text=question)
    examples = [LineMessage.model_validate(x) for x in json.loads((EXAMPLES / "line_messages.json").read_text())]
    same_side = [x for x in examples if x.speaker == speaker] or examples
    line = same_side[(turn // 2) % len(same_side)].model_copy(deep=True)
    line.turn = turn
    for c in line.claims:
        c.label = "pending"  # verify.py assigns the real label
    return line


def write_brief(fact_sheet: FactSheet, lines: list[LineMessage]) -> CommitteeBrief:
    """TODO(Person 2): Gemini summarizes agreed / disputed / unsupported / open
    questions. Unsupported should come straight from claims labeled unsupported."""
    return CommitteeBrief.model_validate(json.loads((EXAMPLES / "committee_brief.json").read_text()))
