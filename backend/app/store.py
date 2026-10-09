"""Supabase: the filing cabinet. Owner: Person 2.

Falls back to an in-memory dict when Supabase isn't configured, so everyone
can run the backend locally on day one.

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


def save_debate(debate: Debate) -> None:
    _debates[debate.id] = debate
    if _client:
        _client.table("debates").upsert(
            {"id": debate.id, "ticker": debate.ticker, "data": debate.model_dump()}
        ).execute()


def load_debate(debate_id: str) -> Debate | None:
    if debate_id in _debates:
        return _debates[debate_id]
    if _client:
        rows = _client.table("debates").select("data").eq("id", debate_id).execute().data
        if rows:
            return Debate.model_validate(rows[0]["data"])
    return None


def save_fact_sheet(sheet: FactSheet) -> None:
    _fact_sheets[sheet.ticker] = sheet
    if _client:
        _client.table("fact_sheets").upsert({"ticker": sheet.ticker, "data": sheet.model_dump()}).execute()


def load_fact_sheet(ticker: str) -> FactSheet | None:
    if ticker in _fact_sheets:
        return _fact_sheets[ticker]
    if _client:
        rows = _client.table("fact_sheets").select("data").eq("ticker", ticker).execute().data
        if rows:
            return FactSheet.model_validate(rows[0]["data"])
    return None


def upload_audio(data: bytes, path: str) -> str:
    if not _client:
        return ""
    _client.storage.from_("audio").upload(path, data, {"content-type": "audio/mpeg", "upsert": "true"})
    return _client.storage.from_("audio").get_public_url(path)
