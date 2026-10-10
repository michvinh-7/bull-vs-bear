"""SEC EDGAR: the library. Owner: Person 1.

Free, no key needed, but SEC requires a User-Agent with contact info and
allows at most 10 requests/second.

Useful endpoints
  Ticker -> CIK map:  https://www.sec.gov/files/company_tickers.json
  XBRL numbers:       https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json
  Filing list:        https://data.sec.gov/submissions/CIK##########.json
"""
import httpx
import re
from datetime import date

from . import config

HEADERS = {"User-Agent": config.SEC_USER_AGENT}


_MATURITY_TAGS = [
    "LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths",
    "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearTwo",
    "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearThree",
    "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFour",
    "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFive",
    "LongTermDebtMaturitiesRepaymentsOfPrincipalAfterYearFive"
]

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
            r = httpx.get(f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accessionNum}/{docName}", headers=HEADERS, timeout=30)
            r.raise_for_status()
            return r.text
    # this is a number given to every SEC file, won't necessarily be a 10-k
    raise ValueError(f"{form} not found for CIK: {cik}")

""" 
We need to pull several metrics for the metrics.py file calculations-
this would be coming from the above 10-k, which is in XBRL tagging format

There is some overlap with the information coming in from the company facts, so some metrics will be from there depending 
on ease of access

[NOTE] admittedly, there is an issue since this was not standardized until 2019
for the purposes of this hackathon it will be unlikely that we address filings before that year

We will need to use the following tags:

NetIncomeLoss
ProfitLoss
IncomeTaxExpenseBenefit
InterestExpense/InterestExpenseDebt/InterestExpenseNonoperating
DepreciationDepletionAndAmortization/DepreciationAndAmortization
OperatingIncomeLoss
CashAndCashEquivalentsAtCarryingValue
LongTermDebtCurrent/LongTermDebtNoncurrent/LongTermDebt
ShortTermBorrowings
CommercialPaper
FinanceLeaseLiabilityCurrent/FinanceLeaseLiabilityNoncurrent
LongTermDebtMaturitiesRepaymentsOfPrincipalInNext[VARIABLE] (twelve months, year one, year two, etc...)

"""

# using the given tag, get the entry
def get_entry(facts: dict, tag: str) -> list[dict]:
    try:
        return facts["facts"]["us-gaap"][tag]["units"]["USD"]
    except KeyError:
        return []

def is_annual(e: dict) -> bool:
    if "start" not in e:
        return True
    days = (date.fromisoformat(e["end"])-date.fromisoformat(e["start"])).days
    # fiscal years vary in length - apple, for example, ends on the last sunday of sept
    return 360 <= days <= 372


def lookup(facts: dict, *tags: str, period:str):
    for t in tags:
        matches = []
        for e in get_entry(facts, t):
            if e["end"] == e.get("form") in ("10-K",) and is_annual(e):
                matches.append(e)
        if matches:
            return max(matches, key=lambda e: e["filed"]["value"])
    return None, None
        


"""
Total debt:
LongTermDebtCurrent/LongTermDebtNoncurrent/LongTermDebt + ShortTermBorrowings + CommercialPaper

[NOTE]: unsure on adding the following fields for now- will be doing research 
UnsecuredDebtMember/DebenturesMember
SubordinatedDebtMember/SubordinatedLongTermDebt
FinanceLeaseLiability/CapitalLeaseObligationsNoncurrent

"""
def total_debt(facts: dict, end: str):
    debts = {}
    val, tag = lookup(facts, "LongTermDebt", end=end)
    if val is not None:
        debts[tag] = val
    for t in ("ShortTermBorrowings", "CommercialPaper"):
        v, tg = lookup(facts, t, end=end)
        if v is not None:
            debts[tg] = v
    return (sum(debts.values()) if debts else None), list(debts)






# bc the xbrl file is a pain to parse through, everything above came from the company facts

