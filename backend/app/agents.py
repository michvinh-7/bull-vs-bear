"""Gemini agents: bull, bear, moderator. Owner: Person 2.

Ground rules baked into every prompt:
  - Argue only from the fact sheet. Never compute new numbers.
  - Every claim cites a source id from the fact sheet.
  - No buy/sell/verdict, ever.

Gemini only writes what needs judgment (GeminiTurn, GeminiBrief). Python adds
everything else: turn numbers, claim ids, labels, audio, the unsupported list.
"""
import json
from pathlib import Path

from pydantic import BaseModel

from .schemas import (
    AgreedPoint,
    Claim,
    CommitteeBrief,
    DisputedPoint,
    FactSheet,
    LineMessage,
    OpenQuestion,
    Positions,
    UnsupportedClaim,
)

EXAMPLES = Path(__file__).resolve().parents[2] / "shared" / "examples"

SYSTEM_PROMPTS = {
    "bull": "You are the bull analyst on a credit committee. Argue the strongest honest case that this company's debt is sound...",
    "bear": "You are the bear analyst on a credit committee. Argue the strongest honest case that this company's debt is risky...",
    "moderator": "You are the portfolio manager moderating the debate. Ask sharp questions; never give a verdict...",
}


# ---- What Gemini returns (use as response_schema). Not shared with the frontend. ----

class GeminiClaim(BaseModel):
    text: str
    source_id: str | None  # tip: pass the fact sheet's source ids as an enum in the response schema


class GeminiTurn(BaseModel):
    text: str
    claims: list[GeminiClaim]


class GeminiBrief(BaseModel):
    agreed: list[AgreedPoint]
    disputed: list[DisputedPoint]
    open_questions: list[OpenQuestion]


def _example(name: str):
    return json.loads((EXAMPLES / name).read_text())


def to_line(raw: GeminiTurn, speaker: str, turn: int, from_user: bool = False) -> LineMessage:
    return LineMessage(
        turn=turn,
        speaker=speaker,
        from_user=from_user,
        text=raw.text,
        claims=[Claim(id=f"t{turn}c{i}", text=c.text, source_id=c.source_id) for i, c in enumerate(raw.claims, 1)],
    )


def generate_positions(fact_sheet: FactSheet) -> Positions:
    """TODO(Person 2): one Gemini call per side for thesis + 3 points with source ids."""
    return Positions.model_validate(_example("positions.json"))


def generate_turn(
    fact_sheet: FactSheet,
    history: list[LineMessage],
    speaker: str,
    turn: int,
    question: str | None = None,
) -> LineMessage:
    """TODO(Person 2): call Gemini with SYSTEM_PROMPTS[speaker], the fact sheet,
    the history and (for moderator turns) the user's question, using GeminiTurn
    as the response schema, then return to_line(...).

    Stub: replays the example lines so the frontend has something to show.
    """
    if speaker == "moderator" and question:
        return to_line(GeminiTurn(text=question, claims=[]), "moderator", turn, from_user=True)
    examples = [LineMessage.model_validate(x) for x in _example("line_messages.json")]
    same_side = [x for x in examples if x.speaker == speaker] or examples
    pick = same_side[(turn // 2) % len(same_side)]
    raw = GeminiTurn(text=pick.text, claims=[GeminiClaim(text=c.text, source_id=c.source_id) for c in pick.claims])
    return to_line(raw, speaker, turn)


def unsupported_claims(lines: list[LineMessage]) -> list[UnsupportedClaim]:
    """Straight from the fact-checker's labels, so Gemini can't soften them."""
    return [
        UnsupportedClaim(claim_id=c.id, speaker=line.speaker, text=c.text)
        for line in lines
        if line.speaker in ("bull", "bear")
        for c in line.claims
        if c.label == "unsupported"
    ]


def write_brief(fact_sheet: FactSheet, lines: list[LineMessage]) -> CommitteeBrief:
    """TODO(Person 2): Gemini fills GeminiBrief (agreed / disputed / open questions,
    citing claim ids). Python adds the unsupported list."""
    raw = GeminiBrief.model_validate(_example("committee_brief.json"))
    return CommitteeBrief(**raw.model_dump(), unsupported=unsupported_claims(lines))
