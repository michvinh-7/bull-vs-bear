"""Fact sheet builder. Owner: Person 1.

EDGAR numbers + metrics + Gemini-grounded news -> one FactSheet with sources.
Both debaters argue only from this.
"""
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import httpx

from . import companies, config, edgar, metrics, research, store
from .agents import money
from .schemas import DebtInstrument, FactSheet, Metric, Source

EXAMPLE = Path(__file__).resolve().parent / "examples" / "fact_sheet.json"  # copy of shared/examples
# the made-up sample company; it isn't on EDGAR, so it always gets the example sheet
SAMPLE_TICKER = "NWRC"
# bump when the sheet's contents change, so sheets cached by older code are rebuilt
SHEET_VERSION = 6




class DataUnavailable(RuntimeError):
    """EDGAR couldn't be reached. The message is shown to the user as is."""


def build_fact_sheet(ticker: str) -> FactSheet:
    """The latest 10-K's numbers, the metrics computed from them, the debt instruments and
    recent news (both found by Gemini, checked by code), and the sources they all cite."""
    ticker = ticker.upper()
    if ticker == SAMPLE_TICKER:
        return FactSheet.model_validate(json.loads(EXAMPLE.read_text(encoding="utf-8")))
    # demo companies are built once, then served from the cache
    key = f"{ticker}@v{SHEET_VERSION}"
    if cached := store.load_fact_sheet(key):
        return cached

    try:
        cik = edgar.get_cik(ticker)
        facts = edgar.get_company_facts(cik)
        url = edgar.latest_filing_url(cik)
        text = edgar.get_latest_filing_text(cik)
    except httpx.HTTPError as e:
        print(f"[facts] EDGAR request failed for {ticker}: {e!r}")
        raise DataUnavailable(
            f"We couldn't get {ticker}'s filings from SEC EDGAR. EDGAR may be down or busy right now; "
            "try again in a few minutes, or replay a saved debate."
        ) from e

    sheet = fact_sheet_from(ticker, facts, edgar.pull_fields(facts, text), url)
    if config.GEMINI_API_KEY:
        fiscal_year = date.fromisoformat(edgar.fiscal_year_end(facts)).year
        with ThreadPoolExecutor(2) as pool:
            debt = pool.submit(research.debt_instruments, text, sheet.company, fiscal_year)
            news = pool.submit(research.news_items, sheet.company, ticker)
            sheet = add_research(sheet, _or_nothing(debt, "debt instruments"), _or_nothing(news, "news"), url)
    store.save_fact_sheet(sheet, key)
    return sheet


def _or_nothing(job, what: str) -> list:
    """Gemini's part is extra: if it fails, the sheet is still built from the 10-K alone."""
    try:
        return job.result()
    except Exception as e:
        print(f"[facts] skipped {what}: {e!r}"[:300])
        return []


def add_research(sheet: FactSheet, debt: list[tuple[dict, str, str | None]], news: list[dict], url: str) -> FactSheet:
    """Adds research.debt_instruments rows (citing their 10-K quote) and research.news_items
    (as N1, N2... sources) to a fact sheet."""
    sources = list(sheet.sources)

    def source_for(excerpt: str, label: str) -> str:
        for s in sources:
            if s.excerpt == excerpt:
                return s.id
        sources.append(Source(id=f"S{sum(s.id.startswith('S') for s in sources) + 1}", kind="10-K", label=label, url=url, excerpt=excerpt))
        return sources[-1].id

    rows = [
        DebtInstrument(**fields, source_id=source_for(quote, f"10-K · p. {page}" if page else "10-K"))
        for fields, quote, page in debt
    ]
    for i, item in enumerate(news):
        sources.append(Source(id=f"N{i + 1}", kind="news", label=item["label"], url=item["url"], excerpt=item["excerpt"]))
    return sheet.model_copy(update={"sources": sources, "debt": rows})


def fact_sheet_from(ticker: str, facts: dict, pulled: dict, url: str) -> FactSheet:
    """Turns edgar.pull_fields output into a FactSheet. Separate from the fetching so it
    can be tested without the network."""
    f, excerpts, end = pulled["fields"], pulled["excerpts"], pulled["fiscal_year_end"]

    sources: list[Source] = []

    def add(label: str, excerpt: str) -> str:
        for s in sources:
            if s.excerpt == excerpt:  # two numbers from the same sentence share one source
                return s.id
        sources.append(Source(id=f"S{len(sources) + 1}", kind="10-K", label=label, url=url, excerpt=excerpt))
        return sources[-1].id

    # numbers read from the 10-K text cite their own sentence and page, even one with no
    # figure in it ("We had no borrowings outstanding under ..."): it's still the evidence
    from_text = {name: add(f"10-K · p. {ex.page}" if ex.page else "10-K", ex.text) for name, ex in excerpts.items()}
    # XBRL numbers have no sentence of their own, so one source states them plainly
    statements = add("10-K · Financial statements", _statement_excerpt(f, excerpts, end))

    def cite(*names: str) -> list[str]:
        return sorted({from_text.get(n, statements) for n in names})

    return FactSheet(
        company=_company_name(ticker, facts),
        ticker=ticker,
        as_of=_fiscal_label(end),
        sources=sources,
        metrics=_metrics(f, cite),
    )


def _metrics(f: dict, cite) -> list[Metric]:
    """The five metrics the debate is built on, skipping any whose inputs weren't found."""
    out = []
    debt, interest = f["total_debt"], f["interest_expense"]
    ebitda = None
    if f["ebit"] is not None and f["depreciation_amortization"] is not None:
        ebitda = metrics.ebitda(f["ebit"], f["depreciation_amortization"])
    ebitda_sources = ("ebit", "depreciation_amortization")

    if debt and ebitda and ebitda > 0:
        out.append(Metric(
            name="leverage", label="Debt-to-EBITDA", unit="x",
            value=metrics.leverage(debt, ebitda),
            formula=f"{money(debt)} debt / {money(ebitda)} EBITDA",
            source_ids=cite("total_debt", *ebitda_sources),
        ))
    if ebitda is not None and interest:
        out.append(Metric(
            name="interest_coverage", label="Interest coverage", unit="x",
            value=metrics.interest_coverage(ebitda, interest),
            formula=f"{money(ebitda)} EBITDA / {money(interest)} interest",
            source_ids=cite("interest_expense", *ebitda_sources),
        ))
    if debt and f["floating_debt"] is not None:
        out.append(Metric(
            name="floating_rate_pct", label="Floating-rate debt", unit="pct",
            value=metrics.floating_rate_pct(f["floating_debt"], debt),
            formula=f"{money(f['floating_debt'])} floating / {money(debt)} debt",
            source_ids=cite("floating_debt", "total_debt"),
        ))
    if f["maturities"]:
        year = metrics.next_big_maturity(f["maturities"], total_debt=debt)
        if year is not None:
            due = f["maturities"][year]
            out.append(Metric(
                name="next_maturity_year", label="Next big maturity", unit="year",
                value=year,
                formula=f"{money(due)} due in {year}" + (f" of {money(debt)} total debt" if debt else ""),
                source_ids=cite("maturities", "total_debt"),
            ))
    if f["cash"] is not None:
        revolver = f["undrawn_revolver"]
        out.append(Metric(
            name="liquidity_usd", label="Total immediate liquidity", unit="usd",
            value=metrics.liquidity(f["cash"], revolver or 0),
            formula=f"{money(f['cash'])} cash + {money(revolver)} undrawn revolver" if revolver
            else f"{money(f['cash'])} cash, no undrawn revolver reported",
            source_ids=cite("cash", "undrawn_revolver") if revolver else cite("cash"),
        ))
    return out


def _statement_excerpt(f: dict, excerpts: dict, end: str) -> str:
    """One plain sentence with the numbers that came from XBRL rather than a 10-K sentence.

    Written the way money() says amounts ("$69.3 billion"), since debaters may only
    quote numbers that appear in a source.
    """
    def said(name: str) -> bool:
        return f.get(name) is not None and name not in excerpts

    parts = []
    if said("net_income"):
        v = f["net_income"]
        parts.append(f"net {'income' if v >= 0 else 'loss'} of {money(abs(v))}")
    if said("ebit"):
        v = f["ebit"]
        parts.append(f"operating {'income' if v >= 0 else 'loss'} of {money(abs(v))}")
    if said("depreciation_amortization"):
        parts.append(f"depreciation and amortization of {money(f['depreciation_amortization'])}")
    if said("interest_expense"):
        parts.append(f"interest expense of {money(f['interest_expense'])}")
    if said("total_debt"):
        parts.append(f"total debt of {money(f['total_debt'])}")
    if said("cash"):
        parts.append(f"cash and cash equivalents of {money(f['cash'])}")
    if said("undrawn_revolver"):
        parts.append(f"undrawn revolving credit of {money(f['undrawn_revolver'])}")
    sentence = f"For the fiscal year ended {_long_date(end)}, the company reported " + "; ".join(parts) + "."
    if f["maturities"] and "maturities" not in excerpts:
        due = [f"{money(v)} in {y}" for y, v in sorted(f["maturities"].items())]
        if f.get("maturities_after_year_five"):
            due.append(f"{money(f['maturities_after_year_five'])} after {date.fromisoformat(end).year + 5}")
        sentence += " Debt principal comes due as follows: " + ", ".join(due) + "."
    return sentence


def _company_name(ticker: str, facts: dict) -> str:
    for c in companies.DEMO_COMPANIES:
        if c.ticker == ticker:
            return c.company
    return facts.get("entityName") or ticker


def _fiscal_label(end: str) -> str:
    """'2025-12-31' -> 'FY2025'. A year ending January-March is named for the year before
    (Macy's year ending January 2026 is its fiscal 2025)."""
    d = date.fromisoformat(end)
    return f"FY{d.year - 1 if d.month <= 3 else d.year}"


def _long_date(end: str) -> str:
    d = date.fromisoformat(end)
    return f"{d:%B} {d.day}, {d.year}"
