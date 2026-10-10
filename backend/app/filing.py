"""10-K text: turns the filing's HTML into plain text with page markers. Owner: Person 1.

The numbers XBRL doesn't tag (floating-rate debt, the undrawn revolver, sometimes
interest expense) only exist as sentences in the filing, so we read them from here.
"""
import re
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser

# tags that start a new line of text
_BLOCK = {"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6", "table", "hr"}
# tags that never have a closing tag
_VOID = {"br", "hr", "img", "meta", "link", "input", "col", "area", "base", "wbr"}
_PAGE_BREAK = re.compile(r"page-break-(?:before|after)\s*:\s*always|break-(?:before|after)\s*:\s*page", re.I)
_HIDDEN = re.compile(r"display\s*:\s*none", re.I)

PAGE_BREAK = "\f"


class _TextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.stack = []  # (tag, hidden, page break after)
        self.hidden = 0
        self.in_cell = 0  # AMC wraps every table cell in a <p>; keep those on the row's line

    def handle_starttag(self, tag, attrs):
        style = dict(attrs).get("style") or ""
        # inline XBRL keeps a copy of every tagged number in a hidden header
        hidden = tag == "ix:header" or tag in ("script", "style") or bool(_HIDDEN.search(style))
        breaks = bool(_PAGE_BREAK.search(style))
        if "before" in style.lower() and breaks:
            self.out.append(PAGE_BREAK)
        if tag in _BLOCK:
            self.out.append(" " if self.in_cell and tag not in ("tr", "table") else "\n")
        if tag in ("td", "th"):
            self.out.append(" | ")
            self.in_cell += 1
        if tag in _VOID:
            if breaks:
                self.out.append(PAGE_BREAK)
            return
        self.stack.append((tag, hidden, breaks and "after" in style.lower()))
        self.hidden += hidden

    def handle_endtag(self, tag):
        # pop up to the matching tag; filings aren't always well formed
        if not any(t == tag for t, _, _ in self.stack):
            return
        while self.stack:
            t, hidden, break_after = self.stack.pop()
            self.hidden -= hidden
            if break_after:
                self.out.append(PAGE_BREAK)
            if t in ("td", "th"):
                self.in_cell -= 1
            if t == tag:
                break
        if tag in _BLOCK:
            self.out.append(" " if self.in_cell and tag not in ("tr", "table") else "\n")

    def handle_data(self, data):
        if not self.hidden:
            self.out.append(data)


def _clean(text: str) -> str:
    text = unescape(text).replace("\xa0", " ").replace("​", "")
    lines = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", line).strip()
        line = re.sub(r"^\|\s*", "", line)
        line = re.sub(r"(\s*\|\s*)+$", "", line)
        line = re.sub(r"(\s*\|\s*){2,}", " | ", line)
        if line:
            lines.append(line)
    return "\n".join(lines)


def html_to_text(html: str) -> str:
    """Plain text of a filing, each page headed by "[page N]".

    N is the page number printed in the page's footer when there is one (so citations
    match the PDF people look at), otherwise the page's position in the document.
    """
    parser = _TextParser()
    parser.feed(html)
    parser.close()
    pages = [_clean(p) for p in "".join(parser.out).split(PAGE_BREAK)]
    out = []
    for i, page in enumerate(p for p in pages if p):
        last = page.rsplit("\n", 1)[-1]
        # footers look like "84", "F-12" or "Page 84"
        m = re.fullmatch(r"(?:page\s+)?([A-Z]-\d{1,3}|\d{1,3})", last, re.I)
        label = m.group(1) if m else str(i + 1)
        out.append(f"[page {label}]\n{page}")
    return "\n\n".join(out)


def page_of(text: str, pos: int) -> str | None:
    """The page label that `pos` falls on."""
    m = None
    for m in re.finditer(r"^\[page ([^\]]+)\]$", text[:pos], re.M):
        pass
    return m.group(1) if m else None


# ---- reading numbers out of the text ----
# every finder returns (value in USD, Excerpt) or (None, None), so the fact sheet can quote
# the sentence the number came from and the fact-checker can check claims against it

_AMOUNT = r"\$\s?(\d[\d,]*(?:\.\d+)?)\s*(billion|million|thousand)?"
_SCALE = {"billion": 1e9, "million": 1e6, "thousand": 1e3, None: 1}


@dataclass
class Excerpt:
    text: str
    page: str | None


def _usd(number: str, scale: str | None) -> float:
    value = float(number.replace(",", ""))
    if scale:
        return value * _SCALE[scale.lower()]
    # filings that state "dollars in millions" up front write "$1,980" for $1.98 billion;
    # no debt figure we look for is really under $100k, so a bare small number means millions
    return value * 1e6 if value < 100_000 else value


def _sentence(text: str, pos: int) -> str:
    """The sentence around `pos` (filings keep each paragraph on one line)."""
    start = text.rfind("\n", 0, pos) + 1
    end = text.find("\n", pos)
    line = text[start:end if end != -1 else None]
    at = pos - start
    # split on sentence ends, but not inside numbers like $15.0 or abbreviations like U.S.
    bounds = [0] + [m.end() for m in re.finditer(r"(?<![A-Z]\.[A-Z])(?<=[.;])\s+(?=[A-Z“\"(])", line)] + [len(line)]
    for a, b in zip(bounds, bounds[1:]):
        if a <= at < b:
            return line[a:b].strip()
    return line.strip()


def _excerpt(text: str, pos: int) -> Excerpt:
    return Excerpt(_sentence(text, pos), page_of(text, pos))


def _first(text: str, patterns, accept=lambda value, sentence: True):
    """The first sentence matching any pattern (in order) whose amount passes `accept`.

    Each pattern is (regex, how to turn the match into USD). Returns (USD, Excerpt) or (None, None).
    """
    for pattern, to_usd in patterns:
        for m in re.finditer(pattern, text, re.I):
            sentence = _sentence(text, m.start())
            value = to_usd(m)
            if value is not None and accept(value, sentence):
                return value, _excerpt(text, m.start())
    return None, None


_FLOAT = r"(?:variable|floating)[- ]rates?"
_DEBT = r"(?:debt|borrowings|indebtedness|loans)"
_ONE_POINT = r"(?:100[- ]basis[- ]points?|1(?:\.0)?\s?%|one percentage point|1 percentage point)"


def floating_rate_debt(text: str, total_debt: float | None):
    """Debt at variable rates, from the interest rate risk section (Item 7A).

    Tries, in order:
      1. the amount, stated outright: "$0.7 billion of variable-rate debt" (delta),
         "floating-rate debt principal was $5.4 billion" (home depot),
         "$6.1 billion ... of our debt had variable rates" (caesars)
      2. a share of total debt: "79% of ... our total debt ... fixed-rate" (verizon),
         "variable rate borrowings ... represented 27% of our total ... debt" (walmart)
      3. a 1-point rate move: "a 100 basis point change ... interest expense ... $Y"
         -> 1% of the floating debt is $Y (AMC, lumen, norwegian)
      4. "debt, which pays interest at a fixed rate" (amazon) or "all of the Company's
         borrowings are under fixed rate instruments" (macy's) -> none of it floats
    Sentences about fair value, interest income or investments are skipped: those
    describe what the company owns, not what it owes.
    """
    def about_debt(value, sentence):
        if re.search(r"fair value|interest income|investments?\b|leases? (?:payments|liabilit)", sentence, re.I):
            return False
        return total_debt is None or value <= total_debt * 1.05

    amount = lambda m: _usd(m.group(1), m.group(2))
    share = lambda fixed: lambda m: (
        round((1 - float(m.group(1)) / 100 if fixed else float(m.group(1)) / 100) * total_debt) if total_debt else None
    )
    patterns = [
        (_AMOUNT + rf"\s+(?:of\s+|in\s+)?(?:aggregate\s+principal\s+amount\s+of\s+)?(?:outstanding\s+)?(?:principal\s+amount\s+of\s+)?{_FLOAT}\s+{_DEBT}", amount),
        (_AMOUNT + rf"\s+of\s+(?:\w+\s+){{0,3}}{_DEBT}\s+(?:that\s+bears\s+interest\s+at|had|bearing\s+interest\s+at)\s+{_FLOAT}", amount),
        (r"\b[Dd]ebt\s+of\s+" + _AMOUNT + rf"[^.$]{{0,60}}?subject\s+to\s+{_FLOAT}", amount),
        (rf"{_FLOAT}\s+{_DEBT}\s+(?:principal\s+)?(?:was|of|totaled|totaling)\s+(?:approximately\s+)?" + _AMOUNT, amount),
        (rf"(\d{{1,3}}(?:\.\d+)?)\s?%\s+of\s+(?:the\s+|our\s+)?[^.%]{{0,120}}?{_DEBT}[^.%]{{0,80}}?fixed[- ]rate", share(True)),
        (rf"(\d{{1,3}}(?:\.\d+)?)\s?%\s+of\s+(?:the\s+|our\s+)?[^.%]{{0,120}}?{_DEBT}[^.%]{{0,80}}?(?:bears?\s+interest\s+at\s+)?{_FLOAT}", share(False)),
        (rf"{_FLOAT}\s+[^.%]{{0,160}}?(?:represented|were|was|comprised)\s+(?:approximately\s+)?(\d{{1,3}}(?:\.\d+)?)\s?%\s+of\s+(?:our\s+)?total[^.]{{0,40}}?{_DEBT}", share(False)),
        (_ONE_POINT + r"\s+(?:change|increase|rise)[^.]{0,250}?(?:interest\s+expense|interest\s+costs?|pre-?tax\s+earnings|pretax\s+earnings)[^.$]{0,200}?" + _AMOUNT,
         lambda m: round(_usd(m.group(1), m.group(2)) * 100)),
        (r"(?:increase|change)\s+(?:of|in\s+(?:\w+\s+){0,2}rates?\s+of)\s+" + _ONE_POINT + r"[^.]{0,250}?(?:interest\s+expense|interest\s+costs?|pre-?tax\s+earnings|pretax\s+earnings)[^.$]{0,200}?" + _AMOUNT,
         lambda m: round(_usd(m.group(1), m.group(2)) * 100)),
    ]
    found = _first(text, patterns, about_debt)
    if found[0] is not None:
        return found
    # amazon says this in a sentence about fair value, so it skips that filter
    return _first(text, [
        (r"debt,?\s+which\s+(?:pays|bears)\s+interest\s+at\s+(?:a\s+)?fixed\s+rates?", lambda m: 0.0),
        (rf"\ball\s+of\s+(?:the\s+company['’]s|our)\s+{_DEBT}\s+(?:are|is|bears?)\s+(?:under\s+|at\s+)?fixed[- ]rate", lambda m: 0.0),
    ])


_FACILITY = r"(?:revolv\w*|credit\s+facilit\w*|ABL|credit\s+agreement|loan\s+facilit\w*)"


def undrawn_revolver(text: str):
    """Revolver capacity still available to borrow.

    Tries, in order:
      1. the amount, stated outright: "$12.0 billion of unused borrowing capacity under our
         ... revolving credit facility" (verizon), "availability of $5.779 billion under our
         ... credit facility" (HCA), "borrowing capacity of the ABL Credit Facility was
         $1,957 million" (macy's), "$1,980 was available for future borrowing" (sirius)
      2. "no borrowings outstanding under ... revolving credit facilities" -> the facility
         sizes added up (amazon)
    """
    amount = lambda m: _usd(m.group(1), m.group(2))
    patterns = [
        (_AMOUNT + r"\s+(?:of\s+|in\s+)?(?:total\s+)?(?:unused\s+borrowing\s+capacity|borrowing\s+capacity|undrawn\s+capacity|undrawn|unused"
         r"|availability|(?:was\s+)?available\s+(?:for\s+(?:future\s+)?borrowing|to\s+(?:be\s+)?(?:borrow|drawn)))[^.]{0,120}?" + _FACILITY, amount),
        (r"(?:availability|borrowing\s+capacity|amount\s+available|borrowings\s+available)\s+(?:under|of)\s+[^.$]{0,80}?" + _FACILITY
         + r"[^.$]{0,40}?(?:was|of)\s+(?:approximately\s+)?" + _AMOUNT, amount),
        (r"(?:availability|borrowings\s+available)\s+(?:of\s+)?(?:approximately\s+)?" + _AMOUNT + r"[^.]{0,60}?" + _FACILITY, amount),
    ]
    found = _first(text, patterns, lambda value, sentence: not re.search(r"letters? of credit sub-?facility|covenant", sentence, re.I))
    if found[0] is not None:
        return found
    m = re.search(r"no\s+(?:outstanding\s+)?borrowings\s+(?:outstanding\s+)?under\s+[^.]{0,80}?revolving\s+credit", text, re.I)
    if m:
        # "We have a $15.0 billion unsecured revolving credit facility", skipping ones that were
        # paid off, and amounts that are borrowings ("$290 million outstanding under the ...")
        sizes = set()
        size = _AMOUNT + r"\s+(?:(?!outstanding|under|of\b|in\b)[\w-]+\s+){0,3}revolving\s+credit\s+(?:facility|agreement)"
        for f in re.finditer(size, text, re.I):
            if not re.search(r"terminat|repaid|expired|reduced|from\s+\$", _sentence(text, f.start()), re.I):
                # the same facility is usually mentioned more than once
                sizes.add(_usd(f.group(1), f.group(2)))
        if sizes:
            return sum(sizes), _excerpt(text, m.start())
    return None, None


def debt_maturities(text: str, fiscal_year: int, total_debt: float | None):
    """{year: principal due} for years 1-5, plus the amount after year five, from the
    debt footnote's maturity table, for companies that stopped tagging it in XBRL.

        Long-Term Debt Maturities                      (lumen)
        2026 | $ | 88
        ...
        2031 and thereafter | 11,023

    Pension, lease and amortization schedules look the same, so the table has to be
    introduced as a debt maturity table and add up to roughly total debt.
    Returns (years, after_year_five, Excerpt) or ({}, None, None).
    """
    lines = text.split("\n")
    first = str(fiscal_year + 1)
    for i, line in enumerate(lines):
        if not re.match(rf"^{first}\s*\|", line):
            continue
        intro = " ".join(lines[max(0, i - 4) : i])
        if not re.search(r"maturit|principal\s+due|due\s+as\s+follows", intro, re.I) or not re.search(r"debt|borrowings|notes", intro, re.I):
            continue
        if re.search(r"leases?\b|pension|amortization\s+expense|benefit", intro, re.I):
            continue
        scale = 1e3 if re.search(r"in\s+thousands", intro, re.I) else 1e6
        years, after = {}, None
        for row in lines[i : i + 10]:
            cells = [c.strip() for c in row.split("|")]
            label = cells[0]
            # last number in the row (the total column), ignoring interest rate columns
            nums = [c for c in cells[1:] if re.fullmatch(r"\(?[\d,]+(?:\.\d+)?\)?|—|-", c)]
            if not nums:
                continue
            value = 0.0 if nums[-1] in ("—", "-") else float(nums[-1].strip("()").replace(",", "")) * scale
            if re.fullmatch(r"20\d\d", label) and fiscal_year < int(label) <= fiscal_year + 5:
                years[int(label)] = value
            elif re.search(r"thereafter|after\s+20\d\d|beyond", label, re.I):
                after = value
                break
        if len(years) < 3:
            continue
        total = sum(years.values()) + (after or 0)
        if total_debt and not 0.7 <= total / total_debt <= 1.4:
            continue
        return years, after, _excerpt(text, sum(len(l) + 1 for l in lines[: max(0, i - 2)]))
    return {}, None, None


_INCOME_STATEMENT = re.compile(r"^consolidated statements? of (?:operations|income|earnings)$", re.I | re.M)


def income_statement_value(text: str, label: str, fiscal_year: int):
    """A number from the consolidated income statement, e.g. "Interest expense | (3,182) | (2,406) | (2,274)".

    Only looks on the statement's own page, so segment tables and MD&A comparisons with
    the same row name don't get picked up. The columns are years, in whatever order the
    company prints them, so this reads the header row for the `fiscal_year` column.
    Statements are in millions unless they say thousands. Companies whose fiscal year ends in January label it the
    year before (Macy's year ending Jan 2026 is "2025"), so that year is tried as well.
    Returns the size of the number: "(2,274)" comes back as 2,274,000,000.
    """
    row = re.compile(rf"^{label}\s*(?:\(\d\))?((?:\s*\|\s*(?:\$|\(?[\d,.—-]+\)?))+)\s*$", re.I | re.M)
    for page in re.finditer(r"^\[page [^\]]+\]$(.*?)(?=^\[page |\Z)", text, re.M | re.S):
        body = page.group(1)
        heading = _INCOME_STATEMENT.search(body)
        if not heading:
            continue
        # norwegian reports in thousands
        scale = 1e3 if re.search(r"in\s+thousands", body[heading.end() : heading.end() + 300], re.I) else 1e6
        for m in row.finditer(body, heading.end()):
            cells = [c.strip() for c in m.group(1).split("|") if c.strip() and c.strip() != "$"]
            header = None
            for line in body[heading.end() : m.start()].split("\n"):
                years = re.findall(r"\b(20\d\d)\b", line)
                if len(years) == len(cells):
                    header = [int(y) for y in years]
                    break
            if not header:
                continue
            for year in (fiscal_year, fiscal_year - 1):
                if year in header:
                    num = cells[header.index(year)].strip("()").replace(",", "")
                    if re.fullmatch(r"\d+(?:\.\d+)?", num):
                        return float(num) * scale, _excerpt(text, page.start(1) + m.start())
                    break
    return None, None
