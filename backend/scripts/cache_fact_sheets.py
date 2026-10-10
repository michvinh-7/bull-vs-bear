"""Builds fact sheets ahead of time so debates on these companies start at once.

build_fact_sheet caches what it builds (see facts.py): the 10-K part until the company
files a new 10-K or the fact-sheet code changes, the news for a few hours. Debates then
load the cached sheet in under a second. Run this before a demo, after deploying a change
to the fact-sheet code, or when a company files a new 10-K.

Run from backend/:
  python -m scripts.cache_fact_sheets                 every demo company in companies.py
  python -m scripts.cache_fact_sheets AAPL F          specific tickers
"""
import sys
import time

from app import companies, store
from app.facts import SAMPLE_TICKER, build_fact_sheet

if not store._client:
    sys.exit("SUPABASE_URL / SUPABASE_SERVICE_KEY are empty in backend/.env: nothing would be saved.")

tickers = [t.upper() for t in sys.argv[1:]] or [c.ticker for c in companies.DEMO_COMPANIES]
for ticker in tickers:
    if ticker == SAMPLE_TICKER:
        print(f"{ticker}: skipped, the sample company is never cached")
        continue
    start = time.perf_counter()
    try:
        sheet = build_fact_sheet(ticker)
    except Exception as e:
        print(f"{ticker}: FAILED, {e}")
        continue
    print(f"{ticker}: {sheet.company}, {len(sheet.metrics)} metrics, {len(sheet.debt)} debt rows, "
          f"{sum(s.kind == 'news' for s in sheet.sources)} news ({time.perf_counter() - start:.0f}s)")
    # e.g. the debt step failed: that sheet wasn't cached, so run this again
    for notice in sheet.notices:
        print(f"    ! {notice}")
