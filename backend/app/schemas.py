"""The shared data shapes. Source of truth for shared/schemas/*.json.

After editing, run `python -m scripts.export_schemas` from backend/ and update
frontend/lib/types.ts to match. Any change gets announced to the whole team.
"""
from typing import Literal

from pydantic import BaseModel, Field

Speaker = Literal["bull", "bear", "moderator"]
Side = Literal["bull", "bear"]
Label = Literal["verified", "contested", "unsupported", "pending"]


# ---- Fact sheet (made once per company, read by the debaters) ----

class Source(BaseModel):
    """One citable passage. Claims and metrics point here by id, so the
    fact-checker always checks against the real filing text, never text a
    debater wrote."""
    id: str = Field(description='Short stable id, e.g. "S3" for filings, "N1" for news')
    kind: Literal["10-K", "10-Q", "8-K", "news", "other"]
    label: str = Field(description='What the citation chip shows, e.g. "10-Q · Liquidity, p. 31"')
    url: str = ""
    excerpt: str = Field(description="Exact text from the document; what the fact-checker reads")


class Metric(BaseModel):
    name: str = Field(description="Stable key, e.g. leverage, interest_coverage")
    label: str = Field(description='Display name, e.g. "Interest coverage"')
    value: float
    unit: Literal["x", "pct", "usd", "year"]
    formula: str = Field("", description='Python-computed working, e.g. "$310M EBITDA / $163M interest"')
    source_ids: list[str] = Field(default_factory=list)


class DebtInstrument(BaseModel):
    name: str
    amount_usd: float
    seniority: Literal["senior_secured", "senior_unsecured", "subordinated"]
    rate_type: Literal["fixed", "floating"]
    rate: str = Field(description='As written, e.g. "SOFR + 4.25%"')
    maturity_year: int
    source_id: str


class FactSheet(BaseModel):
    company: str
    ticker: str
    as_of: str = Field(description='Fiscal period of the latest filing, e.g. "FY2025" or "Q2 2026"')
    sources: list[Source] = Field(default_factory=list)
    metrics: list[Metric] = Field(default_factory=list)
    debt: list[DebtInstrument] = Field(default_factory=list)
    notices: list[str] = Field(
        default_factory=list,
        description="Plain-English notes for the debate page when part of the data couldn't be fetched, "
                    "e.g. older news or EDGAR being down",
    )

    def source(self, source_id: str | None) -> Source | None:
        return next((s for s in self.sources if s.id == source_id), None)


# ---- Positions (once per debate, before turn 1; fills the side panels) ----

class Point(BaseModel):
    text: str
    source_id: str | None = None


class Position(BaseModel):
    thesis: str
    points: list[Point] = Field(default_factory=list)


class Positions(BaseModel):
    bull: Position
    bear: Position


# ---- Line message (one per debate turn, sent over the WebSocket) ----

class Claim(BaseModel):
    id: str = Field(description='"t{turn}c{n}", e.g. "t2c1"; the brief links back to these')
    text: str
    source_id: str | None = Field(None, description="Must be an id in fact_sheet.sources; null means Unsupported")
    label: Label = "pending"


class LineMessage(BaseModel):
    turn: int
    speaker: Speaker
    from_user: bool = Field(False, description="True when a moderator line relays a user's interrupt")
    text: str
    claims: list[Claim] = Field(default_factory=list)
    audio_url: str = ""


# ---- Committee brief (one per debate, at the end) ----

class AgreedPoint(BaseModel):
    text: str
    claim_ids: list[str] = Field(default_factory=list)


class DisputedPoint(BaseModel):
    topic: str
    bull: str
    bear: str
    claim_ids: list[str] = Field(default_factory=list)


class UnsupportedClaim(BaseModel):
    claim_id: str
    speaker: Side
    text: str


class OpenQuestion(BaseModel):
    question: str
    where_to_look: str = Field(description='e.g. "10-K · Item 7A, market risk"')


class CommitteeBrief(BaseModel):
    agreed: list[AgreedPoint] = Field(default_factory=list)
    disputed: list[DisputedPoint] = Field(default_factory=list)
    unsupported: list[UnsupportedClaim] = Field(
        default_factory=list, description="Built in Python from claim labels, not by Gemini"
    )
    open_questions: list[OpenQuestion] = Field(default_factory=list)


DISCLAIMER = "This summarizes the debate. It is not investment advice."


# ---- API request/response bodies ----

class StartDebateRequest(BaseModel):
    ticker: str


class StartDebateResponse(BaseModel):
    debate_id: str


class Debate(BaseModel):
    id: str
    ticker: str
    status: Literal["running", "done", "error"] = "running"
    max_turns: int = 8
    fact_sheet: FactSheet | None = None
    positions: Positions | None = None
    lines: list[LineMessage] = Field(default_factory=list)
    brief: CommitteeBrief | None = None

    def claim(self, claim_id: str) -> Claim | None:
        return next((c for line in self.lines for c in line.claims if c.id == claim_id), None)
