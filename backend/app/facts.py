"""Fact sheet builder. Owner: Person 1.

EDGAR numbers + metrics + Gemini-grounded news -> one FactSheet with sources.
Both debaters argue only from this.
"""
import json
from pathlib import Path

from .schemas import FactSheet

EXAMPLE = Path(__file__).resolve().parent / "examples" / "fact_sheet.json"  # copy of shared/examples


def build_fact_sheet(ticker: str) -> FactSheet:
    """TODO(Person 1): replace the example with the real pipeline:
         1. edgar.get_cik / get_company_facts / get_latest_filing_text
         2. metrics.* on the pulled numbers
         3. Gemini (with Search grounding) for recent news + debt_details
         4. store.save_fact_sheet so demo companies are cached
    """
    sheet = FactSheet.model_validate(json.loads(EXAMPLE.read_text()))
    if ticker.upper() != sheet.ticker:
        sheet.ticker = ticker.upper()
    return sheet
