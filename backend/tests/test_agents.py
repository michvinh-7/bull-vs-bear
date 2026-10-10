"""The agents' rules (checked by code, not trusted to Gemini) and the order of a
debate. Gemini is faked: no key, no network."""
import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import agents, config, main, store
from app.schemas import Claim, Debate, FactSheet, LineMessage

EXAMPLES = Path(__file__).resolve().parents[2] / "shared" / "examples"
SHEET = FactSheet.model_validate(json.loads((EXAMPLES / "fact_sheet.json").read_text(encoding="utf-8")))

GOOD_BULL = {
    "text": "This term loan is secured by owned stores and distribution centers. Lenders sit first in line on real assets.",
    "claims": [{"text": "The term loan is secured by owned real property.", "source_id": "S1",
                "quote": "secured by a first-priority lien on owned real property"}],
}


@pytest.fixture
def gemini(monkeypatch):
    """Queue up fake Gemini replies; records every prompt sent."""
    monkeypatch.setattr(config, "GEMINI_API_KEY", "fake")
    replies, prompts = [], []

    def fake(system, user, schema, temperature):
        prompts.append(user)
        return replies.pop(0)

    monkeypatch.setattr(agents, "_generate", fake)
    return replies, prompts


def line(speaker, turn, claims):
    return LineMessage(turn=turn, speaker=speaker, text="...", claims=[
        Claim(id=f"t{turn}c{i}", text=t, source_id=s, label=label) for i, (t, s, label) in enumerate(claims, 1)
    ])


# ---- Turns ----

def test_valid_turn_becomes_a_line(gemini):
    replies, _ = gemini
    replies.append(GOOD_BULL)
    out = agents.generate_turn(SHEET, [], "bull", 1)
    assert out.speaker == "bull" and out.turn == 1
    assert [(c.id, c.source_id, c.label) for c in out.claims] == [("t1c1", "S1", "pending")]


def test_invented_number_is_retried_with_the_error(gemini):
    replies, prompts = gemini
    replies += [
        {**GOOD_BULL, "text": "Rates could fall 200 basis points. The term loan is secured by owned stores."},
        GOOD_BULL,
    ]
    assert agents.generate_turn(SHEET, [], "bull", 1).text == GOOD_BULL["text"]
    assert "REJECTED" in prompts[1] and "200" in prompts[1]


def test_turn_dropped_after_two_failures(gemini):
    replies, _ = gemini
    bad = {**GOOD_BULL, "text": "We recommend you buy this debt. It is safe."}
    replies += [bad, bad]
    assert agents.generate_turn(SHEET, [], "bull", 1) is None


def test_gemini_error_drops_turn_without_retry(gemini, monkeypatch):
    def boom(*a):
        raise RuntimeError("503")
    monkeypatch.setattr(agents, "_generate", boom)
    assert agents.generate_turn(SHEET, [], "bull", 1) is None


@pytest.mark.parametrize("change, error", [
    ({"claims": [{**GOOD_BULL["claims"][0], "quote": "secured by everything they own"}]}, "quote is not copied"),
    ({"claims": [{**GOOD_BULL["claims"][0], "source_id": "S9"}]}, "did not match the schema"),
    ({"claims": []}, "0 claims"),
    ({"text": "Secured. By real property. Owned outright. Every bit."}, "4 sentences"),
    ({"text": "**Secured** by owned real property. Lenders are safe."}, "markdown"),
    ({"text": "Sell nothing, this is secured by owned real property. Lenders are safe."}, "trade call"),
])
def test_rule_violations(gemini, change, error):
    replies, prompts = gemini
    replies += [{**GOOD_BULL, **change}, GOOD_BULL]
    agents.generate_turn(SHEET, [], "bull", 1)
    assert error in prompts[1]


def test_numbers_must_come_from_cited_sources(gemini):
    replies, prompts = gemini
    ok = {"text": "About 62% of borrowings float. That hurts when rates rise.",
          "claims": [{"text": "62% of borrowings are variable rate.", "source_id": "S3",
                      "quote": "Approximately 62% of our outstanding borrowings bear interest at variable rates"}]}
    replies.append(ok)
    assert agents.generate_turn(SHEET, [], "bear", 2) is not None
    # Same number, but citing a source that doesn't contain it
    replies += [{**ok, "claims": [{**GOOD_BULL["claims"][0]}]}, ok]
    agents.generate_turn(SHEET, [], "bear", 2)
    assert "['62']" in prompts[2]


def test_spelled_out_numbers_are_rejected(gemini):
    replies, prompts = gemini
    replies += [{**GOOD_BULL, "text": "The four hundred sixteen million dollar loan is secured. Lenders sit first."}, GOOD_BULL]
    agents.generate_turn(SHEET, [], "bull", 1)
    assert "spelled out" in prompts[1]


def test_python_metrics_may_be_quoted_in_display_form(gemini):
    replies, _ = gemini
    replies.append({"text": "Liquidity is $410 million. That covers a lot.",
                    "claims": [{"text": "Liquidity is $410 million.", "source_id": "S4",
                                "quote": "$110 million of cash and $300 million available"}]})
    assert agents.generate_turn(SHEET, [], "bull", 1) is not None


def test_same_side_cannot_repeat_a_fact_in_new_words(gemini):
    replies, prompts = gemini
    history = [line("bull", 1, [("Northwind had $110 million of cash.", "S4", "verified")])]
    again = {"text": "They hold $110 million of cash. That is real cushion.",
             "claims": [{"text": "Northwind held $110 million of cash at quarter end.", "source_id": "S4",
                         "quote": "we had $110 million of cash"}]}
    replies += [again, GOOD_BULL]
    agents.generate_turn(SHEET, history, "bull", 3, target=None)
    assert "repeats a fact" in prompts[1]


def test_rebuttal_must_engage_the_target(gemini):
    replies, prompts = gemini
    history = [line("bull", 1, [("The term loan is secured by owned real property.", "S1", "pending")])]
    off_topic = {"text": "Same-store sales fell again. That is a bad sign.",
                 "claims": [{"text": "Same-store sales fell for a third quarter.", "source_id": "N2",
                             "quote": "same-store sales fall for third straight quarter"}]}
    on_topic = {**off_topic, "text": "Secured property does not pay interest. Same-store sales fell again."}
    replies += [off_topic, on_topic]
    assert agents.generate_turn(SHEET, history, "bear", 2).text == on_topic["text"]
    assert "does not engage TARGET_CLAIM" in prompts[1]
    assert '"id": "t1c1"' in prompts[0]


def test_question_answers_may_run_longer(gemini):
    replies, _ = gemini
    four = {**GOOD_BULL, "text": "Yes, it is secured. Owned real property backs it. Stores and centers count. Lenders sit first."}
    replies.append(four)
    assert agents.generate_turn(SHEET, [], "bull", 3, question="Is the loan secured?", target=None) is not None


def test_pick_target_prefers_verified_then_pending():
    history = [
        line("bull", 1, [("a", "S1", "unsupported"), ("b", "S2", "verified")]),
        line("bear", 2, [("c", "S3", "contested"), ("d", "S4", "pending")]),
    ]
    assert agents.pick_target(history, "bear").id == "t1c2"
    assert agents.pick_target(history, "bull").id == "t2c2"
    assert agents.pick_target([], "bull") is None


# ---- Moderator ----

HISTORY = [
    line("bull", 1, [("The term loan is secured by owned real property.", "S1", "verified")]),
    line("bear", 2, [("62% of borrowings are variable rate.", "S3", "unsupported")]),
]


def test_cross_examine_directs_a_side_about_a_claim(gemini):
    replies, _ = gemini
    replies.append({"text": "Bear, the checker could not confirm your 62% figure. Where exactly does it come from?",
                    "directed_to": "bear", "about_claim_ids": ["t2c1"]})
    out, side, about = agents.cross_examine(SHEET, HISTORY, 3)
    assert (out.speaker, out.from_user, side, about.id) == ("moderator", False, "bear", "t2c1")


def test_cross_examine_rejects_verdicts_and_bad_ids(gemini):
    replies, prompts = gemini
    replies += [
        {"text": "Bull is winning. Bear, any reply", "directed_to": "bear", "about_claim_ids": ["t2c1"]},
        {"text": "Bear, where does 62% come from?", "directed_to": "bear", "about_claim_ids": ["t2c1"]},
    ]
    assert agents.cross_examine(SHEET, HISTORY, 3) is not None
    assert 'end with "?"' in prompts[1]


def test_relay_question_is_marked_from_user():
    out = agents.relay_question("  Why does floating debt matter? ", 5)
    assert (out.speaker, out.from_user, out.text, out.claims) == ("moderator", True, "Why does floating debt matter?", [])


def test_positions_need_three_cited_points(gemini):
    replies, prompts = gemini
    side = {"thesis": "Secured lenders are well covered.",
            "points": [{"text": "Loan secured by owned property", "source_id": "S1"},
                       {"text": "Revolver matures 2029", "source_id": "S2"},
                       {"text": "Store closures cut costs", "source_id": "N1"}]}
    replies += [{"bull": {**side, "points": side["points"][:2]}, "bear": side}, {"bull": side, "bear": side}]
    pos = agents.generate_positions(SHEET)
    assert len(pos.bull.points) == 3 and "exactly 3 points" in prompts[1]


# ---- Debate order over the WebSocket (stub agents, no key) ----

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    monkeypatch.setattr(config, "VOICE_ENABLED", False)
    monkeypatch.setattr(store, "_client", None)
    monkeypatch.setattr(store, "_debates", {})
    return TestClient(main.app)


def run(client, debate_id, interrupt=None):
    msgs = []
    with client.websocket_connect(f"/ws/debates/{debate_id}") as ws:
        if interrupt:
            ws.send_json({"type": "interrupt", "question": interrupt})
        while True:
            msgs.append(ws.receive_json())
            if msgs[-1]["type"] in ("brief", "error"):
                return msgs


def speakers(msgs):
    return [(m["data"]["speaker"], m["data"]["from_user"]) for m in msgs if m["type"] == "line"]


def test_debate_has_a_halfway_moderator_question(client):
    store.save_debate(Debate(id="d1", ticker="NWRC", max_turns=4))
    msgs = run(client, "d1")
    # The stub moderator questions whoever spoke last (bear); bear answers, then bull.
    assert speakers(msgs) == [("bull", False), ("bear", False), ("moderator", False), ("bear", False), ("bull", False)]
    assert {m["max_turns"] for m in msgs if m["type"] == "turn_start"} == {5}
    assert [m["turn"] for m in msgs if m["type"] == "turn_start"] == [1, 2, 3, 4, 5]
    assert msgs[-1]["type"] == "brief" and store.load_debate("d1").status == "done"


def test_user_interrupt_is_relayed_then_both_sides_answer(client, monkeypatch):
    slow = main.build_fact_sheet
    monkeypatch.setattr(main, "build_fact_sheet", lambda t: (time.sleep(0.3), slow(t))[1])  # let the interrupt land
    store.save_debate(Debate(id="d2", ticker="NWRC", max_turns=2))
    msgs = run(client, "d2", interrupt="Why does floating-rate debt matter?")
    lines = [m["data"] for m in msgs if m["type"] == "line"]
    assert (lines[0]["speaker"], lines[0]["from_user"], lines[0]["text"]) == ("moderator", True, "Why does floating-rate debt matter?")
    assert [l["speaker"] for l in lines[1:3]] == ["bull", "bear"]  # side that was due answers first
    assert len(lines) == 6 and max(m["max_turns"] for m in msgs if m["type"] == "turn_start") == 6


def test_dropped_turn_gets_a_fresh_try_from_the_same_side(client, monkeypatch):
    real, calls = agents.generate_turn, []

    def flaky(sheet, history, side, turn, question=None, target="auto"):
        calls.append(side)
        return None if len(calls) == 2 else real(sheet, history, side, turn, question, target)

    monkeypatch.setattr(agents, "generate_turn", flaky)
    store.save_debate(Debate(id="d4", ticker="NWRC", max_turns=4))
    msgs = run(client, "d4")
    assert calls[:3] == ["bull", "bear", "bear"]
    analysts = [s for s, _ in speakers(msgs) if s != "moderator"]
    assert analysts.count("bull") == analysts.count("bear") == 2


def test_interrupts_are_capped(client, monkeypatch):
    monkeypatch.setattr(config, "MAX_INTERRUPTS", 0)
    slow = main.build_fact_sheet
    monkeypatch.setattr(main, "build_fact_sheet", lambda t: (time.sleep(0.3), slow(t))[1])
    store.save_debate(Debate(id="d3", ticker="NWRC", max_turns=2))
    msgs = run(client, "d3", interrupt="Anything?")
    assert not any(f for _, f in speakers(msgs))
