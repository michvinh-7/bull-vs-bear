"""Guards the fact sheet builder: pulled EDGAR numbers become sources and metrics,
missing inputs skip a metric instead of inventing one, and an EDGAR outage is told
to the user instead of crashing. Uses fake pull_fields output, so no network."""
from datetime import timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from app import agents, config, edgar, facts, main, research, store
from app.filing import Excerpt
from app.schemas import Debate

URL = "https://www.sec.gov/Archives/edgar/data/1/000/10k.htm"
FACTS = {"entityName": "VERIZON COMMUNICATIONS INC"}


def pulled(**overrides):
    fields = {
        "net_income": 17_174e6,
        "income_taxes": 5_064e6,
        "interest_expense": 6_694e6,
        "depreciation_amortization": 18_349e6,
        "ebit": 29_259e6,
        "cash": 19_048e6,
        "total_debt": 158_150e6,
        "undrawn_revolver": 12_000e6,
        "maturities": {2026: 17_267e6, 2027: 9_569e6, 2028: 13_032e6},
        "maturities_after_year_five": 96_753e6,
        "floating_debt": 33_211.5e6,
    }
    excerpts = {
        "undrawn_revolver": Excerpt("Verizon had $12.0 billion of unused borrowing capacity under our revolving credit facility.", "16"),
        "floating_debt": Excerpt("Approximately 79% of our total debt portfolio consisted of fixed-rate indebtedness.", "47"),
    }
    fields.update(overrides.pop("fields", {}))
    excerpts.update(overrides.pop("excerpts", {}))
    return {"fiscal_year_end": "2025-12-31", "fields": fields, "tags": {}, "excerpts": excerpts}


def test_sources_and_metrics():
    sheet = facts.fact_sheet_from("VZ", FACTS, pulled(), URL)
    assert (sheet.company, sheet.ticker, sheet.as_of) == ("Verizon Communications Inc.", "VZ", "FY2025")
    by_id = {s.id: s for s in sheet.sources}
    assert [s.label for s in sheet.sources] == ["10-K · p. 16", "10-K · p. 47", "10-K · Financial statements"]
    assert all(s.kind == "10-K" and s.url == URL for s in sheet.sources)
    statements = by_id["S3"].excerpt
    assert statements.startswith("For the fiscal year ended December 31, 2025, the company reported net income of $17.2 billion")
    assert "total debt of $158.2 billion" in statements and "$96.8 billion after 2030" in statements
    # numbers that have their own 10-K sentence aren't repeated in the statements source
    assert "undrawn" not in statements

    m = {x.name: x for x in sheet.metrics}
    assert list(m) == ["leverage", "interest_coverage", "floating_rate_pct", "next_maturity_year", "liquidity_usd"]
    assert (m["leverage"].value, m["leverage"].formula) == (3.32, "$158.2 billion debt / $47.6 billion EBITDA")
    # EBIT / interest: $29.3 billion / $6.7 billion
    assert (m["interest_coverage"].value, m["interest_coverage"].formula) == (4.37, "$29.3 billion EBIT / $6.7 billion interest")
    assert (m["floating_rate_pct"].value, m["floating_rate_pct"].source_ids) == (21.0, ["S2", "S3"])
    assert m["next_maturity_year"].value == 2026
    assert (m["liquidity_usd"].value, m["liquidity_usd"].source_ids) == (31_048e6, ["S1", "S3"])


def test_debaters_can_quote_every_number_in_the_sheet():
    sheet = facts.fact_sheet_from("VZ", FACTS, pulled(), URL)
    said = agents._number_text(sheet)
    for n in ("$158.2 billion", "$6.7 billion", "79%", "$12.0 billion", "3.32x"):
        assert agents.numbers(n) <= agents.numbers(said), n


def test_sentence_without_a_figure_is_still_a_source():
    no_figure = Excerpt("We had no borrowings outstanding under the two revolving credit facilities as of December 31, 2025.", "23")
    sheet = facts.fact_sheet_from("AMZN", FACTS, pulled(excerpts={"undrawn_revolver": no_figure}), URL)
    assert (sheet.sources[0].label, sheet.sources[0].excerpt) == ("10-K · p. 23", no_figure.text)
    liquidity = next(x for x in sheet.metrics if x.name == "liquidity_usd")
    assert liquidity.value == 31_048e6 and liquidity.source_ids == ["S1", "S3"]


def test_metrics_with_missing_inputs_are_left_out():
    sheet = facts.fact_sheet_from("AAPL", FACTS, pulled(fields={
        "interest_expense": None, "floating_debt": None, "undrawn_revolver": None, "maturities": {},
    }), URL)
    m = {x.name: x for x in sheet.metrics}
    assert list(m) == ["leverage", "liquidity_usd"]
    assert m["liquidity_usd"].formula == "$19 billion cash, no undrawn revolver reported"


def test_coverage_is_negative_with_an_operating_loss():
    sheet = facts.fact_sheet_from("AMC", FACTS, pulled(fields={"ebit": -17.4e6, "interest_expense": 459.5e6}), URL)
    coverage = next(x for x in sheet.metrics if x.name == "interest_coverage")
    assert (coverage.value, coverage.formula) == (-0.04, "-$17.4 million EBIT / $459.5 million interest")


def test_losses_read_as_losses():
    sheet = facts.fact_sheet_from("AMC", FACTS, pulled(fields={"net_income": -632.4e6, "ebit": -17.4e6}), URL)
    statements = sheet.sources[-1].excerpt
    assert "net loss of $632.4 million" in statements and "operating loss of $17.4 million" in statements


def test_fiscal_label():
    assert facts._fiscal_label("2025-12-31") == "FY2025"
    assert facts._fiscal_label("2025-09-27") == "FY2025"
    assert facts._fiscal_label("2026-01-31") == "FY2025"  # macy's fiscal 2025


def test_sample_company_needs_no_network(monkeypatch):
    monkeypatch.setattr(edgar, "get_cik", lambda t: pytest.fail("called EDGAR"))
    assert facts.build_fact_sheet("nwrc").company == "Northwind Retail Corp"


@pytest.fixture
def sec(monkeypatch):
    """A fake EDGAR and Gemini that count what gets fetched, and an empty in-memory cache."""
    calls = {"facts": 0, "news": 0, "debt": 0}
    state = {"accession": "000073271226000001"}
    monkeypatch.setattr(store, "_client", None)
    monkeypatch.setattr(store, "_cache", {})
    monkeypatch.setattr(config, "GEMINI_API_KEY", "fake")
    monkeypatch.setattr(edgar, "get_cik", lambda t: "0000732712")
    monkeypatch.setattr(edgar, "latest_filing", lambda cik: (state["accession"], URL))

    def company_facts(cik):
        calls["facts"] += 1
        return FACTS
    monkeypatch.setattr(edgar, "get_company_facts", company_facts)
    monkeypatch.setattr(edgar, "get_filing_text", lambda url: "[page 1]\ntext")
    monkeypatch.setattr(edgar, "pull_fields", lambda f, t: pulled())
    monkeypatch.setattr(edgar, "fiscal_year_end", lambda f: "2025-12-31")

    def news(company, ticker):
        calls["news"] += 1
        return [{"label": "News · verizon.com · 2026-07-24", "url": "https://x", "excerpt": f"Verizon news #{calls['news']}."}]
    monkeypatch.setattr(research, "news_items", news)

    def debt(text, company, fy):
        calls["debt"] += 1
        return []
    monkeypatch.setattr(research, "debt_instruments", debt)
    return calls, state


def test_second_debate_uses_the_cache(sec):
    calls, _ = sec
    first = facts.build_fact_sheet("VZ")
    second = facts.build_fact_sheet("vz")
    assert calls == {"facts": 1, "news": 1, "debt": 1}
    assert first == second and [s.excerpt for s in second.sources if s.kind == "news"] == ["Verizon news #1."]


def test_new_10k_rebuilds_and_clears_the_old_one(sec):
    calls, state = sec
    facts.build_fact_sheet("VZ")
    state["accession"] = "000073271227000001"  # verizon files its next 10-K
    facts.build_fact_sheet("VZ")
    assert calls["facts"] == 2
    filing_rows = [k for k in store._cache if k.startswith("VZ|filing|")]
    assert filing_rows == [f"VZ|filing|000073271227000001|{facts.CODE_VERSION}"]


def test_code_change_rebuilds(sec, monkeypatch):
    calls, _ = sec
    facts.build_fact_sheet("VZ")
    monkeypatch.setattr(facts, "CODE_VERSION", "changed")
    facts.build_fact_sheet("VZ")
    assert calls["facts"] == 2


def test_old_news_is_refreshed_without_rebuilding_the_10k_part(sec, monkeypatch):
    calls, _ = sec
    facts.build_fact_sheet("VZ")
    later = facts._now() + facts.NEWS_MAX_AGE + timedelta(minutes=1)
    monkeypatch.setattr(facts, "_now", lambda: later)
    sheet = facts.build_fact_sheet("VZ")
    assert calls == {"facts": 1, "news": 2, "debt": 1}
    assert [s.excerpt for s in sheet.sources if s.kind == "news"] == ["Verizon news #2."]


def gemini_down(*a):
    raise RuntimeError("503 UNAVAILABLE")


def test_everything_fetched_means_no_notices(sec):
    assert facts.build_fact_sheet("VZ").notices == []
    assert facts.build_fact_sheet("VZ").notices == []  # from the cache


def test_failed_debt_step_says_so_and_isnt_cached(sec, monkeypatch):
    calls, _ = sec
    monkeypatch.setattr(research, "debt_instruments", gemini_down)
    sheet = facts.build_fact_sheet("VZ")
    assert sheet.metrics and sheet.debt == []
    assert sheet.notices == [
        "We couldn't read Verizon Communications Inc.'s debt instruments from its 10-K this time, so the debt "
        "table is empty. The rest of the fact sheet is complete; the next debate tries again."
    ]
    assert not any(k.startswith("VZ|filing") for k in store._cache)
    facts.build_fact_sheet("VZ")  # tries again
    assert calls["facts"] == 2


def test_failed_news_refresh_uses_older_news_and_says_so(sec, monkeypatch):
    facts.build_fact_sheet("VZ")
    store._cache["VZ|news"]["fetched_at"] = "2026-10-09T15:00:00+00:00"  # past NEWS_MAX_AGE
    monkeypatch.setattr(facts, "_now", lambda: facts.datetime(2026, 10, 10, 15, tzinfo=facts.timezone.utc))
    monkeypatch.setattr(research, "news_items", gemini_down)
    sheet = facts.build_fact_sheet("VZ")
    assert [s.excerpt for s in sheet.sources if s.kind == "news"] == ["Verizon news #1."]
    assert sheet.notices == ["We couldn't refresh the news just now, so the news here is from October 9, 2026."]


def test_no_news_at_all_says_so(sec, monkeypatch):
    monkeypatch.setattr(research, "news_items", gemini_down)
    sheet = facts.build_fact_sheet("VZ")
    assert not any(s.kind == "news" for s in sheet.sources)
    assert sheet.notices == ["We couldn't get recent news just now, so this debate uses the 10-K only."]


def test_edgar_outage_serves_the_last_sheet_and_says_so(sec, monkeypatch):
    built = facts.build_fact_sheet("VZ")
    store._cache[store._cache["VZ|filing"]["key"]]["built_at"] = "2026-10-08T12:00:00+00:00"

    def down(ticker):
        raise httpx.ConnectError("connection refused")
    monkeypatch.setattr(edgar, "get_cik", down)
    sheet = facts.build_fact_sheet("VZ")
    assert sheet.metrics == built.metrics and sheet.debt == built.debt
    assert sheet.notices == [
        "SEC EDGAR isn't responding right now; it may be down or busy. This debate uses Verizon Communications "
        "Inc.'s fact sheet from October 8, 2026, which may be out of date."
    ]


def test_sec_error_that_isnt_an_outage_doesnt_say_down(sec, monkeypatch):
    def forbidden(ticker):
        request = httpx.Request("GET", "https://www.sec.gov/files/company_tickers.json")
        raise httpx.HTTPStatusError("403", request=request, response=httpx.Response(403, request=request))
    monkeypatch.setattr(edgar, "get_cik", forbidden)
    with pytest.raises(facts.DataUnavailable) as e:
        facts.build_fact_sheet("VZ")
    assert "may be down" not in str(e.value)
    assert "SEC EDGAR returned an error (HTTP 403) when we asked for VZ's filings." in str(e.value)


@pytest.mark.parametrize("status, outage", [(429, True), (503, True), (403, False), (404, False)])
def test_what_counts_as_an_outage(status, outage):
    request = httpx.Request("GET", "https://data.sec.gov")
    assert facts._is_outage(httpx.HTTPStatusError("x", request=request, response=httpx.Response(status, request=request))) is outage
    assert facts._is_outage(httpx.ConnectTimeout("x"))


def edgar_down(monkeypatch):
    def down(ticker):
        raise httpx.ConnectError("connection refused")
    monkeypatch.setattr(store, "_cache", {})
    monkeypatch.setattr(store, "_client", None)
    monkeypatch.setattr(edgar, "get_cik", down)


def test_edgar_outage_says_so(monkeypatch):
    edgar_down(monkeypatch)
    with pytest.raises(facts.DataUnavailable, match="it may be down"):
        facts.build_fact_sheet("VZ")


def test_edgar_outage_reaches_the_debate_page(monkeypatch):
    edgar_down(monkeypatch)
    monkeypatch.setattr(config, "PACING", False)
    monkeypatch.setattr(store, "_debates", {})
    store.save_debate(Debate(id="o1", ticker="VZ", max_turns=2))
    with TestClient(main.app).websocket_connect("/ws/debates/o1") as ws:
        msg = ws.receive_json()
    assert msg["type"] == "error"
    assert msg["message"] == ("We couldn't get VZ's filings. SEC EDGAR isn't responding right now; it may be down "
                              "or busy. Try again in a few minutes, or replay a saved debate.")


def test_capex_to_operating_cash_flow():
    sheet = facts.fact_sheet_from("ORCL", FACTS, pulled(fields={"capex": 55.7e9, "operating_cash_flow": 32.0e9}), URL)
    m = {x.name: x for x in sheet.metrics}
    capex = m["capex_to_cash_flow"]
    assert (capex.label, capex.value, capex.unit) == ("Capex / operating cash flow", 174.1, "pct")
    assert capex.formula == "$55.7 billion capex / $32 billion operating cash flow"
    statements = next(s for s in sheet.sources if s.label == "10-K · Financial statements")
    assert capex.source_ids == [statements.id]
    assert "cash from operations of $32 billion; capital expenditures of $55.7 billion" in statements.excerpt


def test_capex_ratio_skipped_when_operations_burn_cash():
    sheet = facts.fact_sheet_from("AMC", FACTS, pulled(fields={"capex": 0.2e9, "operating_cash_flow": -0.1e9}), URL)
    assert "capex_to_cash_flow" not in {x.name for x in sheet.metrics}
    assert "cash used in operations of $100 million" in sheet.sources[-1].excerpt
