"""A refresh or second tab must never restart a debate (double spend, duplicated lines),
and a debate stops generating once its browser is gone. Stub agents: no key, no network."""
import time

import pytest
from fastapi.testclient import TestClient

from app import agents, config, main, store
from app.schemas import Debate, LineMessage


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(config, "PACING", False)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    monkeypatch.setattr(config, "VOICE_ENABLED", False)
    monkeypatch.setattr(store, "_client", None)
    monkeypatch.setattr(store, "_debates", {})
    monkeypatch.setattr(main, "_live", set())
    return TestClient(main.app)


def collect(ws, until=("brief", "error", "interrupted")):
    msgs = []
    while not msgs or msgs[-1]["type"] not in until:
        msgs.append(ws.receive_json())
    return msgs


def test_reconnecting_to_a_half_finished_debate_replays_it_and_never_restarts(client, monkeypatch):
    said = [LineMessage(turn=1, speaker="bull", text="First."), LineMessage(turn=2, speaker="bear", text="Second.")]
    store.save_debate(Debate(id="half", ticker="NWRC", status="interrupted", lines=said))
    calls = []
    monkeypatch.setattr(agents, "generate_turn", lambda *a, **k: calls.append(a))
    monkeypatch.setattr(agents, "generate_positions", lambda *a, **k: calls.append(a))
    with client.websocket_connect("/ws/debates/half") as ws:
        msgs = collect(ws)
    assert [m["data"]["turn"] for m in msgs if m["type"] == "line"] == [1, 2]
    assert msgs[-1] == {"type": "interrupted"}
    assert calls == []  # nothing regenerated
    assert len(store.load_debate("half").lines) == 2


def test_a_debate_left_running_by_a_crash_is_also_not_restarted(client):
    store.save_debate(Debate(id="stale", ticker="NWRC", lines=[LineMessage(turn=1, speaker="bull", text="Hi.")]))
    with client.websocket_connect("/ws/debates/stale") as ws:
        msgs = collect(ws)
    assert msgs[-1]["type"] == "interrupted" and len(store.load_debate("stale").lines) == 1


def test_a_second_connection_while_live_does_not_start_a_second_copy(client, monkeypatch):
    store.save_debate(Debate(id="busy", ticker="NWRC"))
    main._live.add("busy")  # another tab is generating it right now
    monkeypatch.setattr(agents, "generate_positions", lambda *a, **k: pytest.fail("second copy started"))
    with client.websocket_connect("/ws/debates/busy") as ws:
        assert collect(ws)[-1]["type"] == "interrupted"


def test_leaving_mid_debate_marks_it_interrupted_and_generates_nothing_more(client, monkeypatch):
    # Note: TestClient tears the server side down when the client disconnects, so this checks the
    # outcome (interrupted, no extra lines), not that the `gone` signal itself fired. On a real
    # server `gone` is what stops a debate that is waiting on playback (see pace() in main.py).
    monkeypatch.setattr(config, "PACING", True)
    store.save_debate(Debate(id="leave", ticker="NWRC", max_turns=8))
    real, calls = agents.generate_turn, []

    def counted(*a, **k):
        calls.append(1)
        return real(*a, **k)

    monkeypatch.setattr(agents, "generate_turn", counted)
    with client.websocket_connect("/ws/debates/leave") as ws:
        lines = 0
        while lines < 2:  # line 2 arrives while line 1 "plays"; then the server waits on playback
            lines += ws.receive_json()["type"] == "line"
        time.sleep(0.3)  # the server is now waiting for line 1 to finish playing (several seconds)
    deadline = time.monotonic() + 1.5  # far less than the first line's playing time
    while "leave" in main._live and time.monotonic() < deadline:
        time.sleep(0.05)
    d = store.load_debate("leave")
    assert "leave" not in main._live, "still generating after the browser left"
    assert d.status == "interrupted" and d.brief is None
    assert len(calls) == 2 and len(d.lines) == 2


def test_a_finished_debate_still_replays_normally(client):
    store.save_debate(Debate(id="fin", ticker="NWRC", max_turns=2))
    with client.websocket_connect("/ws/debates/fin") as ws:
        first = collect(ws, until=("brief", "error"))
    assert first[-1]["type"] == "brief" and store.load_debate("fin").status == "done"
    with client.websocket_connect("/ws/debates/fin") as ws:
        again = collect(ws, until=("brief", "error", "interrupted"))
    assert again[-1]["type"] == "brief"  # replay, not "interrupted"
