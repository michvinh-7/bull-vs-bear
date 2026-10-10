"""Guards the fact sheet builder: pulled EDGAR numbers become sources and metrics,
missing inputs skip a metric instead of inventing one, and an EDGAR outage is told
to the user instead of crashing. Uses fake pull_fields output, so no network."""
import httpx
import pytest
from fastapi.testclient import TestClient

from app import agents, config, edgar, facts, main, store
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
    assert m["interest_coverage"].value == 7.11
    assert (m["floating_rate_pct"].value, m["floating_rate_pct"].source_ids) == (21.0, ["S2", "S3"])
    assert m["next_maturity_year"].value == 2026
    assert (m["liquidity_usd"].value, m["liquidity_usd"].source_ids) == (31_048e6, ["S1", "S3"])


def test_debaters_can_quote_every_number_in_the_sheet():
    sheet = facts.fact_sheet_from("VZ", FACTS, pulled(), URL)
    said = agents._number_text(sheet)
    for n in ("$158.2 billion", "$6.7 billion", "79%", "$12.0 billion", "3.32x"):
        assert agents.numbers(n) <= agents.numbers(said), n


def test_sentence_without_a_figure_is_skipped():
    no_figure = Excerpt("We had no borrowings outstanding under the two revolving credit facilities as of December 31, 2025.", "23")
    sheet = facts.fact_sheet_from("AMZN", FACTS, pulled(excerpts={"undrawn_revolver": no_figure}), URL)
    assert not any("no borrowings" in s.excerpt for s in sheet.sources)
    liquidity = next(x for x in sheet.metrics if x.name == "liquidity_usd")
    # the value still counts; the metric cites only what's left (the statements source)
    assert liquidity.value == 31_048e6 and liquidity.source_ids == ["S2"]


def test_metrics_with_missing_inputs_are_left_out():
    sheet = facts.fact_sheet_from("AAPL", FACTS, pulled(fields={
        "interest_expense": None, "floating_debt": None, "undrawn_revolver": None, "maturities": {},
    }), URL)
    m = {x.name: x for x in sheet.metrics}
    assert list(m) == ["leverage", "liquidity_usd"]
    assert m["liquidity_usd"].formula == "$19 billion cash, no undrawn revolver reported"


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


def test_cached_sheet_skips_edgar(monkeypatch):
    sheet = facts.fact_sheet_from("VZ", FACTS, pulled(), URL)
    monkeypatch.setattr(store, "_fact_sheets", {"VZ": sheet})
    monkeypatch.setattr(store, "_client", None)
    monkeypatch.setattr(edgar, "get_cik", lambda t: pytest.fail("called EDGAR"))
    assert facts.build_fact_sheet("vz") is sheet


def edgar_down(monkeypatch):
    def down(ticker):
        raise httpx.ConnectError("connection refused")
    monkeypatch.setattr(store, "_fact_sheets", {})
    monkeypatch.setattr(store, "_client", None)
    monkeypatch.setattr(edgar, "get_cik", down)


def test_edgar_outage_says_so(monkeypatch):
    edgar_down(monkeypatch)
    with pytest.raises(facts.DataUnavailable, match="EDGAR may be down"):
        facts.build_fact_sheet("VZ")


def test_edgar_outage_reaches_the_debate_page(monkeypatch):
    edgar_down(monkeypatch)
    monkeypatch.setattr(config, "PACING", False)
    monkeypatch.setattr(store, "_debates", {})
    store.save_debate(Debate(id="o1", ticker="VZ", max_turns=2))
    with TestClient(main.app).websocket_connect("/ws/debates/o1") as ws:
        msg = ws.receive_json()
    assert msg["type"] == "error"
    assert msg["message"].startswith("We couldn't get VZ's filings from SEC EDGAR. EDGAR may be down or busy")
