"""Shared test setup: the real NLI model is slow to load, so every test gets an
instant fake fact-checker unless it swaps in its own (test_verify.py does).
Debates don't need a user's own key unless a test turns REQUIRE_USER_KEY back on."""
import pytest

from app import config, main, verify


@pytest.fixture(autouse=True)
def fast_fact_check(monkeypatch):
    monkeypatch.setattr(verify, "nli", lambda premise, hypothesis: "entailment")
    monkeypatch.setitem(main.fact_check, "state", "ready")


@pytest.fixture(autouse=True)
def team_key_allowed(monkeypatch):
    monkeypatch.setattr(config, "REQUIRE_USER_KEY", False)
