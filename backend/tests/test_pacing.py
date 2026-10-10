"""The debate stays one line ahead of playback, and questions are taken until
the last line has been heard."""
import asyncio
import time

import pytest
from fastapi.testclient import TestClient

from app import config, main, pacing, store
from app.pacing import Pacer, speaking_seconds
from app.schemas import Debate

TEN_WORDS = "one two three four five six seven eight nine ten"


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


def test_estimate_lines_play_back_to_back():
    clock = Clock()
    p = Pacer(clock)
    p.sent(1, TEN_WORDS)
    p.sent(2, TEN_WORDS)  # queued behind line 1
    assert p.unfinished() == 2
    clock.now += speaking_seconds(TEN_WORDS) + 0.01
    assert p.unfinished() == 1
    clock.now += speaking_seconds(TEN_WORDS)
    assert p.unfinished() == 0


def test_client_reports_beat_the_estimate():
    clock = Clock()
    p = Pacer(clock)
    p.sent(1, TEN_WORDS)
    p.sent(2, TEN_WORDS)
    p.played(1)  # client finished early (e.g. short audio)
    assert p.unfinished() == 1
    clock.now += 2 * speaking_seconds(TEN_WORDS) + 1  # estimate says done, but client hasn't said so
    assert p.unfinished() == 1
    clock.now += pacing.GRACE_SECONDS  # client went quiet: don't stall forever
    assert p.unfinished() == 0


def test_wait_returns_early_when_a_question_arrives():
    p = Pacer(Clock())  # frozen clock: the line never finishes on its own
    p.sent(1, TEN_WORDS)
    questions = asyncio.Queue()
    questions.put_nowait("Why?")
    asyncio.run(asyncio.wait_for(p.wait(0, questions, poll=0.01), 1))


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(config, "PACING", True)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    monkeypatch.setattr(config, "VOICE_ENABLED", False)
    monkeypatch.setattr(store, "_client", None)
    monkeypatch.setattr(store, "_debates", {})
    return TestClient(main.app)


def test_question_during_the_last_line_is_still_answered(client):
    """Before pacing, the server finished in seconds and hung up, so this question was lost."""
    store.save_debate(Debate(id="p1", ticker="NWRC", max_turns=2))
    lines, asked = [], False
    with client.websocket_connect("/ws/debates/p1") as ws:
        while True:
            msg = ws.receive_json()
            if msg["type"] == "line":
                lines.append(msg["data"])
                last_planned = len([l for l in lines if not l["from_user"]]) == 3  # bull, moderator, answer
                if last_planned and not asked:
                    ws.send_json({"type": "interrupt", "question": "Will they run out of cash?"})
                    asked = True
                else:
                    ws.send_json({"type": "played", "turn": msg["data"]["turn"]})
                if asked and msg["data"]["turn"] > 3:
                    ws.send_json({"type": "played", "turn": 3})  # finally let the held line finish
            if msg["type"] in ("brief", "error"):
                break
    assert msg["type"] == "brief"
    assert [(l["speaker"], l["from_user"]) for l in lines][3] == ("moderator", True)
    assert len(lines) == 6  # 3 planned + question + both sides


def test_server_waits_for_playback_before_writing_ahead(client, monkeypatch):
    """With a frozen clock and no 'played' reports, the server sends at most 2 lines
    (one playing, one queued) and then waits."""
    clock = Clock()
    monkeypatch.setattr(main, "Pacer", lambda: Pacer(clock))
    monkeypatch.setattr(pacing, "GRACE_SECONDS", 0)
    store.save_debate(Debate(id="p2", ticker="NWRC", max_turns=6))
    with client.websocket_connect("/ws/debates/p2") as ws:
        got = 0
        while got < 2:
            if ws.receive_json()["type"] == "line":
                got += 1
        time.sleep(0.5)  # give a server that ignores playback time to run ahead
        # Nothing else should be generated until playback moves; then it continues.
        assert len(store.load_debate("p2").lines) == 2
        clock.now += 1000
        while ws.receive_json()["type"] != "line":
            pass
    assert len(store.load_debate("p2").lines) >= 3
