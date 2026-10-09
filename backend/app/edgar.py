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

""" [TODO] as a stretch goal, probably a good idea to look into 10-k vs 10-k/a, that would be the ammended version"""
def get_latest_filing_text(cik: str, form: str = "10-K") -> str:
    r = httpx.get(f"https://data.sec.gov/submissions/CIK{cik}.json", headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    # the recent section includes both the document number (accession) and the doc type in form
    recent = data["filings"]["recent"]
    for i, f in enumerate(recent["form"]):
        if f == form:
            accessionNum = recent["accessionNumber"][i].replace("-", "")
            docName = recent["primaryDocument"][i]
            # url is from https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data
            r = httpx.get(f"https://www.sec.gov/Archives/edgar/data/(cik)/{accessionNum}/{docName}", headers=HEADERS, timeout=30)
            r.raise_for_status()
            return r.text
    # this is a number given to every SEC file, won't necessarily be a 10-k
    raise ValueError(f"{form} not found for CIK: {cik}")
