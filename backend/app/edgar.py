"""SEC EDGAR: the library. Owner: Person 1.

Free, no key needed, but SEC requires a User-Agent with contact info and
allows at most 10 requests/second.

Useful endpoints
  Ticker -> CIK map:  https://www.sec.gov/files/company_tickers.json
  XBRL numbers:       https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json
  Filing list:        https://data.sec.gov/submissions/CIK##########.json
"""
import httpx

from . import config

HEADERS = {"User-Agent": config.SEC_USER_AGENT}


def get_cik(ticker: str) -> str:
    """Return the 10-digit zero-padded CIK for a ticker."""
    r = httpx.get("https://www.sec.gov/files/company_tickers.json", headers=HEADERS, timeout=20)
    r.raise_for_status()
    for row in r.json().values():
        if row["ticker"].upper() == ticker.upper():
            return str(row["cik_str"]).zfill(10)
    raise ValueError(f"Ticker not found on EDGAR: {ticker}")


def get_company_facts(cik: str) -> dict:
    """All XBRL-tagged numbers the company has ever reported."""
    r = httpx.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json", headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def get_latest_filing_text(cik: str, form: str = "10-K") -> str:
    """TODO(Person 1): find the latest filing of `form` in the submissions feed,
    download its primary document, and return plain text (keep page markers so
    claims can cite "p. 84")."""
    raise NotImplementedError
