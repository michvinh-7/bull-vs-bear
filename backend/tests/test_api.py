"""Every endpoint the frontend calls, run against in-memory storage and a fake
SEC list, so tests never touch the network or the real Supabase."""
import pytest
from fastapi.testclient import TestClient

from app import companies, store
from app.companies import Company
from app.main import app
from app.schemas import CommitteeBrief, Debate

FAKE_SEC = [
    Company(ticker="AAPL", company="Apple Inc."),
    Company(ticker="AAL", company="American Airlines Group Inc."),
    Company(ticker="PINE", company="Alpine Income Property Trust"),
    Company(ticker="F", company="FORD MOTOR CO"),
    Company(ticker="F-PB", company="FORD MOTOR CO"),
]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(store, "_client", None)
    monkeypatch.setattr(store, "_debates", {})
    monkeypatch.setattr(companies, "_sec", FAKE_SEC)
    return TestClient(app)


def test_health(client):
    assert client.get("/health").json() == {"ok": True}


def test_demo_companies(client):
    body = client.get("/companies").json()
    assert body and all({"ticker", "company"} <= c.keys() for c in body)
    assert body[0]["tagline"]


def test_search_ranks_ticker_then_name(client):
    assert [c["ticker"] for c in client.get("/companies/search", params={"q": "aa"}).json()] == ["AAPL", "AAL"]
    assert client.get("/companies/search", params={"q": "apple"}).json()[0]["ticker"] == "AAPL"
    assert [c["ticker"] for c in client.get("/companies/search", params={"q": "alpine"}).json()] == ["PINE"]
    assert "tagline" not in client.get("/companies/search", params={"q": "aapl"}).json()[0]


def test_search_one_row_per_company(client):
    assert [c["ticker"] for c in client.get("/companies/search", params={"q": "ford"}).json()] == ["F"]


def test_search_includes_demo_companies(client):
    assert client.get("/companies/search", params={"q": "northwind"}).json()[0]["ticker"] == "NWRC"


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
    assert client.post("/debates", json={"ticker": "nwrc"}).status_code == 200


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
