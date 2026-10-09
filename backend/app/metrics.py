"""Python metrics: the accountant. Owner: Person 1.

The AI never does math. Every number the debaters quote comes from here.
Done when every metric matches a hand calculation from the 10-K.

Definitions and formulas:
"""


def leverage(total_debt: float, ebitda: float) -> float:
    """Total debt / EBITDA, in turns (x)."""
    return round(total_debt / ebitda, 2)


def interest_coverage(ebitda: float, interest_expense: float) -> float:
    """EBITDA / interest expense, in turns (x). Swap to EBIT if the team prefers."""
    return round(ebitda / interest_expense, 2)


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


def liquidity(cash: float, undrawn_revolver: float) -> float:
    """Cash plus undrawn revolver capacity."""
    return cash + undrawn_revolver


def coverage_after_rate_shock(ebitda: float, interest_expense: float, floating_debt: float, bps: int) -> float:
    """Coverage if floating-rate debt reprices up by `bps` basis points."""
    shocked_interest = interest_expense + floating_debt * bps / 10_000
    return round(ebitda / shocked_interest, 2)
