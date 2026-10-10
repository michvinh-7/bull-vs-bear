"""No single outside service can break the demo: Gemini, ElevenLabs, the
fact-checker or Supabase failing degrades a line, never ends the debate."""
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app import agents, config, main, store, verify, voice
from app.schemas import Debate, FactSheet

SHEET = FactSheet.model_validate(json.loads(
    (Path(__file__).resolve().parents[2] / "shared" / "examples" / "fact_sheet.json").read_text(encoding="utf-8")
))
GOOD_TURN = {
    "text": "This term loan is secured by owned stores and distribution centers. Lenders sit first in line on real assets.",
    "claims": [{"text": "The term loan is secured by owned real property.", "source_id": "S1",
                "quote": "secured by a first-priority lien on owned real property"}],
}


class APIError(Exception):
    def __init__(self, code):
        super().__init__(f"{code} error")
        self.code = code


@pytest.fixture
def gemini(monkeypatch):
    """Script Gemini: each item is a reply dict or an exception to raise. Records sleeps."""
    monkeypatch.setattr(config, "GEMINI_API_KEY", "fake")
    script, sleeps = [], []

    def fake(*args):
        item = script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(agents, "_generate", fake)
    monkeypatch.setattr(agents, "_sleep", sleeps.append)
    return script, sleeps


# ---- Gemini ----

def test_busy_gemini_is_retried(gemini):
    script, sleeps = gemini
    script += [APIError(503), GOOD_TURN]
    assert agents.generate_turn(SHEET, [], "bull", 1) is not None
    assert sleeps == [1.0]


def test_timeouts_are_retried(gemini):
    script, sleeps = gemini
    script += [httpx.ReadTimeout("The read operation timed out"), GOOD_TURN]
    assert agents.generate_turn(SHEET, [], "bull", 1) is not None


def test_gemini_gives_up_after_two_retries(gemini):
    script, sleeps = gemini
    script += [APIError(429), APIError(429), APIError(429)]
    assert agents.generate_turn(SHEET, [], "bull", 1) is None
    assert sleeps == [1.0, 3.0] and "429" in agents.last_error


@pytest.mark.parametrize("code", [400, 401, 404])
def test_bad_requests_are_not_retried(gemini, code):
    script, sleeps = gemini
    script.append(APIError(code))
    assert agents.generate_turn(SHEET, [], "bull", 1) is None
    assert sleeps == []


# ---- ElevenLabs ----

@pytest.fixture
def eleven(monkeypatch):
    monkeypatch.setattr(config, "ELEVENLABS_API_KEY", "fake")
    monkeypatch.setitem(voice.VOICES, "bull", "voice-id")
    monkeypatch.setattr(voice, "_sleep", lambda s: None)
    monkeypatch.setattr(store, "upload_audio", lambda data, path: f"https://cdn/{path}")
    responses = []
    monkeypatch.setattr(voice.httpx, "post", lambda *a, **k: (r := responses.pop(0), r() if callable(r) else r)[1])
    return responses


def resp(status):
    return httpx.Response(status, content=b"mp3" if status == 200 else b"nope", request=httpx.Request("POST", "https://x"))


def test_voice_retries_once_then_plays(eleven):
    eleven += [resp(503), resp(200)]
    assert voice.speak("Hi there.", "bull", "d1", 1) == "https://cdn/d1/01-bull.mp3"


def test_voice_timeout_then_text_only(eleven):
    def timeout():
        raise httpx.ReadTimeout("slow")
    eleven += [timeout, timeout]
    assert voice.speak("Hi there.", "bull", "d1", 1) == ""


def test_voice_out_of_credits_is_not_retried(eleven):
    eleven += [resp(401)]
    assert voice.speak("Hi there.", "bull", "d1", 1) == "" and eleven == []


def test_voice_upload_failure_is_text_only(eleven, monkeypatch):
    def broken(data, path):
        raise RuntimeError("bucket missing")
    monkeypatch.setattr(store, "upload_audio", broken)
    eleven.append(resp(200))
    assert voice.speak("Hi there.", "bull", "d1", 1) == ""


# ---- Supabase ----

class BrokenSupabase:
    def __getattr__(self, name):
        raise RuntimeError("Supabase is down")


def test_supabase_down_keeps_working_from_memory(monkeypatch):
    monkeypatch.setattr(store, "_client", BrokenSupabase())
    monkeypatch.setattr(store, "_debates", {})
    store.save_debate(Debate(id="m1", ticker="NWRC"))  # no exception
    assert store.load_debate("m1").ticker == "NWRC"
    assert store.load_debate("missing") is None
    assert store.upload_audio(b"mp3", "x.mp3") == ""


# ---- A whole debate with everything around Gemini failing ----

def test_debate_survives_fact_checker_voice_and_storage_failures(monkeypatch):
    monkeypatch.setattr(config, "PACING", False)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")  # stub lines
    monkeypatch.setattr(config, "VOICE_ENABLED", True)
    monkeypatch.setattr(store, "_debates", {})

    def crash(*a):
        raise RuntimeError("boom")
    monkeypatch.setattr(verify, "check_claims", crash)
    monkeypatch.setattr(voice, "speak", crash)
    store.save_debate(Debate(id="r1", ticker="NWRC", max_turns=2))
    monkeypatch.setattr(store, "_client", BrokenSupabase())

    msgs = []
    with TestClient(main.app).websocket_connect("/ws/debates/r1") as ws:
        while not msgs or msgs[-1]["type"] not in ("brief", "error"):
            msgs.append(ws.receive_json())
    lines = [m["data"] for m in msgs if m["type"] == "line"]
    assert msgs[-1]["type"] == "brief" and len(lines) == 3
    assert all(l["audio_url"] == "" for l in lines)
    assert {c["label"] for l in lines for c in l["claims"]} <= {"pending", "verified", "contested", "unsupported"}


# ---- Fact-check model: never holds up a line ----

def _claims():
    from app.schemas import Claim
    return [Claim(id="t1c1", text="The term loan is secured.", source_id="S1")]


def test_lines_go_out_pending_while_the_model_loads(monkeypatch):
    import asyncio
    monkeypatch.setitem(main.fact_check, "state", "loading")
    out = asyncio.run(main._fact_check_in_time(_claims(), SHEET))
    assert [c.label for c in out] == ["pending"]


def test_slow_fact_check_times_out_to_pending(monkeypatch):
    import asyncio
    import time as _time
    monkeypatch.setattr(config, "FACT_CHECK_TIMEOUT", 0.2)
    monkeypatch.setattr(verify, "nli", lambda p, h: (_time.sleep(1), "entailment")[1])
    out = asyncio.run(main._fact_check_in_time(_claims(), SHEET))
    assert [c.label for c in out] == ["pending"]


def test_fast_fact_check_labels_the_claims():
    import asyncio
    out = asyncio.run(main._fact_check_in_time(_claims(), SHEET))
    assert [c.label for c in out] == ["verified"]


def test_warm_up_reports_ready_or_failed(monkeypatch):
    monkeypatch.setitem(main.fact_check, "state", "idle")
    main._warm_up_fact_check()
    assert main.fact_check["state"] == "ready"

    def broken(p, h):
        raise RuntimeError("out of memory")
    monkeypatch.setattr(verify, "nli", broken)
    monkeypatch.setitem(main.fact_check, "state", "idle")
    main._warm_up_fact_check()
    assert main.fact_check["state"] == "failed"


def test_fact_check_off_switch(monkeypatch):
    import asyncio
    monkeypatch.setattr(config, "FACT_CHECK", False)
    monkeypatch.setitem(main.fact_check, "state", "idle")
    out = asyncio.run(main._fact_check_in_time(_claims(), SHEET))
    assert [c.label for c in out] == ["pending"] and main.fact_check["state"] == "off"
