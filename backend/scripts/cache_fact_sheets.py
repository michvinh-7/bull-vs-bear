"""Builds and saves fact sheets so debates on these companies start at once.

Debates read a saved fact sheet before building one (EDGAR + Gemini can take a
while). Run this for the demo companies once the real fact-sheet pipeline is in,
and again whenever the pipeline or a company's filings change.

Run from backend/:
  python -m scripts.cache_fact_sheets                 every demo company in companies.py
  python -m scripts.cache_fact_sheets AAPL F          specific tickers
"""
import json
import sys
import time

from app import companies, store
from app.agents import EXAMPLES
from app.facts import build_fact_sheet
from app.schemas import FactSheet

SAMPLE = FactSheet.model_validate(json.loads((EXAMPLES / "fact_sheet.json").read_text(encoding="utf-8")))

if not store._client:
    sys.exit("SUPABASE_URL / SUPABASE_SERVICE_KEY are empty in backend/.env: nothing would be saved.")

tickers = [t.upper() for t in sys.argv[1:]] or [c.ticker for c in companies.DEMO_COMPANIES]
for ticker in tickers:
    start = time.perf_counter()
    sheet = build_fact_sheet(ticker)
    if sheet.ticker != ticker:
        print(f"{ticker}: skipped, the builder returned {sheet.ticker}")
        continue
    if sheet.company == SAMPLE.company and ticker != SAMPLE.ticker:
        print(f"{ticker}: skipped, the builder still returns the {SAMPLE.company} sample")
        continue
    store.save_fact_sheet(sheet)
    print(f"{ticker}: saved {sheet.company}, {len(sheet.sources)} sources, {len(sheet.metrics)} metrics "
          f"({time.perf_counter() - start:.0f}s)")
