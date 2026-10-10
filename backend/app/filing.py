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
    return float(number.replace(",", "")) * _SCALE[scale.lower() if scale else None]


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


def floating_rate_debt(text: str, total_debt: float | None):
    """Debt at variable rates, from the interest rate risk section (Item 7A).

    Tries, in order:
      1. "X% of our debt ... fixed-rate"  -> (100 - X)% of total debt
         "X% of our borrowings bear interest at variable rates" -> X% of total debt
      2. "a 100 basis point change ... interest expense ... $Y" -> 1% of the floating debt is $Y
      3. "debt, which pays interest at a fixed rate" -> none of it floats
    """
    if total_debt:
        pct = r"(\d{1,3}(?:\.\d+)?)\s?%\s+of\s+(?:the\s+|our\s+)?[^.%]{0,120}?(?:debt|indebtedness|borrowings)[^.%]{0,80}?"
        for pattern, fixed in ((pct + r"fixed[- ]rate", True), (pct + r"(?:variable|floating)[- ]?(?:interest\s+)?rates?", False)):
            m = re.search(pattern, text, re.I)
            if m:
                share = float(m.group(1)) / 100
                return round((1 - share if fixed else share) * total_debt), _excerpt(text, m.start())
    m = re.search(
        r"100[- ]basis[- ]points?\s+(?:change|increase)[^.]{0,250}?interest expense[^.$]{0,200}?" + _AMOUNT,
        text,
        re.I,
    )
    if m:
        return round(_usd(m.group(1), m.group(2)) * 100), _excerpt(text, m.start())
    m = re.search(r"debt,?\s+which\s+(?:pays|bears)\s+interest\s+at\s+(?:a\s+)?fixed\s+rates?", text, re.I)
    if m:
        return 0.0, _excerpt(text, m.start())
    return None, None


def undrawn_revolver(text: str):
    """Revolver capacity still available to borrow.

    Tries, in order:
      1. "$X of unused borrowing capacity / availability under ... revolving credit"
      2. "no borrowings outstanding under ... revolving credit facilities" -> the facility sizes added up
    """
    m = re.search(
        _AMOUNT + r"\s+(?:of\s+)?(?:unused\s+borrowing\s+capacity|undrawn|unused|availability|available\s+(?:for\s+borrowing|to\s+(?:be\s+)?borrow))"
        r"[^.]{0,120}?revolving",
        text,
        re.I,
    )
    if m:
        return _usd(m.group(1), m.group(2)), _excerpt(text, m.start())
    m = re.search(r"no\s+borrowings\s+outstanding\s+under\s+[^.]{0,80}?revolving\s+credit", text, re.I)
    if m:
        sizes, seen = 0.0, set()
        # "We have a $15.0 billion unsecured revolving credit facility", skipping ones that were paid off
        for f in re.finditer(_AMOUNT + r"\s+(?:[\w-]+\s+){0,3}revolving\s+credit\s+(?:facility|agreement)", text, re.I):
            sentence = _sentence(text, f.start())
            if sentence in seen or re.search(r"terminat|repaid|expired", sentence, re.I):
                continue
            seen.add(sentence)
            sizes += _usd(f.group(1), f.group(2))
        if sizes:
            return sizes, _excerpt(text, m.start())
    return None, None


_INCOME_STATEMENT = re.compile(r"^consolidated statements? of (?:operations|income|earnings)$", re.I | re.M)


def income_statement_value(text: str, label: str, fiscal_year: int):
    """A number from the consolidated income statement, e.g. "Interest expense | (3,182) | (2,406) | (2,274)".

    Only looks on the statement's own page, so segment tables and MD&A comparisons with
    the same row name don't get picked up. The columns are years, in whatever order the
    company prints them, so this reads the header row for the `fiscal_year` column.
    Statements are in millions. Companies whose fiscal year ends in January label it the
    year before (Macy's year ending Jan 2026 is "2025"), so that year is tried as well.
    Returns the size of the number: "(2,274)" comes back as 2,274,000,000.
    """
    row = re.compile(rf"^{label}\s*(?:\(\d\))?((?:\s*\|\s*(?:\$|\(?[\d,.—-]+\)?))+)\s*$", re.I | re.M)
    for page in re.finditer(r"^\[page [^\]]+\]$(.*?)(?=^\[page |\Z)", text, re.M | re.S):
        body = page.group(1)
        heading = _INCOME_STATEMENT.search(body)
        if not heading:
            continue
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
                        return float(num) * 1e6, _excerpt(text, page.start(1) + m.start())
                    break
    return None, None
