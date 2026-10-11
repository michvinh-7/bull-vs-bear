"""A user's question is capped at MAX_QUESTION_CHARS before it is relayed (read aloud, sent to Gemini)."""
from fastapi.testclient import TestClient

from app import config, main, store
from app.schemas import Debate


def test_overlong_question_is_cut_to_the_limit(monkeypatch):
    monkeypatch.setattr(config, "PACING", False)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    monkeypatch.setattr(config, "VOICE_ENABLED", False)
    monkeypatch.setattr(store, "_client", None)
    monkeypatch.setattr(store, "_debates", {})
    monkeypatch.setattr(main, "_live", set())
    store.save_debate(Debate(id="long", ticker="NWRC", max_turns=2))
    msgs = []
    with TestClient(main.app).websocket_connect("/ws/debates/long") as ws:
        ws.send_json({"type": "interrupt", "question": "  " + "Why? " * 400})  # 2,000 characters
        while not msgs or msgs[-1]["type"] not in ("brief", "error"):
            msgs.append(ws.receive_json())
    asked = [m["data"]["text"] for m in msgs if m["type"] == "line" and m["data"]["from_user"]]
    assert asked and len(asked[0]) <= config.MAX_QUESTION_CHARS
    assert asked[0].startswith("Why?")  # leading spaces trimmed


def test_blank_question_is_ignored(monkeypatch):
    monkeypatch.setattr(config, "PACING", False)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    monkeypatch.setattr(config, "VOICE_ENABLED", False)
    monkeypatch.setattr(store, "_client", None)
    monkeypatch.setattr(store, "_debates", {})
    monkeypatch.setattr(main, "_live", set())
    store.save_debate(Debate(id="blank", ticker="NWRC", max_turns=2))
    msgs = []
    with TestClient(main.app).websocket_connect("/ws/debates/blank") as ws:
        ws.send_json({"type": "interrupt", "question": "     "})
        while not msgs or msgs[-1]["type"] not in ("brief", "error"):
            msgs.append(ws.receive_json())
    assert not any(m["type"] == "line" and m["data"]["from_user"] for m in msgs)
