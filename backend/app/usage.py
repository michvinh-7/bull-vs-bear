"""Which Gemini models a user may pick, what they cost, and per-debate usage. Owner: Person 3.

Each live debate runs inside a DebateContext (a contextvar), so every Gemini call
and voice clip made for that debate, including those in worker threads, is counted
against it, with the user's own API key if they gave one. The key lives only here,
in memory, for the length of the debate: it is never saved, logged or sent back.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field

from pydantic import BaseModel

# Paid-tier standard prices, USD per 1M tokens; output includes thinking tokens.
# Source: https://ai.google.dev/gemini-api/docs/pricing (checked 2026-10-10).
PRICES_CHECKED = "2026-10-10"
DEFAULT_MODEL = "gemini-3.6-flash"
MODELS: dict[str, dict] = {
    "gemini-3.6-flash": {
        "label": "Flash",
        "note": "Balanced speed and quality. Recommended.",
        "input_per_m": 0.75,
        "output_per_m": 3.75,
        "price_note": "Introductory price through Dec 31, 2026 ($1.50 / $7.50 after).",
        "min_thinking": "minimal",
    },
    "gemini-3.5-flash-lite": {
        "label": "Flash-Lite",
        "note": "Fastest and cheapest. Shorter, simpler arguments.",
        "input_per_m": 0.30,
        "output_per_m": 2.50,
        "price_note": "",
        "min_thinking": "minimal",
    },
    "gemini-3.1-pro-preview": {
        "label": "Pro (preview)",
        "note": "Most capable, but slower. Needs an API key with Pro access.",
        "input_per_m": 2.00,
        "output_per_m": 12.00,
        "price_note": "Prompts up to 200k tokens.",
        "min_thinking": "low",  # Pro rejects thinking_level=minimal
    },
}
# Google answers some retired names with a newer model; price them as what actually ran.
ALIASES = {"gemini-3.5-flash": "gemini-3.6-flash"}

THINKING_ORDER = ["minimal", "low", "medium", "high"]


def resolve(model: str) -> str:
    return ALIASES.get(model, model)


def thinking_for(model: str, wanted: str) -> str:
    """Raise the thinking level to the model's minimum (Pro can't do "minimal")."""
    floor = MODELS.get(resolve(model), {}).get("min_thinking", "minimal")
    return max(wanted, floor, key=lambda lvl: THINKING_ORDER.index(lvl) if lvl in THINKING_ORDER else 0)


class Usage(BaseModel):
    """Running totals for one debate. Sent to the browser and saved with the debate."""

    model: str
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    thinking_tokens: int = 0
    voice_chars: int = 0
    cost_usd: float | None = 0.0  # None when the model's price isn't known

    def add_gemini(self, model_version: str | None, input_tokens: int, output_tokens: int, thinking_tokens: int) -> None:
        self.calls += 1
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.thinking_tokens += thinking_tokens
        price = MODELS.get(resolve(model_version or self.model))
        if price is None or self.cost_usd is None:
            self.cost_usd = None
        else:
            # Not rounded per call: tiny per-call roundings add up over a debate. The UI rounds for display.
            self.cost_usd += (input_tokens * price["input_per_m"] + (output_tokens + thinking_tokens) * price["output_per_m"]) / 1e6

    def add_voice(self, chars: int) -> None:
        self.voice_chars += chars


@dataclass
class DebateContext:
    model: str
    usage: Usage
    api_key: str | None = field(default=None, repr=False)  # never printed


_current: ContextVar[DebateContext | None] = ContextVar("debate_context", default=None)


def current() -> DebateContext | None:
    return _current.get()


def enter(ctx: DebateContext):
    """Start counting against `ctx` in this task (and threads it starts). Returns a token for leave()."""
    return _current.set(ctx)


def leave(token) -> None:
    _current.reset(token)


@contextmanager
def debate_context(ctx: DebateContext):
    token = _current.set(ctx)
    try:
        yield ctx
    finally:
        _current.reset(token)


def record_gemini(resp) -> None:
    """Count one Gemini response against the current debate (no-op outside a debate)."""
    ctx = current()
    meta = getattr(resp, "usage_metadata", None)
    if ctx is None or meta is None:
        return
    ctx.usage.add_gemini(
        getattr(resp, "model_version", None),
        meta.prompt_token_count or 0,
        meta.candidates_token_count or 0,
        getattr(meta, "thoughts_token_count", None) or 0,
    )


def record_voice(text: str) -> None:
    ctx = current()
    if ctx is not None:
        ctx.usage.add_voice(len(text))


def models_payload() -> dict:
    """What GET /models returns: the picker's options and where the prices came from."""
    return {
        "default": DEFAULT_MODEL,
        "prices_checked": PRICES_CHECKED,
        "models": [{"id": mid, **{k: v for k, v in m.items() if k != "min_thinking"}} for mid, m in MODELS.items()],
    }
