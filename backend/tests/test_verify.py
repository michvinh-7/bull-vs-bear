"""Guards the fact-check contract: check_claims labels every claim verified,
contested or unsupported, and a crash leaves the debate running with "pending".
The NLI model is faked so these run fast and without torch."""

import pytest

from app import main, verify
from app.schemas import Claim, FactSheet, Source

SHEET = FactSheet(
    company="Acme",
    ticker="ACME",
    as_of="FY2025",
    sources=[Source(id="S1", kind="10-K", label="10-K", excerpt="Revenue grew 12% to $4.1B in FY2025.")],
)


def claims():
    return [
        Claim(id="t1c1", text="Revenue increased.", source_id="S1"),
        Claim(id="t1c2", text="Revenue fell.", source_id="S1"),
        Claim(id="t1c3", text="The CEO resigned.", source_id="S1"),
        Claim(id="t1c4", text="Revenue grew 12%.", source_id="S9"),
        Claim(id="t1c5", text="Revenue grew 12%.", source_id=None),
    ]


def fake_nli(premise, hypothesis):
    return {"Revenue increased.": "entailment", "Revenue fell.": "contradiction"}.get(hypothesis, "neutral")


def test_every_claim_gets_a_final_label(monkeypatch):
    monkeypatch.setattr(verify, "nli", fake_nli)
    labels = [c.label for c in verify.check_claims(claims(), SHEET)]
    assert labels == ["verified", "contested", "unsupported", "unsupported", "unsupported"]


def test_made_up_source_is_cleared(monkeypatch):
    monkeypatch.setattr(verify, "nli", fake_nli)
    assert verify.check_claims(claims(), SHEET)[3].source_id is None


def test_model_failure_raises(monkeypatch):
    def broken(premise, hypothesis):
        raise RuntimeError("model failed to load")

    monkeypatch.setattr(verify, "nli", broken)
    with pytest.raises(RuntimeError):
        verify.check_claims(claims(), SHEET)


def test_crash_leaves_claims_pending(monkeypatch):
    calls = []

    def flaky(premise, hypothesis):
        # Succeed once, then crash, so a half-done check must not leak through.
        if calls:
            raise RuntimeError("model crashed")
        calls.append(hypothesis)
        return "entailment"

    monkeypatch.setattr(verify, "nli", flaky)
    result = main._check_claims(claims(), SHEET)
    assert [c.label for c in result] == ["pending"] * 5


def test_verified_needs_the_numbers_in_the_source(monkeypatch):
    # the NLI model passed "Leverage is 5.8x" against a sentence with no 5.8 in it
    monkeypatch.setattr(verify, "nli", lambda premise, hypothesis: "entailment")
    right = Claim(id="a", text="Revenue grew 12%.", source_id="S1")
    wrong = Claim(id="b", text="Leverage is 5.8x.", source_id="S1")
    assert [c.label for c in verify.check_claims([right, wrong], SHEET)] == ["verified", "unsupported"]


def test_premise_names_the_company_and_its_metrics(monkeypatch):
    from app.schemas import Metric

    seen = []
    monkeypatch.setattr(verify, "nli", lambda premise, hypothesis: seen.append(premise) or "neutral")
    sheet = SHEET.model_copy(update={"metrics": [
        Metric(name="leverage", label="Leverage", value=13.6, unit="x", formula="$4 billion debt / $296 million EBITDA", source_ids=["S1"]),
    ]})
    verify.check_claim(Claim(id="a", text="Leverage is 13.6x.", source_id="S1"), sheet)
    assert seen == ["From Acme's filing: Revenue grew 12% to $4.1B in FY2025. "
                    "Leverage was 13.6x ($4 billion debt / $296 million EBITDA)."]
