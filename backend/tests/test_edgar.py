"""Guards the company-facts parsing that feeds metrics.py. Uses a tiny fake
companyfacts payload shaped like the real one, so no network is needed."""
from app import edgar, metrics


def year(val, end="2026-01-31", start="2025-02-02", form="10-K", filed="2026-03-20", fp="FY"):
    """One annual (flow) entry, like net income for the fiscal year."""
    return {"start": start, "end": end, "val": val, "form": form, "filed": filed, "fp": fp}


def snap(val, end="2026-01-31", form="10-K", filed="2026-03-20"):
    """One balance-sheet (instant) entry, like cash on the fiscal year end date."""
    return {"end": end, "val": val, "form": form, "filed": filed, "fp": "FY"}


def facts(**tags):
    return {"facts": {"us-gaap": {t: {"units": {"USD": entries}} for t, entries in tags.items()}}}


FACTS = facts(
    NetIncomeLoss=[
        year(500, end="2025-02-01", start="2024-02-04", filed="2025-03-20"),
        year(600),
        year(150, start="2025-11-02", form="10-Q", fp="Q4"),  # a quarter, not the year
    ],
    IncomeTaxExpenseBenefit=[year(200)],
    InterestExpense=[year(100)],
    DepreciationAndAmortization=[year(300)],
    OperatingIncomeLoss=[year(900)],
    CashAndCashEquivalentsAtCarryingValue=[snap(250)],
    LongTermDebtCurrent=[snap(50)],
    LongTermDebtNoncurrent=[snap(1_950)],
    LineOfCreditFacilityMaximumBorrowingCapacity=[snap(1_000)],
    LineOfCredit=[snap(200)],
    LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths=[snap(50)],
    LongTermDebtMaturitiesRepaymentsOfPrincipalInYearThree=[snap(1_500)],
    LongTermDebtMaturitiesRepaymentsOfPrincipalAfterYearFive=[snap(450)],
)


def test_fiscal_year_end_is_latest_annual():
    assert edgar.fiscal_year_end(FACTS) == "2026-01-31"


def test_lookup_ignores_quarters_and_takes_newest_filing():
    restated = facts(NetIncomeLoss=[year(600), year(610, filed="2027-03-20")])
    assert edgar.lookup(FACTS, "NetIncomeLoss", end="2026-01-31") == (600, "NetIncomeLoss")
    assert edgar.lookup(restated, "NetIncomeLoss", end="2026-01-31") == (610, "NetIncomeLoss")


def test_lookup_falls_back_through_tags():
    assert edgar.lookup(FACTS, "ProfitLoss", "NetIncomeLoss", end="2026-01-31") == (600, "NetIncomeLoss")
    assert edgar.lookup(FACTS, "ProfitLoss", end="2026-01-31") == (None, None)


def test_pull_fields():
    out = edgar.pull_fields(FACTS)
    f = out["fields"]
    assert out["fiscal_year_end"] == "2026-01-31"
    assert (f["net_income"], f["income_taxes"], f["interest_expense"]) == (600, 200, 100)
    assert (f["depreciation_amortization"], f["ebit"], f["cash"]) == (300, 900, 250)
    # no LongTermDebt tag, so current + noncurrent
    assert f["total_debt"] == 2_000
    assert out["tags"]["total_debt"] == ["LongTermDebtCurrent", "LongTermDebtNoncurrent"]
    # facility size minus what's drawn
    assert f["undrawn_revolver"] == 800
    assert f["maturities"] == {2027: 50, 2029: 1_500}
    assert f["maturities_after_year_five"] == 450


def test_debt_current_isnt_double_counted():
    # DebtCurrent already includes short-term borrowings, like verizon reports it
    vz = facts(
        DebtCurrent=[snap(100)],
        LongTermDebtCurrent=[snap(100)],
        ShortTermBorrowings=[snap(10)],
        LongTermDebtAndCapitalLeaseObligations=[snap(900)],
    )
    assert edgar.total_debt(vz, "2026-01-31") == (1_000, ["DebtCurrent", "LongTermDebtAndCapitalLeaseObligations"])


def test_after_year_five_is_not_a_maturity_wall():
    # most of the debt is due "after year five", but that's not one year, so no wall
    lumpy = facts(
        NetIncomeLoss=[year(600)],
        LongTermDebt=[snap(1_000)],
        LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths=[snap(20)],
        LongTermDebtMaturitiesRepaymentsOfPrincipalAfterYearFive=[snap(980)],
    )
    f = edgar.pull_fields(lumpy)["fields"]
    assert f["maturities"] == {2027: 20}
    assert metrics.next_big_maturity(f["maturities"], total_debt=f["total_debt"]) is None


def test_fields_feed_metrics():
    f = edgar.pull_fields(FACTS)["fields"]
    ebitda = metrics.ebitda(f["ebit"], f["depreciation_amortization"])
    assert ebitda == 1_200
    assert metrics.leverage(f["total_debt"], ebitda) == 1.67
    assert metrics.next_big_maturity(f["maturities"], total_debt=f["total_debt"]) == 2029
    assert metrics.liquidity(f["cash"], f["undrawn_revolver"]) == 1_050


def test_text_fills_what_xbrl_doesnt_tag():
    no_interest = facts(
        NetIncomeLoss=[year(600)],
        LongTermDebt=[snap(1_000_000_000)],
    )
    text = "\n".join([
        "[page 31]",
        "Approximately 40% of our outstanding borrowings bear interest at variable rates.",
        "[page 37]",
        "CONSOLIDATED STATEMENTS OF OPERATIONS",
        "| 2023 | 2024 | 2025",
        "Interest expense | (3,182) | (2,406) | (2,274)",
        "[page 50]",
        "We had $750 million of availability under our revolving credit facility.",
    ])
    out = edgar.pull_fields(no_interest, text)
    f, ex = out["fields"], out["excerpts"]
    assert f["interest_expense"] == 2_274_000_000 and ex["interest_expense"].page == "37"
    assert f["floating_debt"] == 400_000_000 and ex["floating_debt"].page == "31"
    assert f["undrawn_revolver"] == 750_000_000 and ex["undrawn_revolver"].page == "50"


def test_banks_and_foreign_filers_get_a_clear_error():
    import pytest

    bank = facts(NetIncomeLoss=[year(600)], Deposits=[snap(2_000_000)])
    with pytest.raises(ValueError, match="bank"):
        edgar.pull_fields(bank)
    foreign = {"entityName": "TOYOTA", "facts": {"ifrs-full": {}, "us-gaap": {}}}
    with pytest.raises(ValueError, match="US GAAP"):
        edgar.pull_fields(foreign)


def test_missing_xbrl_pieces_fall_back():
    sparse = facts(
        NetIncomeLoss=[year(600)],
        # no OperatingIncomeLoss: pre-tax income + interest
        IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest=[year(700)],
        InterestAndDebtExpense=[year(100)],
        # no combined D&A: depreciation + amortization
        Depreciation=[year(250)],
        AmortizationOfIntangibleAssets=[year(50)],
        CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents=[snap(90)],
        NotesPayable=[snap(1_000)],
        # years 2-5 tagged, year 1 and "after year five" aren't
        LongTermDebtCurrent=[snap(100)],
        LongTermDebtMaturitiesRepaymentsOfPrincipalInYearTwo=[snap(200)],
        LongTermDebtMaturitiesRepaymentsOfPrincipalInYearThree=[snap(300)],
    )
    f = edgar.pull_fields(sparse)["fields"]
    assert (f["ebit"], f["interest_expense"], f["depreciation_amortization"], f["cash"]) == (800, 100, 300, 90)
    assert f["total_debt"] == 1_000
    assert f["maturities"] == {2027: 100, 2028: 200, 2029: 300}
    assert f["maturities_after_year_five"] == 400


def test_short_term_borrowings_alone_arent_total_debt():
    only_cp = facts(NetIncomeLoss=[year(600)], CommercialPaper=[snap(500)])
    assert edgar.total_debt(only_cp, "2026-01-31") == (None, [])
