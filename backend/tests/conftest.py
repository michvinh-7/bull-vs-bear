"""Shared test setup: the real NLI model is slow to load, so every test gets an
instant fake fact-checker unless it swaps in its own (test_verify.py does)."""
import pytest

from app import main, verify


@pytest.fixture(autouse=True)
def fast_fact_check(monkeypatch):
    monkeypatch.setattr(verify, "nli", lambda premise, hypothesis: "entailment")
    monkeypatch.setitem(main.fact_check, "state", "ready")
