"""Gemini research for the fact sheet: the debt instruments and recent news. Owner: Person 1.

Gemini only finds and copies text; code checks everything it returns and does the math.
  - Debt: Gemini copies each instrument's sentence or table row from the 10-K. Code keeps
    it only if that quote really is in the filing and holds the amount, rate and year,
    then converts the amount to dollars and decides fixed or floating from the rate.
  - News: Gemini searches Google and writes short factual sentences. Only sentences that
    Google's grounding ties to a search result are kept, with that result's link.
Anything that fails a check is dropped, and if Gemini is unavailable the fact sheet is
built without this part.
"""
import re
from datetime import date
from typing import Literal

from pydantic import BaseModel

from . import agents, config, filing, usage

_SCALES = {"thousand": 1e3, "million": 1e6, "billion": 1e9}
_FLOATING = re.compile(r"SOFR|LIBOR|EURIBOR|SONIA|base rate|prime|floating|variable", re.I)
# loans from banks float almost always, even when the table only shows today's rate (AMC's
# term loan row says "10.731%")
_BANK_LOAN = re.compile(r"term loan|credit facilit|credit agreement|revolv", re.I)

def _generate(contents: str, thinking: str | None = "low", **settings):
    """One Gemini call with the debate's key and model (the user's own from Settings, else the
    server's), counted in the debate's usage like every other call.

    Thinking is "low" by default: finding and copying text needs little reasoning, and it
    made the debt step about 4x faster (21 s -> 5 s for Amazon) and news about 1.5x faster.
    None leaves it to the model's default."""
    from google.genai import types

    ctx = usage.current()
    model = ctx.model if ctx else config.GEMINI_MODEL
    if thinking:
        # raised to the model's floor where needed (Pro can't go below "low")
        settings["thinking_config"] = types.ThinkingConfig(thinking_level=usage.thinking_for(model, thinking))
    # held in a variable for the whole call: if the news and debt steps both create the
    # shared client at once, the one that gets replaced would otherwise be garbage collected,
    # and Google's library closes its connection mid-request ("client has been closed")
    client = agents._client_for(ctx)
    resp = client.models.generate_content(
        model=model,
        contents=contents,
        # longer than a debate turn's 20 s: a search or a 30-page read takes a while, and
        # it's done once per company before the debate starts
        config=types.GenerateContentConfig(http_options=types.HttpOptions(timeout=90_000), **settings),
    )
    usage.record_gemini(resp)
    return resp


# ---- debt instruments ----

class _Instrument(BaseModel):
    name: str
    amount_as_written: str
    rate_as_written: str
    maturity_year: int
    seniority: Literal["senior_secured", "senior_unsecured", "subordinated"]
    quote: str


class _Instruments(BaseModel):
    instruments: list[_Instrument]


DEBT_PROMPT = """You are reading pages from {company}'s latest 10-K. List up to 8 of the largest
debt instruments (or groups of notes) outstanding at the end of the fiscal year.

For each one, copy from the pages below, exactly as written:
  - quote: the sentence or table row that states it, copied character for character,
    including any " | " separators. It must contain the amount, the rate and the maturity year.
  - amount_as_written: the outstanding amount as it appears in the quote, e.g. "$416 million" or "2,000"
  - rate_as_written: the interest rate as it appears in the quote, e.g. "SOFR plus 4.25%" or "7.5%"
  - maturity_year: the year it matures, as in the quote
  - seniority: senior_secured, senior_unsecured or subordinated
Use rows for actual notes, loans or facilities. Don't use summary rows that group debt by
maturity bucket ("< 5 Years", "5-10 Years", "> 10 Years"): they don't name a maturity year.
Use the amount outstanding at the end of fiscal {fiscal_year}, not the year before. Skip
anything that was repaid, terminated or isn't outstanding at year end. Do not
calculate, round or combine anything.

PAGES:
{pages}"""


def _debt_pages(text: str, limit: int = 8) -> str:
    """The pages that talk about debt the most: the debt footnote, liquidity, market risk."""
    pages = re.split(r"(?m)^(?=\[page )", text)
    words = r"senior (?:secured |unsecured )?notes|term loan|notes due|debentures|revolving credit|credit facilit|% notes|maturit"
    ranked = sorted(pages, key=lambda p: len(re.findall(words, p, re.I)), reverse=True)[:limit]
    return "\n\n".join(p for p in pages if p in ranked)  # back in filing order


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("’", "'")).strip().lower()


def _scale(text: str, quote_at: int, amount: str) -> float | None:
    """Dollars per unit of `amount`: from its own words ("$416 million"), else from the
    "(in millions)" note heading the quote's page. None if neither says."""
    words = re.search(r"(thousand|million|billion)", amount, re.I)
    if words:
        return _SCALES[words.group(1).lower()]
    page_start = text.rfind("[page ", 0, quote_at)
    heading = text[page_start:quote_at]
    unit = None
    for m in re.finditer(r"in (thousands|millions|billions)", heading, re.I):
        unit = _SCALES[m.group(1).lower()[:-1]]
    return unit


def _find(quote: str, text: str) -> re.Match | None:
    """Where `quote` is in the filing, ignoring differences in spacing and curly quotes."""
    words = quote.replace("’", "'").split()
    if not words:
        return None
    return re.search(r"\s+".join(re.escape(w) for w in words), text.replace("’", "'"), re.I)


def _year_column(text: str, row_at: int, row: str, fiscal_year: int) -> str | None:
    """For a table row, the cell under the fiscal year's column, e.g. "12,000" from
    "... | 13,000 | 12,000" under "December 31, 2024 | December 31, 2025". Companies order
    the years either way. None if the row isn't a table row or no year header is found."""
    if " | " not in row:
        return None
    page_start = text.rfind("[page ", 0, row_at)
    year_cell = re.compile(r"^(?:[A-Za-z]+\.? \d{1,2}, )?(20\d\d)$")
    for line in reversed(text[page_start:row_at].split("\n")):
        years = [int(m.group(1)) for c in line.split("|") if (m := year_cell.match(c.strip()))]
        if len(years) >= 2:
            cells = [c.strip() for c in row.split("|") if c.strip() and c.strip() != "$"]
            if len(cells) < len(years):
                return None
            # the amounts are the last cells, one per year
            amounts = dict(zip(years, cells[-len(years):]))
            for year in (fiscal_year, fiscal_year + 1):  # a January year end is labelled the year after
                if year in amounts:
                    return amounts[year]
            return None
    return None


def check_instrument(raw: dict, text: str, fiscal_year: int) -> tuple[dict, str, int] | None:
    """A Gemini-extracted instrument if it holds up against the filing, else None.

    Returns (DebtInstrument fields minus source_id, the quote as it appears in the
    filing, where it appears)."""
    found = _find(raw["quote"], text)
    if not found:
        return None
    quote = text[found.start() : found.end()]
    number = re.search(r"\d[\d,]*(?:\.\d+)?", raw["amount_as_written"])
    rate = raw["rate_as_written"].strip()
    if not number or number.group(0) not in quote:
        return None
    # in a table, the amount has to be this year's column, not last year's
    this_year = _year_column(text, found.start(), quote, fiscal_year)
    if this_year is not None and this_year.replace("$", "").strip() != number.group(0):
        return None
    if not rate or _norm(rate) not in _norm(quote) or str(raw["maturity_year"]) not in quote:
        return None
    if not fiscal_year <= raw["maturity_year"] <= fiscal_year + 100:
        return None
    if raw["seniority"] == "senior_secured" and re.search(r"\bunsecured\b", quote, re.I):
        return None
    scale = _scale(text, found.start(), raw["amount_as_written"])
    amount = float(number.group(0).replace(",", "")) * scale if scale else 0
    if amount <= 0:
        return None
    name = raw["name"].strip()
    # a group of notes maturing over a range ("2026 - 2061") shouldn't read as one 2061 bond
    span = re.search(r"\b(20\d\d)\s*[-–]\s*(20\d\d)\b", quote)
    if span and str(raw["maturity_year"]) in span.groups() and span.group(1) not in name:
        name += f" (due {span.group(1)}–{span.group(2)})"
    return {
        "name": name,
        "amount_usd": amount,
        "seniority": raw["seniority"],
        "rate_type": "floating" if _FLOATING.search(rate) or _BANK_LOAN.search(name) else "fixed",
        "rate": rate,
        "maturity_year": raw["maturity_year"],
    }, quote, found.start()


def debt_instruments(text: str, company: str, fiscal_year: int) -> list[tuple[dict, str, str | None]]:
    """[(DebtInstrument fields minus source_id, quote, page)], largest first.

    Tries low thinking first. If most of what it returns fails the checks (it sometimes
    reads a maturity-bucket summary table instead of the notes, as with Verizon), it tries
    once more with the model's default thinking: slower, but it reads the right table."""
    prompt = DEBT_PROMPT.format(company=company, fiscal_year=fiscal_year, pages=_debt_pages(text))
    for thinking in ("low", None):
        resp = _generate(prompt, thinking=thinking, temperature=0, response_mime_type="application/json",
                         response_schema=_Instruments)
        raw = _Instruments.model_validate_json(resp.text).model_dump()["instruments"]
        checked = [(r, check_instrument(r, text, fiscal_year)) for r in raw]
        if sum(1 for _, c in checked if c) * 2 >= len(raw):
            break
        print(f"[research] {sum(1 for _, c in checked if c)}/{len(raw)} debt rows held up with low thinking; trying again")
    out, seen = [], set()
    for raw_row, checked_row in checked:
        if not checked_row:
            print(f"[research] dropped debt row that didn't match the filing: {raw_row['name']!r}")
            continue
        fields, quote, pos = checked_row
        key = (fields["name"].lower(), fields["maturity_year"], fields["amount_usd"])
        if key not in seen:
            seen.add(key)
            out.append((fields, quote, filing.page_of(text, pos)))
    return sorted(out, key=lambda x: -x[0]["amount_usd"])


# ---- news ----

NEWS_PROMPT = """Today is {today}. Using Google Search, find up to 5 news items from the last six
months about {company} ({ticker}) that matter to its lenders: debt issuance or
refinancing, credit rating changes, earnings, guidance, layoffs, closures, lawsuits.

Write each as one factual sentence on its own line that starts with the date
(Month D, YYYY). Include the figures where the news has them. No opinions, no predictions."""


def _news_date(sentence: str) -> str | None:
    m = re.search(r"([A-Z][a-z]+ \d{1,2}, \d{4})", sentence)
    if not m:
        return None
    try:
        from datetime import datetime

        return datetime.strptime(m.group(1), "%B %d, %Y").date().isoformat()
    except ValueError:
        return None


def news_items(company: str, ticker: str, today: date | None = None, limit: int = 4) -> list[dict]:
    """[{"label", "url", "excerpt"}] for recent news, each tied to a search result."""
    today = today or date.today()
    from google.genai import types

    resp = _generate(
        NEWS_PROMPT.format(today=f"{today:%B} {today.day}, {today.year}", company=company, ticker=ticker),
        tools=[types.Tool(google_search=types.GoogleSearch())],
        temperature=0.2,
    )
    grounding = resp.candidates[0].grounding_metadata if resp.candidates else None
    if not grounding or not grounding.grounding_supports:
        return []
    chunks = grounding.grounding_chunks or []
    return grounded_news(
        resp.text or "",
        [(s.segment.text, [chunks[i].web for i in s.grounding_chunk_indices if i < len(chunks)])
         for s in grounding.grounding_supports],
        today,
        limit,
    )


def grounded_news(answer: str, supports: list[tuple[str, list]], today: date, limit: int = 4) -> list[dict]:
    """Turns Gemini's answer and Google's grounding supports (a piece of the answer and the
    web results behind it) into news sources. Separate from the call so it can be tested
    without the network.

    A support can cover just part of a sentence ("'s Corporate Family Rating to B3..."), so
    the excerpt is the whole line of the answer it's on; the support gives the link."""
    out, seen = [], set()
    for segment, webs in supports:
        at = answer.find(segment)
        if at < 0 or not webs:
            continue
        start = answer.rfind("\n", 0, at) + 1
        end = answer.find("\n", at)
        sentence = answer[start : end if end != -1 else None]
        sentence = re.sub(r"^[\s*•-]+", "", sentence).replace("**", "").strip()
        if not sentence or sentence in seen:
            continue
        when = _news_date(sentence)
        if when and (today - date.fromisoformat(when)).days > 200:
            continue  # older than the last six months or so
        seen.add(sentence)
        web = webs[0]
        # "News · " up front: the brief's open questions copy source labels into
        # where_to_look, which has to name a kind of document
        out.append({
            "label": f"News · {web.title} · {when}" if when else f"News · {web.title}",
            "url": web.uri,
            "excerpt": sentence,
        })
        if len(out) == limit:
            break
    return out
