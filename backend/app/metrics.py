"""Python metrics: the accountant. Owner: Person 1.

The AI never does math. Every number the debaters quote comes from here.
Done when every metric matches a hand calculation from the 10-K.


[TODO: move this to README later]
Definitions and formulas:

Debt-to-EBITDA (Indication of leverage):
[Total debt]/[EBITDA]
This shows the gains vs losses since it compares the debt/loans taken on by the business with the gains/cash flow. 

- EBITDA: [net income] + [interest] + [taxes] + [deprecation] + [amortization]
This gives a picture of the business's cash flow.
We calculate it as [operating income (EBIT)] + [depreciation and amortization], which is the same
thing without one-off gains/losses below operating income (see ebitda()).

Interest Coverage:
[EBIT]/[Interest Expense]
Shows how many times a company can pay its obligations (money that was lent, etc) with its earnings. 
A low ratio could suggest high debt.

Floating vs. Fixed Debt:

Two different loan types - 
- fixed: a constant interest rate throughout the life of the loan
- floating: also known as a variable interest rate - adjusting periodically based off some sort of benchmark. 

(Debt) Maturity Wall: 
This is when a large amount of a firm's debt is due within a short period of time (1-2 years), which increases the risk of it rolling over.

Total Immediate Liquidity: 
Ease in which an asset or security can become cash. 
Usually a ratio
Here, we are using the undrawn revolver amount which is only used when a borrower can sign/affirm that there is no upcoming default.
This would be a loan between corporate banks and clients - this has fees for the banks to benefit from (upfront, utlization/drawn margin, committment fees.)

Capex / Operating Cash Flow:
[Purchases of property, plant and equipment]/[Net cash provided by operating activities]
How much of the cash the business brings in goes straight back into building things (data
centers, stores, networks). Over 100% means it spent more than it brought in and funded the
rest with cash on hand or borrowing - a sign of heavy (e.g. AI) investment.
Uses purchases of PP&E, not total cash flows from investing activities: that total also
includes acquisitions and buying/selling securities, which would swamp the capex figure.
Not shown when operating cash flow is negative (the ratio's sign would be meaningless).
"""


def ebitda(ebit: float, depreciation_amortization: float) -> float:
    """EBIT (operating income) + depreciation and amortization.

    Same as net income + interest + taxes + D&A, minus the one-off items below operating
    income (like AMC's $196M loss on paying off debt early), which would make the
    company look worse than its business is.
    """
    return ebit + depreciation_amortization


def leverage(total_debt: float, ebitda: float) -> float:
    """Debt-to-EBITDA ratio, an indicator of leverage: total debt / EBITDA, in turns (x)."""
    return round(total_debt / ebitda, 2)


def interest_coverage(ebit: float, interest_expense: float) -> float:
    """EBIT (operating income) / interest expense, in turns (x): how many times operating
    earnings cover the interest bill. Negative when the company has an operating loss."""
    return round(ebit / interest_expense, 2)


def floating_rate_pct(floating_debt: float, total_debt: float) -> float:
    """Share of debt at variable rates, 0-100."""
    return round(100 * floating_debt / total_debt, 1)


def next_big_maturity(maturities: dict[int, float], threshold_pct: float = 10, total_debt: float | None = None) -> int | None:
    """First year whose maturing amount is at least `threshold_pct` of total debt.

    maturities: {year: amount_due}
    """
    total = total_debt or sum(maturities.values())
    for year in sorted(maturities):
        if total and 100 * maturities[year] / total >= threshold_pct:
            return year
    return None


def capex_to_operating_cash_flow(capex: float, operating_cash_flow: float) -> float:
    """Capex as a share of operating cash flow, 0-100+. Over 100% means the company spent
    more on property and equipment than its business brought in, and had to fund the rest
    with cash on hand or borrowing (Oracle's AI data centers: 174% in fiscal 2026)."""
    return round(100 * capex / operating_cash_flow, 1)


def liquidity(cash: float, undrawn_revolver: float) -> float:
    """Total immediate liquidity: cash plus undrawn revolver capacity."""
    return cash + undrawn_revolver

