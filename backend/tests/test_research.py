"""Guards the checks on what Gemini finds: a debt row is only kept if its quote is really
in the filing and holds the amount, rate and year for the right fiscal year, and news is
only kept if Google's grounding ties it to a search result. No network."""
from datetime import date
from types import SimpleNamespace

import pytest

from app import config, edgar, facts, research, store
from app.filing import Excerpt

FILING = "\n".join([
    "[page 98]",
    "NOTE 8—CORPORATE BORROWINGS",
    "(In millions) | December 31, 2025 | December 31, 2024",
    "Credit Agreement-Term Loans due 2029 (10.731% as of December 31, 2025) | $ | 1,994.2 | $ | 2,014.2",
    "7.5% First Lien Notes due 2029 | 360.0 | 950.0",
    "6.125% Senior Subordinated Notes due 2027 | 125.5 | 125.5",
    "[page 58]",
    "Note 6 — DEBT (in millions)",
    "| Maturities | Stated Interest Rates | December 31, 2024 | December 31, 2025",
    "2017 Notes issuance of $17.0 billion | 2027 - 2057 | 3.15% - 4.25% | 13,000 | 12,000",
    "[page 70]",
    "In 2025 we issued $1.5 billion of 5.25% unsecured senior notes due 2035.",
])


def row(**overrides):
    raw = {
        "name": "7.5% First Lien Notes due 2029",
        "amount_as_written": "360.0",
        "rate_as_written": "7.5%",
        "maturity_year": 2029,
        "seniority": "senior_secured",
        "quote": "7.5% First Lien Notes due 2029 | 360.0 | 950.0",
    }
    return {**raw, **overrides}


def test_instrument_from_a_table_row():
    fields, quote, at = research.check_instrument(row(), FILING, 2025)
    assert fields == {
        "name": "7.5% First Lien Notes due 2029", "amount_usd": 360e6, "seniority": "senior_secured",
        "rate_type": "fixed", "rate": "7.5%", "maturity_year": 2029,
    }
    assert quote == "7.5% First Lien Notes due 2029 | 360.0 | 950.0"


def test_instrument_from_a_sentence():
    fields, _, _ = research.check_instrument(row(
        name="5.25% senior notes due 2035", amount_as_written="$1.5 billion", rate_as_written="5.25%",
        maturity_year=2035, seniority="senior_unsecured",
        quote="In 2025 we issued $1.5 billion of 5.25% unsecured senior notes due 2035.",
    ), FILING, 2025)
    assert fields["amount_usd"] == 1.5e9


@pytest.mark.parametrize("bad", [
    {"quote": "7.5% First Lien Notes due 2029 | 360.0 | 900.0"},  # not in the filing
    {"amount_as_written": "950.0"},                              # last year's column
    {"rate_as_written": "8.5%"},                                 # rate isn't in the quote
    {"maturity_year": 2030},                                     # year isn't in the quote
    {"name": "x", "quote": "In 2025 we issued $1.5 billion of 5.25% unsecured senior notes due 2035.",
     "amount_as_written": "$1.5 billion", "rate_as_written": "5.25%", "maturity_year": 2035,
     "seniority": "senior_secured"},                             # the quote says unsecured
])
def test_instrument_that_doesnt_match_the_filing_is_dropped(bad):
    assert research.check_instrument(row(**bad), FILING, 2025) is None


def test_amount_without_a_unit_is_dropped():
    page = "[page 5]\n7.5% First Lien Notes due 2029 | 360.0 | 950.0"  # no "(in millions)" anywhere
    assert research.check_instrument(row(), page, 2025) is None


def test_bank_loans_float_and_ranges_go_in_the_name():
    loan, _, _ = research.check_instrument(row(
        name="Credit Agreement-Term Loans due 2029", amount_as_written="1,994.2", rate_as_written="10.731%",
        quote="Credit Agreement-Term Loans due 2029 (10.731% as of December 31, 2025) | $ | 1,994.2 | $ | 2,014.2",
    ), FILING, 2025)
    assert loan["rate_type"] == "floating" and loan["amount_usd"] == 1_994.2e6
    # amazon's table puts 2024 first; the 2025 column is the one that counts
    notes, _, _ = research.check_instrument(row(
        name="2017 Notes issuance of $17.0 billion", amount_as_written="12,000", rate_as_written="3.15% - 4.25%",
        maturity_year=2057, seniority="senior_unsecured",
        quote="2017 Notes issuance of $17.0 billion | 2027 - 2057 | 3.15% - 4.25% | 13,000 | 12,000",
    ), FILING, 2025)
    assert notes["amount_usd"] == 12e9 and notes["name"] == "2017 Notes issuance of $17.0 billion (due 2027–2057)"


def web(title, uri="https://vertexaisearch.cloud.google.com/grounding-api-redirect/x"):
    return SimpleNamespace(title=title, uri=uri)


def test_news_uses_the_whole_line_behind_each_grounded_piece():
    answer = "\n".join([
        "* **July 28, 2026**, S&P Global Ratings raised AMC's issuer credit rating to B- from CCC+, citing $51 million of interest savings.",
        "* **May 5, 2026**, AMC said attendance was strong.",  # no figure, still news
        "* **January 2, 2025**, AMC reported $1.0 billion of revenue.",  # too old
        "* **August 3, 2026**, AMC reported 10.2 million moviegoers over five days.",
        "* AMC has $4 billion of debt, analysts said.",  # never grounded
    ])
    supports = [
        ("rating to B- from CCC+, citing $51 million of interest savings.", [web("spglobal.com")]),
        ("S&P Global Ratings raised AMC's issuer credit rating", [web("spglobal.com")]),  # same line again
        ("AMC said attendance was strong.", [web("amctheatres.com")]),
        ("AMC reported $1.0 billion of revenue.", [web("old.com")]),
        ("AMC reported 10.2 million moviegoers over five days.", []),  # no web result behind it
    ]
    news = research.grounded_news(answer, supports, date(2026, 10, 10))
    assert news == [
        {
            "label": "News · spglobal.com · 2026-07-28",
            "url": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/x",
            "excerpt": "July 28, 2026, S&P Global Ratings raised AMC's issuer credit rating to B- from CCC+, citing $51 million of interest savings.",
        },
        {
            "label": "News · amctheatres.com · 2026-05-05",
            "url": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/x",
            "excerpt": "May 5, 2026, AMC said attendance was strong.",
        },
    ]


def test_debt_and_news_become_sources():
    pulled = {
        "fiscal_year_end": "2025-12-31", "tags": {},
        "fields": {"net_income": 1e9, "income_taxes": None, "interest_expense": 1e8, "depreciation_amortization": 2e8,
                   "ebit": 1.2e9, "cash": 5e8, "total_debt": 2e9, "undrawn_revolver": None, "maturities": {},
                   "maturities_after_year_five": None, "floating_debt": None},
        "excerpts": {},
    }
    sheet = facts.fact_sheet_from("AMC", {}, pulled, "https://sec.gov/10k")
    fields, quote, _ = research.check_instrument(row(), FILING, 2025)
    news = [{"label": "spglobal.com · 2026-07-28", "url": "https://x", "excerpt": "S&P raised AMC to B-, citing $51 million of savings."},
            {"label": "x.com", "url": "https://y", "excerpt": "AMC said attendance was strong."}]
    sheet = facts.add_news(facts.add_debt(sheet, [(fields, quote, "98"), (fields, quote, "98")], "https://sec.gov/10k"), news)
    assert [(s.id, s.kind, s.label) for s in sheet.sources] == [
        ("S1", "10-K", "10-K · Financial statements"),
        ("S2", "10-K", "10-K · p. 98"),
        ("N1", "news", "spglobal.com · 2026-07-28"),
        ("N2", "news", "x.com"),
    ]
    # the same quote twice is one source
    assert [d.source_id for d in sheet.debt] == ["S2", "S2"]


def test_gemini_failing_still_gives_a_fact_sheet(monkeypatch):
    pulled = {"fiscal_year_end": "2025-12-31", "tags": {}, "excerpts": {"floating_debt": Excerpt("79% fixed-rate.", "47")},
              "fields": {"net_income": 1e9, "income_taxes": None, "interest_expense": 1e8, "depreciation_amortization": 2e8,
                         "ebit": 1.2e9, "cash": 5e8, "total_debt": 2e9, "undrawn_revolver": None, "maturities": {},
                         "maturities_after_year_five": None, "floating_debt": 4.2e8}}
    monkeypatch.setattr(config, "GEMINI_API_KEY", "fake")
    monkeypatch.setattr(store, "_client", None)
    monkeypatch.setattr(store, "_cache", {})
    monkeypatch.setattr(edgar, "get_cik", lambda t: "1")
    monkeypatch.setattr(edgar, "get_company_facts", lambda cik: {"entityName": "VERIZON"})
    monkeypatch.setattr(edgar, "latest_filing", lambda cik: ("0001", "https://sec.gov/10k"))
    monkeypatch.setattr(edgar, "get_filing_text", lambda url: "[page 1]\ntext")
    monkeypatch.setattr(edgar, "pull_fields", lambda f, t: pulled)
    monkeypatch.setattr(edgar, "fiscal_year_end", lambda f: "2025-12-31")

    def down(*a):
        raise RuntimeError("503 UNAVAILABLE")
    monkeypatch.setattr(research, "debt_instruments", down)
    monkeypatch.setattr(research, "news_items", down)
    sheet = facts.build_fact_sheet("VZ")
    assert sheet.metrics and sheet.debt == [] and not any(s.kind == "news" for s in sheet.sources)


def test_research_uses_the_debates_key_and_counts_its_calls(monkeypatch):
    """A user's own Gemini key (Settings) is used for the debt and news steps too, and those
    calls show up in their usage, even the news call made in a worker thread."""
    from app import agents, usage
    from app.usage import DebateContext, Usage

    used = []

    class FakeModels:
        def generate_content(self, model, contents, config):
            used.append((usage.current().api_key, model))
            meta = SimpleNamespace(prompt_token_count=1000, candidates_token_count=100, thoughts_token_count=0)
            return SimpleNamespace(text='{"instruments": []}', candidates=[], usage_metadata=meta, model_version=model)

    monkeypatch.setattr(agents, "_client_for", lambda ctx: SimpleNamespace(models=FakeModels()))
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")  # no server key: only the user's
    monkeypatch.setattr(store, "_client", None)
    monkeypatch.setattr(store, "_cache", {})
    monkeypatch.setattr(edgar, "get_cik", lambda t: "1")
    monkeypatch.setattr(edgar, "latest_filing", lambda cik: ("0001", "https://sec.gov/10k"))
    monkeypatch.setattr(edgar, "get_company_facts", lambda cik: {"entityName": "VERIZON"})
    monkeypatch.setattr(edgar, "get_filing_text", lambda url: "[page 1]\ntext")
    monkeypatch.setattr(edgar, "pull_fields", lambda f, t: {
        "fiscal_year_end": "2025-12-31", "tags": {}, "excerpts": {},
        "fields": {"net_income": 1e9, "income_taxes": None, "interest_expense": 1e8, "depreciation_amortization": 2e8,
                   "ebit": 1.2e9, "cash": 5e8, "total_debt": 2e9, "undrawn_revolver": None, "maturities": {},
                   "maturities_after_year_five": None, "floating_debt": None}})
    monkeypatch.setattr(edgar, "fiscal_year_end", lambda f: "2025-12-31")

    ctx = DebateContext(model="gemini-3.6-flash", usage=Usage(model="gemini-3.6-flash"), api_key="users-own-key")
    with usage.debate_context(ctx):
        facts.build_fact_sheet("VZ")
    assert sorted(used) == [("users-own-key", "gemini-3.6-flash")] * 2  # debt + news
    assert ctx.usage.calls == 2 and ctx.usage.input_tokens == 2000
