"""Fact sheet builder. Owner: Person 1.

EDGAR numbers + metrics + Gemini-grounded news -> one FactSheet with sources.
Both debaters argue only from this.
"""
import contextvars
import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx

from . import agents, companies, edgar, metrics, research, store
from .agents import money
from .schemas import DebtInstrument, FactSheet, Metric, Source

APP = Path(__file__).resolve().parent
EXAMPLE = APP / "examples" / "fact_sheet.json"  # copy of shared/examples
# the made-up sample company; it isn't on EDGAR, so it always gets the example sheet
SAMPLE_TICKER = "NWRC"

# A fact sheet is cached in two parts that go stale at different times:
#   - the 10-K part (metrics, 10-K sources, debt rows), until the company files a new 10-K
#     or the code that builds it changes. Keyed by SEC's accession number for the filing and
#     a fingerprint of that code, so neither needs anyone to remember to bump a version.
#   - the news, for NEWS_MAX_AGE.
CODE_VERSION = hashlib.sha256(b"".join(
    (APP / name).read_bytes() for name in ("facts.py", "edgar.py", "filing.py", "research.py", "metrics.py")
)).hexdigest()[:10]
NEWS_MAX_AGE = timedelta(hours=12)


class DataUnavailable(RuntimeError):
    """EDGAR couldn't give us the filings. The message is shown to the user as is."""


def _is_outage(e: httpx.HTTPError) -> bool:
    """SEC unreachable, timing out, overloaded or rate limiting us, as opposed to SEC
    answering with an error about the request itself (a 403 or 404)."""
    if isinstance(e, httpx.HTTPStatusError):
        return e.response.status_code == 429 or e.response.status_code >= 500
    return isinstance(e, httpx.TransportError)


def _edgar_problem(ticker: str, e: httpx.HTTPError) -> str:
    if _is_outage(e):
        return "SEC EDGAR isn't responding right now; it may be down or busy."
    status = e.response.status_code if isinstance(e, httpx.HTTPStatusError) else "unknown"
    return f"SEC EDGAR returned an error (HTTP {status}) when we asked for {ticker}'s filings."


def build_fact_sheet(ticker: str) -> FactSheet:
    """The latest 10-K's numbers, the metrics computed from them, the debt instruments and
    recent news (both found by Gemini, checked by code), and the sources they all cite.
    Anything that couldn't be fetched is said in `notices`, shown on the debate page."""
    ticker = ticker.upper()
    if ticker == SAMPLE_TICKER:
        return FactSheet.model_validate(json.loads(EXAMPLE.read_text(encoding="utf-8")))
    notices: list[str] = []
    try:
        cik = edgar.get_cik(ticker)
        accession, url = edgar.latest_filing(cik)
        key = f"{ticker}|filing|{accession}|{CODE_VERSION}"
        cached = store.load_cached(key)
        if cached:
            sheet = FactSheet.model_validate(cached["sheet"])
            news = _news(sheet.company, ticker, notices)
        else:
            sheet, news = _build(ticker, cik, url, key, notices)
    except httpx.HTTPError as e:
        print(f"[facts] EDGAR request failed for {ticker}: {e!r}")
        problem = _edgar_problem(ticker, e)
        # the last sheet built for this company beats an error, even if it's out of date
        last = store.load_cached(f"{ticker}|filing")
        last = last and store.load_cached(last["key"])
        if not last:
            raise DataUnavailable(f"We couldn't get {ticker}'s filings. {problem} Try again in a few minutes, or replay a saved debate.") from e
        sheet = FactSheet.model_validate(last["sheet"])
        notices = [f"{problem} This debate uses {sheet.company}'s fact sheet from {_day(last['built_at'])}, "
                   "which may be out of date."]
        news = _news(sheet.company, ticker, notices)
    return add_news(sheet, news).model_copy(update={"notices": notices})


def _build(ticker: str, cik: str, url: str, key: str, notices: list[str]) -> tuple[FactSheet, list[dict]]:
    """Builds the 10-K part (and fetches news alongside it), caching the 10-K part."""
    facts = edgar.get_company_facts(cik)
    company = _company_name(ticker, facts)
    news_notices: list[str] = []
    with ThreadPoolExecutor(2) as pool:
        # a search takes a while; start it now. copy_context: the worker thread has to know
        # whose debate this is, to use their Gemini key and count the call in their usage
        news = pool.submit(contextvars.copy_context().run, _news, company, ticker, news_notices)
        text = edgar.get_filing_text(url)
        sheet = fact_sheet_from(ticker, facts, edgar.pull_fields(facts, text), url)
        debt, debt_ok = [], True
        if agents.has_key():
            fiscal_year = date.fromisoformat(edgar.fiscal_year_end(facts)).year
            try:
                debt = research.debt_instruments(text, company, fiscal_year)
            except Exception as e:
                print(f"[facts] skipped debt instruments: {e!r}"[:300])
                debt_ok = False
                notices.append(f"We couldn't read {company}'s debt instruments from its 10-K this time, so the "
                               "debt table is empty. The rest of the fact sheet is complete; the next debate tries again.")
        sheet = add_debt(sheet, debt, url)
        news = news.result()
    notices += news_notices
    # a sheet missing its debt rows because Gemini hiccupped isn't cached, so the next
    # debate tries again instead of being stuck without them until the next 10-K
    if debt_ok:
        store.save_cached(key, {"sheet": sheet.model_dump(), "built_at": _now().isoformat()})
        store.save_cached(f"{ticker}|filing", {"key": key})  # the latest, for when EDGAR is down
        store.delete_cached(f"{ticker}|filing|", keep=key)  # older filings and older code
        store.delete_cached(f"{ticker}@v")  # sheets cached before this scheme
    return sheet, news


def _news(company: str, ticker: str, notices: list[str]) -> list[dict]:
    """research.news_items, fetched again once the cached copy is older than NEWS_MAX_AGE.
    If fetching fails, older news is better than none, and `notices` says which it is."""
    key = f"{ticker}|news"
    cached = store.load_cached(key)
    fresh = cached and _now() - datetime.fromisoformat(cached["fetched_at"]) < NEWS_MAX_AGE
    if fresh or not agents.has_key():
        return cached["items"] if cached else []
    try:
        items = research.news_items(company, ticker)
    except Exception as e:
        print(f"[facts] couldn't refresh news: {e!r}"[:300])
        if cached and cached["items"]:
            notices.append(f"We couldn't refresh the news just now, so the news here is from {_day(cached['fetched_at'])}.")
            return cached["items"]
        notices.append("We couldn't get recent news just now, so this debate uses the 10-K only.")
        return []
    store.save_cached(key, {"items": items, "fetched_at": _now().isoformat()})
    return items


def _day(iso: str) -> str:
    """'2026-10-10T20:15:00+00:00' -> 'October 10, 2026'."""
    d = datetime.fromisoformat(iso)
    return f"{d:%B} {d.day}, {d.year}"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _add_source(sources: list[Source], excerpt: str, label: str, url: str) -> str:
    """The id of the 10-K source with this excerpt, adding it if it's new."""
    for s in sources:
        if s.excerpt == excerpt:
            return s.id
    sources.append(Source(id=f"S{sum(s.id.startswith('S') for s in sources) + 1}", kind="10-K", label=label, url=url, excerpt=excerpt))
    return sources[-1].id


def add_debt(sheet: FactSheet, debt: list[tuple[dict, str, str | None]], url: str) -> FactSheet:
    """Adds research.debt_instruments rows, each citing its 10-K quote."""
    sources = list(sheet.sources)
    rows = [
        DebtInstrument(**fields, source_id=_add_source(sources, quote, f"10-K · p. {page}" if page else "10-K", url))
        for fields, quote, page in debt
    ]
    return sheet.model_copy(update={"sources": sources, "debt": rows})


def add_news(sheet: FactSheet, news: list[dict]) -> FactSheet:
    """Adds research.news_items as N1, N2... sources."""
    items = [Source(id=f"N{i + 1}", kind="news", label=n["label"], url=n["url"], excerpt=n["excerpt"]) for i, n in enumerate(news)]
    return sheet.model_copy(update={"sources": [s for s in sheet.sources if s.kind != "news"] + items})


def fact_sheet_from(ticker: str, facts: dict, pulled: dict, url: str) -> FactSheet:
    """Turns edgar.pull_fields output into a FactSheet. Separate from the fetching so it
    can be tested without the network."""
    f, excerpts, end = pulled["fields"], pulled["excerpts"], pulled["fiscal_year_end"]

    sources: list[Source] = []

    def add(label: str, excerpt: str) -> str:
        # two numbers from the same sentence share one source
        return _add_source(sources, excerpt, label, url)

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
