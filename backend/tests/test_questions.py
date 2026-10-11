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


# ---- Who answers first ----

import pytest  # noqa: E402

from app.main import addressed_side  # noqa: E402


@pytest.mark.parametrize("question, side", [
    ("Bull, why does massive cash flow at that scale easily support the business?", "bull"),
    ("bear: what happens if rates rise?", "bear"),
    ("Hey bull, how safe is the 2029 maturity?", "bull"),
    ("Okay Bear what worries you most?", "bear"),
    ("What do you make of that, bull?", "bull"),
    ("Question for the bear: is the revolver a problem?", "bear"),
    ("Can I ask the bull about liquidity?", "bull"),
])
def test_a_named_side_is_detected(question, side):
    assert addressed_side(question) == side


@pytest.mark.parametrize("question", [
    "Why does floating-rate debt matter?",           # nobody named
    "How bad would a bear market be for this debt?",  # market talk, not addressing the bear
    "What's the most bullish part of the filing?",    # "bullish" isn't the bull
    "Bull and bear, where do you actually agree?",    # both named: due side goes first
    "Bearish analysts worry about the revolver. Why?",
])
def test_no_single_side_named(question):
    assert addressed_side(question) is None


def test_the_named_side_answers_first_even_when_the_other_is_due(monkeypatch):
    import time

    monkeypatch.setattr(config, "PACING", False)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    monkeypatch.setattr(config, "VOICE_ENABLED", False)
    monkeypatch.setattr(store, "_client", None)
    monkeypatch.setattr(store, "_debates", {})
    monkeypatch.setattr(main, "_live", set())
    slow = main.build_fact_sheet
    monkeypatch.setattr(main, "build_fact_sheet", lambda t: (time.sleep(0.3), slow(t))[1])  # let the question land first
    store.save_debate(Debate(id="ask-bear", ticker="NWRC", max_turns=2))
    msgs = []
    with TestClient(main.app).websocket_connect("/ws/debates/ask-bear") as ws:
        ws.send_json({"type": "interrupt", "question": "Bear, why does floating-rate debt matter?"})  # bull is due
        while not msgs or msgs[-1]["type"] not in ("brief", "error"):
            msgs.append(ws.receive_json())
    lines = [m["data"] for m in msgs if m["type"] == "line"]
    assert lines[0]["from_user"] is True
    assert [l["speaker"] for l in lines[1:3]] == ["bear", "bull"]  # the bear was asked, so the bear goes first
