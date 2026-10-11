"""GET /debates: the History list. Only finished debates with a brief; summaries, newest first."""
import pytest
from fastapi.testclient import TestClient

from app import config, main, store
from app.schemas import Claim, CommitteeBrief, Debate, LineMessage


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(store, "_client", None)
    monkeypatch.setattr(store, "_debates", {})
    monkeypatch.setattr(config, "PACING", False)
    return TestClient(main.app)


def line(turn, labels):
    return LineMessage(turn=turn, speaker="bull", text="x", claims=[Claim(id=f"t{turn}c{i}", text="c", label=l) for i, l in enumerate(labels, 1)])


def test_lists_only_finished_debates_with_a_brief(client):
    brief = CommitteeBrief(agreed=[])
    store.save_debate(Debate(id="old", ticker="VZ", status="done", brief=brief, lines=[line(1, ["verified"])]))
    store.save_debate(Debate(id="new", ticker="INTU", status="done", brief=brief, model="gemini-3.5-flash",
                             lines=[line(1, ["verified", "unsupported"]), line(2, ["verified"])]))
    store.save_debate(Debate(id="cut", ticker="ORCL", status="interrupted", lines=[line(1, ["verified"])]))
    store.save_debate(Debate(id="running", ticker="ORCL"))
    store.save_debate(Debate(id="nobrief", ticker="VZ", status="done"))
    rows = client.get("/debates").json()
    assert [r["id"] for r in rows] == ["new", "old"]  # newest first; the rest left out
    assert rows[0]["lines"] == 2 and rows[0]["labels"] == {"verified": 2, "unsupported": 1}
    assert rows[0]["model"] == "gemini-3.5-flash" and "brief" not in rows[0] and "fact_sheet" not in rows[0]


def test_limit_is_bounded(client):
    assert client.get("/debates", params={"limit": 0}).status_code == 422
    assert client.get("/debates", params={"limit": 500}).status_code == 422
    assert client.get("/debates", params={"limit": 5}).status_code == 200


def test_still_serves_one_debate_by_id(client):
    store.save_debate(Debate(id="one", ticker="VZ"))
    assert client.get("/debates/one").json()["id"] == "one"
