"""Settings: model choice, a user's own Gemini key, and token/cost tracking.
Gemini is faked at the client level, so the real _generate runs: no key, no network."""
import asyncio
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import agents, companies, config, main, store, usage, voice
from app.schemas import Debate

USER_KEY = "AIzaUserOwnKey_0123456789abcdef"


# ---- Cost math ----

def test_cost_uses_input_and_output_prices():
    u = usage.Usage(model="gemini-3.6-flash")
    u.add_gemini("gemini-3.6-flash", 1_000_000, 0, 0)
    assert u.cost_usd == pytest.approx(0.75)
    u.add_gemini("gemini-3.6-flash", 0, 1_000_000, 0)
    assert u.cost_usd == pytest.approx(0.75 + 3.75)
    assert (u.calls, u.input_tokens, u.output_tokens) == (2, 1_000_000, 1_000_000)


def test_thinking_tokens_bill_at_the_output_price():
    u = usage.Usage(model="gemini-3.1-pro-preview")
    u.add_gemini("gemini-3.1-pro-preview", 0, 0, 1_000_000)
    assert u.cost_usd == pytest.approx(12.00) and u.thinking_tokens == 1_000_000


def test_many_small_calls_add_up_exactly():
    u = usage.Usage(model="gemini-3.5-flash-lite")
    for _ in range(19):
        u.add_gemini("gemini-3.5-flash-lite", 2271, 172, 0)  # a real debate's typical call
    assert u.cost_usd == pytest.approx(19 * (2271 * 0.30 + 172 * 2.50) / 1e6, rel=1e-12)


def test_retired_name_is_priced_as_the_model_that_ran():
    u = usage.Usage(model="gemini-3.5-flash")
    u.add_gemini("gemini-3.5-flash", 1_000_000, 0, 0)  # Google serves it as 3.6 Flash
    assert u.cost_usd == pytest.approx(0.75)


def test_unknown_model_has_no_cost_rather_than_a_wrong_one():
    u = usage.Usage(model="gemini-9-ultra")
    u.add_gemini("gemini-9-ultra", 1000, 1000, 0)
    u.add_gemini("gemini-3.6-flash", 1000, 1000, 0)
    assert u.cost_usd is None and u.calls == 2 and u.input_tokens == 2000


def test_pro_never_gets_minimal_thinking():
    assert usage.thinking_for("gemini-3.1-pro-preview", "minimal") == "low"
    assert usage.thinking_for("gemini-3.1-pro-preview", "high") == "high"
    assert usage.thinking_for("gemini-3.6-flash", "minimal") == "minimal"
    assert usage.thinking_for("some-new-model", "minimal") == "minimal"


def test_models_payload_lists_prices_and_default():
    body = usage.models_payload()
    ids = [m["id"] for m in body["models"]]
    assert body["default"] in ids and "gemini-3.1-pro-preview" in ids
    assert all({"label", "note", "input_per_m", "output_per_m"} <= m.keys() for m in body["models"])
    assert all("min_thinking" not in m for m in body["models"])


# ---- The real _generate with a fake Gemini client ----

class FakeClient:
    def __init__(self, version):
        self.calls = []
        self.models = SimpleNamespace(generate_content=self._generate)
        self.version = version

    def _generate(self, model, contents, config):
        level = config.thinking_config.thinking_level  # the SDK turns "low" into ThinkingLevel.LOW
        self.calls.append({"model": model, "thinking": str(getattr(level, "value", level)).lower(), "timeout": config.http_options})
        meta = SimpleNamespace(prompt_token_count=1000, candidates_token_count=200, thoughts_token_count=300)
        return SimpleNamespace(text=json.dumps({"ok": True}), usage_metadata=meta, model_version=self.version or model)


@pytest.fixture
def clients(monkeypatch):
    fakes = {}

    def client_for(key):
        return fakes.setdefault(key, FakeClient(None))

    monkeypatch.setattr(agents, "_client_for", client_for)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "server-key")
    monkeypatch.setattr(config, "GEMINI_MODEL", "gemini-3.6-flash")
    return fakes


def call():
    from pydantic import BaseModel

    class Out(BaseModel):
        ok: bool

    return agents._generate("system", "user", Out, 0.5, "minimal")


def test_outside_a_debate_uses_server_key_and_model_and_counts_nothing(clients):
    assert call() == {"ok": True}
    assert list(clients) == ["server-key"] and clients["server-key"].calls[0]["model"] == "gemini-3.6-flash"


def test_debate_uses_the_users_key_and_model_and_counts_tokens(clients):
    ctx = usage.DebateContext(model="gemini-3.1-pro-preview", usage=usage.Usage(model="gemini-3.1-pro-preview"), api_key=USER_KEY)
    with usage.debate_context(ctx):
        call()
    sent = clients[USER_KEY].calls[0]
    assert "server-key" not in clients
    assert sent["model"] == "gemini-3.1-pro-preview" and sent["thinking"] == "low" and sent["timeout"] is not None
    assert (ctx.usage.calls, ctx.usage.input_tokens, ctx.usage.output_tokens, ctx.usage.thinking_tokens) == (1, 1000, 200, 300)
    assert ctx.usage.cost_usd == pytest.approx((1000 * 2.0 + 500 * 12.0) / 1e6)


def test_debate_without_a_users_key_falls_back_to_the_server_key(clients):
    ctx = usage.DebateContext(model="gemini-3.5-flash-lite", usage=usage.Usage(model="gemini-3.5-flash-lite"))
    with usage.debate_context(ctx):
        call()
    assert clients["server-key"].calls[0]["model"] == "gemini-3.5-flash-lite"
    assert clients["server-key"].calls[0]["timeout"] is None  # Flash keeps the 20 s client timeout


def test_counting_follows_calls_into_worker_threads(clients):
    ctx = usage.DebateContext(model="gemini-3.6-flash", usage=usage.Usage(model="gemini-3.6-flash"))

    async def debate():
        with usage.debate_context(ctx):
            await asyncio.gather(*(asyncio.to_thread(call) for _ in range(3)))

    asyncio.run(debate())
    assert ctx.usage.calls == 3


def test_a_users_key_alone_turns_on_real_agents(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    assert not agents.has_key()
    with usage.debate_context(usage.DebateContext(model="gemini-3.6-flash", usage=usage.Usage(model="x"), api_key=USER_KEY)):
        assert agents.has_key()


def test_voice_characters_are_counted_only_when_a_clip_is_made(monkeypatch):
    monkeypatch.setattr(config, "ELEVENLABS_API_KEY", "el-key")
    monkeypatch.setitem(voice.VOICES, "bull", "voice-id")
    monkeypatch.setattr(store, "upload_audio", lambda data, path: "https://audio/x.mp3")
    ctx = usage.DebateContext(model="gemini-3.6-flash", usage=usage.Usage(model="gemini-3.6-flash"))
    with usage.debate_context(ctx):
        monkeypatch.setattr(voice, "_tts", lambda vid, text: b"mp3")
        voice.speak("Twelve chars", "bull", "d1", 1)
        monkeypatch.setattr(voice, "_tts", lambda vid, text: None)  # ElevenLabs failed: nothing billed
        voice.speak("Not counted", "bull", "d1", 2)
    assert ctx.usage.voice_chars == len("Twelve chars")


# ---- API ----

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(store, "_client", None)
    monkeypatch.setattr(store, "_debates", {})
    monkeypatch.setattr(main, "_user_keys", {})
    monkeypatch.setattr(companies, "is_known", lambda t: True)
    monkeypatch.setattr(config, "PACING", False)
    monkeypatch.setattr(config, "VOICE_ENABLED", False)
    return TestClient(main.app)


def test_models_endpoint(client):
    body = client.get("/models").json()
    assert body["default"] == usage.DEFAULT_MODEL and len(body["models"]) == len(usage.MODELS)


def test_start_rejects_unknown_model_and_junk_keys(client):
    r = client.post("/debates", json={"ticker": "NWRC", "model": "gpt-9"})
    assert r.status_code == 400 and "Unknown model" in r.json()["detail"]
    r = client.post("/debates", json={"ticker": "NWRC", "gemini_api_key": "short"})
    assert r.status_code == 400
    r = client.post("/debates", json={"ticker": "NWRC", "gemini_api_key": "has spaces in it which keys never have"})
    assert r.status_code == 400


def test_users_key_is_held_in_memory_and_never_saved_or_returned(client, monkeypatch):
    saved = []
    real_save = store.save_debate
    monkeypatch.setattr(store, "save_debate", lambda d: (saved.append(d.model_dump_json()), real_save(d)))
    r = client.post("/debates", json={"ticker": "NWRC", "model": "gemini-3.5-flash-lite", "gemini_api_key": USER_KEY})
    debate_id = r.json()["debate_id"]
    assert main._user_keys[debate_id][0] == USER_KEY
    body = client.get(f"/debates/{debate_id}").json()
    assert body["model"] == "gemini-3.5-flash-lite" and body["usage"]["calls"] == 0
    assert USER_KEY not in json.dumps(body) and not any(USER_KEY in s for s in saved)
    assert USER_KEY not in repr(main._user_keys[debate_id][0:0]) and "gemini_api_key" not in body


def test_debate_streams_usage_and_forgets_the_key_at_the_end(client, monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")  # stub agents: no Gemini calls, cost stays 0
    debate_id = client.post("/debates", json={"ticker": "NWRC", "gemini_api_key": USER_KEY}).json()["debate_id"]
    monkeypatch.setattr(agents, "has_key", lambda: False)  # keep stub lines even with the user's key
    msgs = []
    with client.websocket_connect(f"/ws/debates/{debate_id}") as ws:
        while not msgs or msgs[-1]["type"] not in ("brief", "error"):
            msgs.append(ws.receive_json())
    kinds = [m["type"] for m in msgs]
    assert kinds[-1] == "brief" and "usage" in kinds
    assert kinds.index("usage") > kinds.index("positions")
    assert kinds[-2] == "usage"  # final totals arrive just before the brief
    assert debate_id not in main._user_keys
    assert store.load_debate(debate_id).usage is not None


def test_old_debates_without_usage_still_load():
    d = Debate.model_validate({"id": "x", "ticker": "NWRC"})
    assert d.usage is None and d.model is None
