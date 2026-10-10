"""Guards the 10-K text reader: HTML to text with page markers, and the finders that
read numbers XBRL doesn't tag. The sentences are real ones from Amazon, Verizon and AMC."""
from app import filing

HTML = """
<html><body>
<ix:header><div>hidden XBRL copy 999,999</div></ix:header>
<div><p>Item 7A. Interest Rate Risk</p>
<p>As of December 31, 2025, approximately 79% of the aggregate principal amount of our total debt
portfolio consisted of fixed-rate indebtedness, including the effect of interest rate swap agreements.</p>
<p>47</p></div>
<hr style="page-break-after:always"/>
<div><p>CONSOLIDATED STATEMENTS OF OPERATIONS</p>
<table>
<tr><td></td><td><p>December 31, 2025</p></td><td><p>December 31, 2024</p></td></tr>
<tr><td><p>Interest expense</p></td><td><p>$</p></td><td><p>(6,694)</p></td><td><p>(6,649)</p></td></tr>
</table>
<p style="display:none">hidden</p>
<p>52</p></div>
</body></html>
"""


def test_html_to_text_pages_and_tables():
    text = filing.html_to_text(HTML)
    assert "999,999" not in text and "hidden" not in text
    # pages are labelled with the number printed in their footer
    assert text.startswith("[page 47]")
    assert "\n[page 52]\n" in text
    # a cell's <p> stays on the row's line
    assert "Interest expense | $ | (6,694) | (6,649)" in text


def test_income_statement_value_reads_the_fiscal_year_column():
    text = filing.html_to_text(HTML)
    val, ex = filing.income_statement_value(text, "Interest expense", 2025)
    assert val == 6_694_000_000 and ex.page == "52"
    assert filing.income_statement_value(text, "Interest expense", 2024)[0] == 6_649_000_000
    # january year ends: the year ending jan 2026 is labelled 2025
    assert filing.income_statement_value(text, "Interest expense", 2026)[0] == 6_694_000_000


def test_floating_from_fixed_share():
    text = filing.html_to_text(HTML)
    val, ex = filing.floating_rate_debt(text, 158_150_000_000)
    assert val == 33_211_500_000
    assert ex.text.startswith("As of December 31, 2025, approximately 79%") and ex.page == "47"


def test_floating_from_rate_sensitivity():
    text = ("[page 68]\nA 100-basis point change in market interest rates would have increased or decreased "
            "interest expense on the New Term Loans by approximately $20.1 million during the year ended December 31, 2025.")
    assert filing.floating_rate_debt(text, 4_024_000_000)[0] == 2_010_000_000


def test_all_fixed_rate_debt_has_none_floating():
    text = ("[page 31]\nHowever, the fair value of our long-term debt, which pays interest at a fixed rate, "
            "will generally fluctuate with movements of interest rates.")
    assert filing.floating_rate_debt(text, 69_291_000_000)[0] == 0


def test_revolver_from_unused_capacity():
    text = ("[page 16]\nAs of December 31, 2025, Verizon had approximately $131.1 billion of outstanding unsecured "
            "indebtedness, $12.0 billion of unused borrowing capacity under our existing revolving credit facility.")
    assert filing.undrawn_revolver(text)[0] == 12_000_000_000


def test_revolver_adds_up_undrawn_facilities():
    text = "\n".join([
        "[page 23]",
        "We had no borrowings outstanding under the two unsecured revolving credit facilities as of December 31, 2025.",
        "[page 58]",
        "We have a $15.0 billion unsecured revolving credit facility with a syndicate of lenders.",
        "In October 2025, we entered into a $5.0 billion unsecured 364-day revolving credit facility, which replaced the prior 364-day revolving credit agreement.",
        "In 2024 we repaid and terminated the $1.0 billion secured revolving credit facility.",
    ])
    val, ex = filing.undrawn_revolver(text)
    assert val == 20_000_000_000 and ex.page == "23"


def test_nothing_found():
    assert filing.floating_rate_debt("[page 1]\nNothing here.", 100) == (None, None)
    assert filing.undrawn_revolver("[page 1]\nNothing here.") == (None, None)


def test_floating_stated_outright():
    cases = {
        "At December 31, 2025, we had $12.6 billion of fixed-rate debt, $0.7 billion of variable-rate debt and $0.4 billion of variable-rate leases.": 700_000_000,
        "At February 1, 2026, after giving consideration to our interest rate swap agreements, floating-rate debt principal was $5.4 billion, or approximately 11% of our senior notes portfolio.": 5_400_000_000,
        "Debt of $2.507 billion at December 31, 2025 was subject to variable rates of interest, while the remaining debt balance of $43.985 billion was subject to fixed rates of interest.": 2_507_000_000,
        "As of December 31, 2025, we had approximately $1.6 billion of indebtedness that bears interest at variable rates, which is net of our interest rate swap agreements.": 1_600_000_000,
    }
    for sentence, want in cases.items():
        assert filing.floating_rate_debt("[page 1]\n" + sentence, 50_000_000_000)[0] == want, sentence


def test_floating_ignores_investments_and_fair_value():
    text = ("[page 1]\nAs of January 31, 2026, our floating rate short-term investments exceeded our floating rate debt "
            "obligations by approximately $2.4 billion.\nA 100 basis point increase would have decreased the fair value "
            "of our fixed-rate debt by $470 million.")
    assert filing.floating_rate_debt(text, 14_000_000_000) == (None, None)


def test_floating_share_and_all_fixed():
    walmart = ("[page 47]\nAs of January 31, 2026, our variable rate borrowings, including the effect of our commercial "
               "paper and interest rate swaps, represented 27% of our total short-term and long-term debt.")
    assert filing.floating_rate_debt(walmart, 100_000_000_000)[0] == 27_000_000_000
    macys = "[page 33]\nAll of the Company's borrowings are under fixed rate instruments."
    assert filing.floating_rate_debt(macys, 2_000_000_000)[0] == 0


def test_revolver_wordings():
    cases = {
        "As of January 31, 2026, borrowing capacity of the ABL Credit Facility was $1,957 million, which reflects letters of credit.": 1_957_000_000,
        "As of December 31, 2025, we had availability of $5.779 billion under our senior unsecured credit facility.": 5_779_000_000,
        "As of December 31, 2025, $1,980 was available for future borrowing under the Credit Facility.": 1_980_000_000,
        "We had $3.4 billion in total undrawn capacity under revolving credit and other facilities.": 3_400_000_000,
    }
    for sentence, want in cases.items():
        assert filing.undrawn_revolver("[page 1]\n" + sentence)[0] == want, sentence


def test_revolver_size_isnt_a_borrowing_or_counted_twice():
    kohls = "\n".join([
        "[page 25]",
        "There were no outstanding borrowings under the revolving credit facility compared to $290 million in the prior year.",
        "As of February 1, 2025, there was $290 million outstanding under the revolving credit facility.",
        "We are also subject to interest rate risk under our $1.5 billion revolving credit facility.",
        "Borrowings under the $1.5 billion revolving credit facility were $0 as of January 31, 2026.",
    ])
    assert filing.undrawn_revolver(kohls)[0] == 1_500_000_000


def test_debt_maturities_table():
    text = "\n".join([
        "[page 103]",
        "Long-Term Debt Maturities",
        "Set forth below is the aggregate principal amount of our long-term debt maturing during the following years:",
        "| (Dollars in millions)",
        "2026 | $ | 88",
        "2027 | 72",
        "2028 | 716",
        "2029 | 3,761",
        "2030 | 2,155",
        "2031 and thereafter | 11,023",
        "Total long-term debt | $ | 17,815",
        "As of December 31, 2025, maturities of lease liabilities were as follows:",
        "| Operating Leases | Finance Leases",
        "2026 | $ | 366 | 28",
        "2027 | 298 | 29",
        "2028 | 254 | 28",
    ])
    years, after, ex = filing.debt_maturities(text, 2025, 17_353_000_000)
    assert years == {2026: 88e6, 2027: 72e6, 2028: 716e6, 2029: 3_761e6, 2030: 2_155e6}
    assert after == 11_023e6 and ex.page == "103"
    # a table that doesn't add up to the company's debt is some other schedule
    assert filing.debt_maturities(text, 2025, 90_000_000_000) == ({}, None, None)


def test_income_statement_in_thousands():
    text = "\n".join([
        "[page F-3]",
        "Consolidated Statements of Operations",
        "(in thousands, except share and per share data)",
        "| 2025 | 2024 | 2023",
        "Interest expense, net | (953,506) | (747,223) | (727,531)",
    ])
    assert filing.income_statement_value(text, r"Interest expense(?:, net)?", 2025)[0] == 953_506_000
