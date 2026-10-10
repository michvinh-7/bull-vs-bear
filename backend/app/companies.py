"""Company list and search for the home page. Owner: Person 2.

Search runs on SEC's ticker list (~10k public companies), downloaded once and
kept in memory. If SEC is unreachable, search falls back to the demo companies
and any ticker is allowed, so an SEC outage never blocks the demo.
"""
import threading

import httpx
from pydantic import BaseModel

from . import config

SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"


class Company(BaseModel):
    ticker: str
    company: str
    tagline: str | None = None


DEMO_COMPANIES = [
    # one of each: a fortress balance sheet, a big steady borrower, and a stressed one
    Company(ticker="AMZN", company="Amazon.com, Inc.", tagline="AI spending spree vs. a fortress balance sheet"),
    Company(ticker="VZ", company="Verizon Communications Inc.", tagline="Steady subscriber cash vs. a giant debt load"),
    Company(ticker="AMC", company="AMC Entertainment Holdings, Inc.", tagline="Box office comeback vs. a mountain of debt"),
]

_sec: list[Company] | None = None
_lock = threading.Lock()


def _sec_companies() -> list[Company]:
    """SEC's list, fetched on first use. Empty if SEC can't be reached (retried next call)."""
    global _sec
    with _lock:
        if _sec is None:
            try:
                r = httpx.get(SEC_TICKERS_URL, headers={"User-Agent": config.SEC_USER_AGENT}, timeout=20)
                r.raise_for_status()
                _sec = [Company(ticker=row["ticker"].upper(), company=row["title"]) for row in r.json().values()]
            except (httpx.HTTPError, ValueError, KeyError):
                return []
        return _sec


def search(q: str, limit: int = 10) -> list[Company]:
    """Demo companies first, then exact ticker, ticker prefix, name prefix, name contains."""
    q = q.strip().upper()
    if not q:
        return []
    demo_tickers = {c.ticker for c in DEMO_COMPANIES}
    pool = DEMO_COMPANIES + [c for c in _sec_companies() if c.ticker not in demo_tickers]

    def rank(c: Company) -> int | None:
        name = c.company.upper()
        if c.ticker == q:
            return 0
        if c.ticker.startswith(q):
            return 1
        if name.startswith(q):
            return 2
        if q in name:
            return 3
        return None

    hits = [(r, i, c) for i, c in enumerate(pool) if (r := rank(c)) is not None]
    hits.sort(key=lambda h: (h[2].ticker not in demo_tickers, h[0], h[1]))
    # One row per company: SEC lists the main ticker first, then preferred shares (F, F-PB, F-PC...).
    seen, results = set(), []
    for _, _, c in hits:
        if c.company.upper() not in seen:
            seen.add(c.company.upper())
            results.append(c)
    return results[:limit]


def is_known(ticker: str) -> bool:
    """True for demo tickers and anything on SEC's list. True when SEC is unreachable."""
    ticker = ticker.upper()
    if any(c.ticker == ticker for c in DEMO_COMPANIES):
        return True
    sec = _sec_companies()
    return not sec or any(c.ticker == ticker for c in sec)
