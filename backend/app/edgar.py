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

from . import config, filing

HEADERS = {"User-Agent": config.SEC_USER_AGENT}

# 10-K/A is an amended 10-K
ANNUAL_FORMS = ("10-K", "10-K/A")


_MATURITY_TAGS = [
    "LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths",
    "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearTwo",
    "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearThree",
    "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFour",
    "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFive",
]
# everything due after year five, lumped together - could be spread over decades,
# so it's kept out of the year-by-year maturities
_AFTER_YEAR_FIVE_TAG = "LongTermDebtMaturitiesRepaymentsOfPrincipalAfterYearFive"

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
def latest_filing_url(cik: str, form: str = "10-K") -> str:
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
            return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accessionNum}/{docName}"
    raise ValueError(f"{form} not found for CIK: {cik}")


def get_latest_filing_text(cik: str, form: str = "10-K") -> str:
    """Plain text of the latest filing, with "[page N]" markers so claims can cite "p. 84"."""
    r = httpx.get(latest_filing_url(cik, form), headers=HEADERS, timeout=60)
    r.raise_for_status()
    return filing.html_to_text(r.text)

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

# each report of their income loss is done per fiscal year, so we can get the dates easily from here
def fiscal_year_end(facts: dict) -> str:
    """End date (YYYY-MM-DD) of the latest fiscal year reported in a 10-K."""
    dates = []
    for tag in ("NetIncomeLoss", "ProfitLoss"):
        for e in get_entry(facts, tag):
            if e.get("form") in ANNUAL_FORMS and e.get("fp") == "FY" and is_annual(e):
                dates.append(e["end"])
    if not dates:
        if "us-gaap" not in facts.get("facts", {}) or "ifrs-full" in facts.get("facts", {}):
            # foreign companies (toyota, etc.) file 20-Fs under IFRS, not 10-Ks under US GAAP
            raise ValueError(f"{facts.get('entityName', 'this company')} doesn't file US GAAP 10-Ks")
        raise ValueError("no annual net income found in company facts")
    return max(dates)



def lookup(facts: dict, *tags: str, end: str) -> tuple[float | None, str | None]:
    """Value for the fiscal year ending `end`, trying each tag in order.

    Returns (value, tag used) so the fact sheet can say where the number came from,
    or (None, None) if none of the tags were reported for that year.
    """
    for t in tags:
        matches = []
        for e in get_entry(facts, t):
            if e["end"] == end and e.get("form") in ANNUAL_FORMS and is_annual(e):
                matches.append(e)
        if matches:
            # the same number shows up again in later 10-Ks as a comparison year; take the newest filing
            latest = max(matches, key=lambda e: e["filed"])
            return latest["val"], t
    return None, None


"""
Total debt:
LongTermDebt (already includes the current portion), or current + noncurrent when a company only
reports the split, + ShortTermBorrowings + CommercialPaper
  current:    DebtCurrent (already includes short-term borrowings and commercial paper, so those
              aren't added again - verizon would double count otherwise), else LongTermDebtCurrent
  noncurrent: LongTermDebtNoncurrent/LongTermDebtAndCapitalLeaseObligations (macy's uses this one; it includes finance leases)

[NOTE]: unsure on adding the following fields for now- will be doing research 
UnsecuredDebtMember/DebenturesMember
SubordinatedDebtMember/SubordinatedLongTermDebt
FinanceLeaseLiability/CapitalLeaseObligationsNoncurrent

"""
def total_debt(facts: dict, end: str) -> tuple[float | None, list[str]]:
    debts = {}
    val, tag = lookup(facts, "LongTermDebt", end=end)
    if val is not None:
        debts[tag] = val
    else:
        noncurrent, noncurrent_tag = lookup(facts, "LongTermDebtNoncurrent", "LongTermDebtAndCapitalLeaseObligations", end=end)
        # the current portion alone is a sliver of the debt, so only use the split when both halves are there
        if noncurrent is not None:
            current, current_tag = lookup(facts, "DebtCurrent", "LongTermDebtCurrent", end=end)
            if current is not None:
                debts[current_tag] = current
            debts[noncurrent_tag] = noncurrent
    if not debts:
        # one combined total (GM), or notes payable (realty income and other REITs)
        val, tag = lookup(
            facts,
            "LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities",
            "DebtAndCapitalLeaseObligations",
            "NotesPayable",
            end=end,
        )
        if val is not None:
            debts[tag] = val
    if not debts:
        # short-term borrowings alone would make a big borrower look tiny, so give up instead
        return None, []
    if "DebtCurrent" not in debts:
        for t in ("ShortTermBorrowings", "CommercialPaper"):
            v, tg = lookup(facts, t, end=end)
            if v is not None:
                debts[tg] = v
    return (sum(debts.values()) if debts else None), list(debts)


# income statement pieces for EBITDA and EBIT (flows over the fiscal year)
def net_income(facts: dict, end: str):
    return lookup(facts, "NetIncomeLoss", "ProfitLoss", end=end)


def income_taxes(facts: dict, end: str):
    return lookup(facts, "IncomeTaxExpenseBenefit", end=end)


def interest_expense(facts: dict, end: str):
    # boeing uses InterestAndDebtExpense
    return lookup(
        facts, "InterestExpense", "InterestExpenseDebt", "InterestExpenseNonoperating", "InterestAndDebtExpense", end=end
    )


def interest_paid(facts: dict, end: str):
    # cash interest paid (from the cash flow statement); a last resort when neither XBRL nor
    # the income statement has interest expense, like kohl's
    return lookup(facts, "InterestPaidNet", end=end)


def depreciation_amortization(facts: dict, end: str) -> tuple[float | None, list[str]]:
    val, tag = lookup(
        facts,
        "DepreciationDepletionAndAmortization",
        "DepreciationAndAmortization",
        "DepreciationAmortizationAndAccretionNet",
        end=end,
    )
    if val is not None:
        return val, [tag]
    # microsoft, tesla, intel only tag the two halves separately
    dep, dep_tag = lookup(facts, "Depreciation", end=end)
    if dep is None:
        return None, []
    amort, amort_tag = lookup(facts, "AmortizationOfIntangibleAssets", end=end)
    return dep + (amort or 0), [dep_tag] + ([amort_tag] if amort_tag else [])


def ebit(facts: dict, end: str):
    # operating income is the usual stand-in for EBIT
    return lookup(facts, "OperatingIncomeLoss", end=end)


def pretax_income(facts: dict, end: str):
    # for companies that don't report operating income (HCA, REITs): EBIT = pre-tax income + interest
    return lookup(
        facts,
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
        end=end,
    )


# balance sheet pieces (a snapshot on the fiscal year end date)
def cash(facts: dict, end: str):
    # target and american airlines only tag cash together with restricted cash
    return lookup(
        facts,
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        end=end,
    )


def undrawn_revolver(facts: dict, end: str) -> tuple[float | None, list[str]]:
    """Revolver capacity still available to borrow."""
    val, tag = lookup(facts, "LineOfCreditFacilityRemainingBorrowingCapacity", end=end)
    if val is not None:
        return val, [tag]
    # most companies only tag the facility size, so subtract whatever is drawn (often nothing)
    size, size_tag = lookup(facts, "LineOfCreditFacilityMaximumBorrowingCapacity", end=end)
    if size is None:
        return None, []
    drawn, drawn_tag = lookup(facts, "LineOfCredit", end=end)
    return size - (drawn or 0), [size_tag] + ([drawn_tag] if drawn_tag else [])


def maturities(facts: dict, end: str) -> dict[int, float]:
    """{year: principal due} from the 10-K's debt maturity table, for metrics.next_big_maturity.

    _MATURITY_TAGS are in order (next 12 months, year two, ... year five), so the nth tag
    is due in fiscal year + n. Pass total_debt to next_big_maturity so the threshold still
    counts the debt due after year five.
    """
    year = date.fromisoformat(end).year
    out = {}
    for n, tag in enumerate(_MATURITY_TAGS, start=1):
        v, _ = lookup(facts, tag, end=end)
        if v is not None:
            out[year + n] = v
    # HCA stopped tagging year one; the current portion of debt is the same thing
    if out and year + 1 not in out:
        v, _ = lookup(facts, "LongTermDebtCurrent", "DebtCurrent", end=end)
        if v is not None:
            out[year + 1] = v
    return out


def maturities_after_year_five(facts: dict, end: str, years_one_to_five: dict[int, float], debt: float | None):
    val, tag = lookup(facts, _AFTER_YEAR_FIVE_TAG, end=end)
    if val is not None:
        return val, [tag]
    # boeing, HCA, nextera tag years 1-5 but not the rest: it's whatever debt is left
    if years_one_to_five and debt and debt > sum(years_one_to_five.values()):
        return debt - sum(years_one_to_five.values()), ["total debt minus years 1-5"]
    return None, []


def pull_fields(facts: dict, text: str | None = None) -> dict:
    """Every number metrics.py needs, for the latest fiscal year, and where each came from.

    `text` is the 10-K from get_latest_filing_text. XBRL doesn't tag floating-rate debt,
    and most companies don't tag their revolver or (like apple) their interest expense, so
    those are read from the filing instead. "tags" says which XBRL tags a number came from;
    "excerpts" has the sentence and page for numbers read from the text, ready to become
    fact sheet sources.
    """
    end = fiscal_year_end(facts)
    # a bank's interest expense is mostly paid on deposits and its "debt" funds its loans, so
    # leverage and coverage would be meaningless; better to say so than show a wrong debate
    if lookup(facts, "Deposits", "InterestExpenseDeposits", end=end)[0]:
        raise ValueError(f"{facts.get('entityName', 'this company')} is a bank; credit metrics here don't apply to banks")
    fields, tags, excerpts = {}, {}, {}

    def from_xbrl(name, val, tag):
        fields[name], tags[name] = val, (tag if isinstance(tag, list) else [tag] if tag else [])

    def from_text(name, val, excerpt):
        fields[name], tags[name], excerpts[name] = val, [], excerpt

    for name, fn in [
        ("net_income", net_income),
        ("income_taxes", income_taxes),
        ("interest_expense", interest_expense),
        ("depreciation_amortization", depreciation_amortization),
        ("ebit", ebit),
        ("cash", cash),
        ("total_debt", total_debt),
        ("undrawn_revolver", undrawn_revolver),
    ]:
        from_xbrl(name, *fn(facts, end))
    fields["maturities"] = maturities(facts, end)
    fields["floating_debt"], tags["floating_debt"] = None, []
    fy = date.fromisoformat(end).year

    if text:
        if fields["interest_expense"] is None:
            val, ex = filing.income_statement_value(text, r"Interest expense(?:, net)?", fy)
            if val is not None:
                from_text("interest_expense", val, ex)
        # the text names the revolver specifically; the XBRL tag can lump in other credit lines
        val, ex = filing.undrawn_revolver(text)
        if val is not None:
            from_text("undrawn_revolver", val, ex)
        val, ex = filing.floating_rate_debt(text, fields["total_debt"])
        if val is not None:
            from_text("floating_debt", val, ex)
        if not fields["maturities"]:
            table, after, ex = filing.debt_maturities(text, fy, fields["total_debt"])
            if table:
                fields["maturities"], excerpts["maturities"] = table, ex
                fields["maturities_after_year_five"], tags["maturities_after_year_five"] = after, []
                excerpts["maturities_after_year_five"] = ex

    if fields["interest_expense"] is None:
        from_xbrl("interest_expense", *interest_paid(facts, end))
    if fields["ebit"] is None and fields["interest_expense"] is not None:
        pretax, pretax_tag = pretax_income(facts, end)
        if pretax is not None:
            fields["ebit"] = pretax + fields["interest_expense"]
            tags["ebit"] = [pretax_tag] + (tags["interest_expense"] or ["interest expense from the 10-K"])
    if "maturities_after_year_five" not in fields:
        from_xbrl(
            "maturities_after_year_five",
            *maturities_after_year_five(facts, end, fields["maturities"], fields["total_debt"]),
        )

    return {"fiscal_year_end": end, "fields": fields, "tags": tags, "excerpts": excerpts}


# bc the xbrl file is a pain to parse through, everything above came from the company facts
