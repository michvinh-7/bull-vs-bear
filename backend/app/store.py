"""Supabase: the filing cabinet. Owner: Person 2.

Falls back to an in-memory dict when Supabase isn't configured, so everyone
can run the backend locally on day one. Everything is kept in memory first, so
a Supabase hiccup is logged and the running debate carries on.

Suggested Supabase setup
  table  debates (id text primary key, ticker text, data jsonb, updated_at timestamptz default now())
  table  fact_sheets (ticker text primary key, data jsonb)
  bucket audio (public)
"""
from . import config
from .schemas import Debate, FactSheet

_debates: dict[str, Debate] = {}
_fact_sheets: dict[str, FactSheet] = {}

_client = None
if config.SUPABASE_URL and config.SUPABASE_SERVICE_KEY:
    from supabase import create_client

    _client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)


def _safe(what: str, fn):
    """Run a Supabase call; on failure log it and return None instead of breaking the debate."""
    try:
        return fn()
    except Exception as e:
        print(f"[store] Supabase {what} failed: {str(e)[:200]}")
        return None


def save_debate(debate: Debate) -> None:
    _debates[debate.id] = debate
    if _client:
        _safe("save debate", lambda: _client.table("debates").upsert(
            {"id": debate.id, "ticker": debate.ticker, "data": debate.model_dump()}
        ).execute())


def load_debate(debate_id: str) -> Debate | None:
    if debate_id in _debates:
        return _debates[debate_id]
    if _client:
        result = _safe("load debate", lambda: _client.table("debates").select("data").eq("id", debate_id).execute())
        if result and result.data:
            return Debate.model_validate(result.data[0]["data"])
    return None


def save_fact_sheet(sheet: FactSheet, key: str | None = None) -> None:
    """`key` defaults to the ticker; facts.py adds a version so old sheets aren't reused."""
    key = key or sheet.ticker
    _fact_sheets[key] = sheet
    if _client:
        _safe("save fact sheet", lambda: _client.table("fact_sheets").upsert(
            {"ticker": key, "data": sheet.model_dump()}
        ).execute())


def load_fact_sheet(ticker: str) -> FactSheet | None:
    if ticker in _fact_sheets:
        return _fact_sheets[ticker]
    if _client:
        result = _safe("load fact sheet", lambda: _client.table("fact_sheets").select("data").eq("ticker", ticker).execute())
        if result and result.data:
            return FactSheet.model_validate(result.data[0]["data"])
    return None


def upload_audio(data: bytes, path: str) -> str:
    """Public URL of the uploaded clip, or "" if storage isn't available."""
    if not _client:
        return ""

    def upload():
        _client.storage.from_("audio").upload(path, data, {"content-type": "audio/mpeg", "upsert": "true"})
        return _client.storage.from_("audio").get_public_url(path)

    return _safe("audio upload", upload) or ""
