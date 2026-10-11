"""Every endpoint the frontend calls, run against in-memory storage and a fake
SEC list, so tests never touch the network or the real Supabase."""
import pytest
from fastapi.testclient import TestClient

from app import companies, config, store
from app.companies import Company
from app.main import app
from app.schemas import CommitteeBrief, Debate

FAKE_SEC = [
    Company(ticker="AAPL", company="Apple Inc."),
    Company(ticker="AAL", company="American Airlines Group Inc."),
    Company(ticker="PINE", company="Alpine Income Property Trust"),
    Company(ticker="GOOGL", company="Alphabet Inc."),
    Company(ticker="GOOG", company="Alphabet Inc."),
]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(store, "_client", None)
    monkeypatch.setattr(store, "_debates", {})
    monkeypatch.setattr(companies, "_sec", FAKE_SEC)
    monkeypatch.setattr(config, "PACING", False)
    return TestClient(app)


def test_health(client, monkeypatch):
    from app import config
    monkeypatch.setattr(config, "GEMINI_API_KEY", "secret-value")
    body = client.get("/health").json()
    assert body["ok"] is True and body["gemini"]["key"] == "set" and body["storage"] == "memory"
    assert "secret-value" not in str(body)


def test_health_shows_which_voice_settings_are_missing(client, monkeypatch):
    from app import config, voice
    monkeypatch.setattr(config, "ELEVENLABS_API_KEY", "el-secret")
    monkeypatch.setitem(voice.VOICES, "bull", "bull-voice-id")
    monkeypatch.setitem(voice.VOICES, "bear", "")
    setup = client.get("/health").json()["voice_setup"]
    assert setup["key"] == "set" and setup["bull"] == "set" and setup["bear"] == "missing"
    assert "el-secret" not in str(setup) and "bull-voice-id" not in str(setup)


def test_demo_companies(client):
    body = client.get("/companies").json()
    assert [c["ticker"] for c in body] == ["AMZN", "VZ", "AMC"]
    assert all({"ticker", "company"} <= c.keys() and c["tagline"] for c in body)


def test_search_ranks_ticker_then_name(client):
    assert [c["ticker"] for c in client.get("/companies/search", params={"q": "aa"}).json()] == ["AAPL", "AAL"]
    assert client.get("/companies/search", params={"q": "apple"}).json()[0]["ticker"] == "AAPL"
    assert [c["ticker"] for c in client.get("/companies/search", params={"q": "alpine"}).json()] == ["PINE"]
    assert "tagline" not in client.get("/companies/search", params={"q": "aapl"}).json()[0]


def test_search_one_row_per_company(client):
    assert [c["ticker"] for c in client.get("/companies/search", params={"q": "alphabet"}).json()] == ["GOOGL"]


def test_search_includes_demo_companies(client):
    assert client.get("/companies/search", params={"q": "verizon"}).json()[0]["ticker"] == "VZ"


def test_search_needs_a_query(client):
    assert client.get("/companies/search").status_code == 422
    assert client.get("/companies/search", params={"q": ""}).status_code == 422
    assert client.get("/companies/search", params={"q": "zzzz"}).json() == []


def test_start_debate_and_fetch_it(client):
    r = client.post("/debates", json={"ticker": " aapl "})
    assert r.status_code == 200
    debate = client.get(f"/debates/{r.json()['debate_id']}").json()
    assert debate["ticker"] == "AAPL" and debate["status"] == "running"


def test_start_debate_demo_ticker(client):
    assert client.post("/debates", json={"ticker": "amc"}).status_code == 200


def test_start_debate_rejects_bad_tickers(client):
    assert client.post("/debates", json={"ticker": "  "}).status_code == 400
    assert client.post("/debates", json={"ticker": "NOTREAL"}).status_code == 404
    assert client.post("/debates", json={}).status_code == 422


def test_start_debate_allows_any_ticker_when_sec_is_down(client, monkeypatch):
    monkeypatch.setattr(companies, "_sec_companies", lambda: [])
    assert client.post("/debates", json={"ticker": "NOTREAL"}).status_code == 200


def test_missing_debate_and_brief(client):
    assert client.get("/debates/nope").status_code == 404
    assert client.get("/debates/nope/brief").status_code == 404


def test_brief_only_when_ready(client):
    store.save_debate(Debate(id="d1", ticker="AAPL"))
    assert client.get("/debates/d1/brief").status_code == 404
    store.save_debate(Debate(id="d1", ticker="AAPL", status="done", brief=CommitteeBrief()))
    assert client.get("/debates/d1/brief").json() == CommitteeBrief().model_dump()


def test_websocket_unknown_debate(client):
    with client.websocket_connect("/ws/debates/nope") as ws:
        assert ws.receive_json() == {"type": "error", "message": "Debate not found"}


def test_websocket_replays_finished_debate(client):
    store.save_debate(Debate(id="d2", ticker="AAPL", status="done", brief=CommitteeBrief()))
    with client.websocket_connect("/ws/debates/d2") as ws:
        assert ws.receive_json()["type"] == "brief"


@pytest.mark.parametrize("origin, allowed", [
    ("http://localhost:3000", True),
    ("https://bull-vs-bear.vercel.app", True),
    ("https://bull-vs-bear-git-p3-frontend-team.vercel.app", True),  # Vercel preview link
    ("https://evil.example.com", False),
    ("https://vercel.app.evil.com", False),
])
def test_cors_allows_the_frontend_sites(client, origin, allowed):
    r = client.options("/debates", headers={"Origin": origin, "Access-Control-Request-Method": "POST"})
    assert (r.headers.get("access-control-allow-origin") == origin) is allowed


def test_saved_fact_sheet_is_used_instead_of_rebuilding(client, monkeypatch):
    import json as _json
    from pathlib import Path
    from app import edgar, facts
    from app.schemas import FactSheet
    sheet = FactSheet.model_validate(_json.loads(
        (Path(__file__).resolve().parents[2] / "shared" / "examples" / "fact_sheet.json").read_text(encoding="utf-8")))
    sheet = sheet.model_copy(update={"ticker": "VZ"})
    # VZ's latest 10-K was already built: only the quick "is there a newer 10-K?" check runs
    monkeypatch.setattr(edgar, "get_cik", lambda t: "0000732712")
    monkeypatch.setattr(edgar, "latest_filing", lambda cik: ("0001", "https://sec.gov/10k"))
    monkeypatch.setattr(edgar, "get_company_facts", lambda cik: (_ for _ in ()).throw(AssertionError("rebuilt")))
    monkeypatch.setattr(store, "_cache", {
        f"VZ|filing|0001|{facts.CODE_VERSION}": {"sheet": sheet.model_dump(), "built_at": "2026-10-10T12:00:00+00:00"},
    })
    store.save_debate(Debate(id="c1", ticker="VZ", max_turns=2))
    with client.websocket_connect("/ws/debates/c1") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "fact_sheet" and msg["data"]["ticker"] == "VZ"
