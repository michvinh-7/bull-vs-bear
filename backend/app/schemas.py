"""The 3 shared data shapes. Must match shared/schemas/*.json and frontend/lib/types.ts.

Any change here gets announced to the whole team.
"""
from typing import Literal

from pydantic import BaseModel, Field


# ---- Fact sheet (made once per company, read by the debaters) ----

class Metric(BaseModel):
    name: str
    value: float
    source: str


class NewsItem(BaseModel):
    headline: str
    url: str


class FactSheet(BaseModel):
    company: str
    ticker: str
    metrics: list[Metric] = Field(default_factory=list)
    debt_details: list[dict] = Field(default_factory=list)
    news: list[NewsItem] = Field(default_factory=list)


# ---- Line message (one per debate turn, sent over the WebSocket) ----

Speaker = Literal["bull", "bear", "moderator"]
Label = Literal["verified", "contested", "unsupported", "pending"]


class Claim(BaseModel):
    text: str
    label: Label = "pending"
    source: str = ""
    passage: str = ""


class LineMessage(BaseModel):
    turn: int
    speaker: Speaker
    text: str
    claims: list[Claim] = Field(default_factory=list)
    audio_url: str = ""


# ---- Committee brief (one per debate, at the end) ----

class DisputedPoint(BaseModel):
    bull: str
    bear: str


class CommitteeBrief(BaseModel):
    agreed: list[str] = Field(default_factory=list)
    disputed: list[DisputedPoint] = Field(default_factory=list)
    unsupported: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


DISCLAIMER = "This summarizes the debate. It is not investment advice."


# ---- API request/response bodies (not part of the 3 shared shapes) ----

class StartDebateRequest(BaseModel):
    ticker: str


class StartDebateResponse(BaseModel):
    debate_id: str


class Debate(BaseModel):
    id: str
    ticker: str
    status: Literal["running", "done", "error"] = "running"
    fact_sheet: FactSheet | None = None
    lines: list[LineMessage] = Field(default_factory=list)
    brief: CommitteeBrief | None = None
