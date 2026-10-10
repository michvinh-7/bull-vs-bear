"""Gemini agents: bull, bear, moderator. Owner: Person 2.

Every rule the agents must follow is written so code can check it. The prompts
tell Gemini the rules, and validate_* enforces them. A reply that breaks a rule
gets ONE retry with the errors fed back; if it fails again the turn is dropped
(team contract: never show broken data on screen).

Who decides what:
  - Code picks which claim each speaker must answer (the "target").
  - Code assigns turn numbers, claim ids, labels, audio, the unsupported list.
  - Gemini only writes the words, citing source ids from the fact sheet.
  - Gemini never does math and never recommends a trade.

Without GEMINI_API_KEY every function replays the shared examples, so the
frontend and tests run with no key.
"""
import json
import re
from pathlib import Path
from typing import Callable, Literal

from pydantic import BaseModel, ValidationError, create_model

from . import config
from .schemas import (
    AgreedPoint,
    Claim,
    CommitteeBrief,
    DisputedPoint,
    FactSheet,
    LineMessage,
    OpenQuestion,
    Positions,
    Side,
    UnsupportedClaim,
)

EXAMPLES = Path(__file__).resolve().parent / "examples"  # copy of shared/examples, so Railway (root backend/) has it

# ---- Operational definitions: the numbers every rule is checked against ----

TURN_SENTENCES = (2, 3)
TURN_MAX_WORDS = 70
ANSWER_SENTENCES = (2, 4)  # answering a moderator or user question goes a little deeper
ANSWER_MAX_WORDS = 90
CLAIMS = (1, 3)
CLAIM_MAX_WORDS = 25
QUESTION_SENTENCES = (1, 3)
QUESTION_MAX_WORDS = 55
HISTORY_LINES = 8
MAX_RETRIES = 1

VERDICT = re.compile(
    r"\b(buy|buying|sell|selling|go long|go short|short the|shorting|recommend\w*|"
    r"investment advice|you should invest|we advise|winner|wins the debate)\b",
    re.IGNORECASE,
)

# ---- Prompts ----

SHARED_RULES = f"""\
You are one voice in a three-person credit committee: a BULL analyst, a BEAR
analyst and a MODERATOR. You are debating whether a company's DEBT is a sound
credit, not whether its stock is a good investment. Every line is read aloud.

HARD RULES. Code checks your output; breaking any rule rejects the turn.

1. LENGTH. "text" is {TURN_SENTENCES[0]} to {TURN_SENTENCES[1]} sentences, at most {TURN_MAX_WORDS} words
   ({ANSWER_SENTENCES[0]} to {ANSWER_SENTENCES[1]} sentences and {ANSWER_MAX_WORDS} words when answering a QUESTION).
   Spoken, not written: no lists, headings, markdown, parentheses or emoji.
2. CLAIMS. List every factual statement you make in "claims", {CLAIMS[0]} to {CLAIMS[1]} per turn:
   - "text": the claim as one plain sentence, at most {CLAIM_MAX_WORDS} words.
   - "source_id": the id of ONE item in SOURCES, exactly as written.
   - "quote": 3 to 15 words copied EXACTLY from that source's excerpt that prove the claim.
   Opinions ("that worries me") may appear in "text" but are never claims.
3. ONLY KNOWN NUMBERS. Every number you say must appear in a source or metric
   you cite this turn, or in TARGET_CLAIM. Never add, subtract, combine,
   estimate, round, project or invent a number: computed figures are already
   in METRICS (cite one of its source_ids to use it). Write numbers as digits,
   the way they appear in SOURCES or METRICS ($416 million, 62%, 5.8x, 2028),
   never spelled out in words.
4. ANSWER THE OTHER SIDE. When TARGET_CLAIM is given, your FIRST sentence
   responds to it directly and reuses its key number or term. If it is the
   other side's claim, contradict it with a fact, outweigh it with a bigger
   fact, or explain why it matters less. If "yours" is true, the moderator is
   challenging YOUR claim: defend it with evidence. Never ignore it.
5. QUESTIONS. When QUESTION is given, answer it directly in your first
   sentence, then back the answer with evidence. If the user asked it, speak
   to them plainly; they may not know finance terms.
6. NO TRADE CALLS. Never say buy, sell, short, go long, recommend, or anything
   telling the listener what to do with money. You argue; the human decides.
7. NO REPEATS. Never repeat a fact from YOUR_RECENT_CLAIMS (your last 2 turns),
   even in new words. Bring a new fact or a new angle. Older facts may come
   back if they answer the point in front of you.
"""

SYSTEM_PROMPTS = {
    "bull": SHARED_RULES + """
YOUR ROLE: THE BULL. You argue the company's debt is a sound credit: lenders
are likely to be paid in full and on time. Lean on cash flow, collateral,
liquidity, distant maturities, fixed-rate debt and improving trends.
Voice: confident, upbeat, plain-spoken, short punchy sentences.
""",
    "bear": SHARED_RULES + """
YOUR ROLE: THE BEAR. You argue the debt carries more risk than it looks:
lenders could face delays, losses or a refinancing squeeze. Lean on leverage,
thin interest coverage, floating-rate exposure, near-term maturities,
shrinking liquidity and deteriorating trends.
Voice: dry, skeptical, precise. You care most about maturities and coverage.
""",
    "moderator": f"""\
You are the MODERATOR of a credit committee debating a company's DEBT. You are
neutral: you never take a side, never say who is winning, never recommend a trade.

TASK: halfway through the debate, point out the most important detail about
the numbers so far and put one sharp question to one side. Good targets: a
claim the fact-checker labeled "unsupported" or "contested", two numbers that
pull in opposite directions, or a key number one side keeps ignoring.

HARD RULES. Code checks your output; breaking any rule rejects it.
1. "text" is {QUESTION_SENTENCES[0]} to {QUESTION_SENTENCES[1]} sentences, at most {QUESTION_MAX_WORDS} words, and ends with "?".
   Address the side by name ("Bull," or "Bear,").
2. "directed_to" is "bull" or "bear": the side that must answer.
3. "about_claim_ids" lists 1 or 2 claim ids from CLAIMS, exactly as written.
4. Every number you say must appear in CLAIMS, SOURCES or METRICS. Never compute one.
5. Ask about evidence, not opinion. Never say buy, sell, short, recommend or who won.
Voice: calm, even, brief.
""",
    "positions": """\
You prepare the opening positions for a credit committee debate about a
company's DEBT. Write the BULL case (the debt is a sound credit) and the BEAR
case (the debt is riskier than it looks).

For each side: "thesis" is 1 to 2 plain sentences; "points" are exactly 3 short
phrases (at most 12 words each), each citing ONE source id from SOURCES.
Every number must appear in that source or in METRICS, written as digits the
same way ($410 million, 62%, 5.8x, 2028). Never compute numbers.
Never say buy, sell, short or recommend.
""",
}

# ---- Response schemas (Gemini structured output; source ids are an enum) ----

def _turn_schema(source_ids: list[str]) -> type[BaseModel]:
    sid = Literal[tuple(source_ids)] if source_ids else str
    claim = create_model("TurnClaim", text=(str, ...), source_id=(sid, ...), quote=(str, ...))
    return create_model("Turn", text=(str, ...), claims=(list[claim], ...))


def _question_schema(claim_ids: list[str]) -> type[BaseModel]:
    cid = Literal[tuple(claim_ids)] if claim_ids else str
    return create_model(
        "Question", text=(str, ...), directed_to=(Literal["bull", "bear"], ...), about_claim_ids=(list[cid], ...)
    )


def _positions_schema(source_ids: list[str]) -> type[BaseModel]:
    sid = Literal[tuple(source_ids)] if source_ids else str
    point = create_model("PositionPoint", text=(str, ...), source_id=(sid, ...))
    side = create_model("PositionSide", thesis=(str, ...), points=(list[point], ...))
    return create_model("PositionsOut", bull=(side, ...), bear=(side, ...))

# ---- Text helpers ----

_SENT = re.compile(r"[^.!?]+[.!?]+(?=\s|$)")
_NUM = re.compile(r"(?<![A-Za-z])\d[\d,]*(?:\.\d+)?")
_STOP = set(
    "the and that this with from have has had were was are for its their they them than then into over "
    "under about which while would could should there these those been being more most less least only "
    "also just very company debt".split()
)


def sentences(text: str) -> list[str]:
    found = _SENT.findall(text.strip())
    return [s.strip() for s in found] if found else ([text.strip()] if text.strip() else [])


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9$%.,'-]+", text)


def numbers(text: str) -> set[str]:
    """'$1,200.50' -> '1200.5', '62%' -> '62', '5.8x' -> '5.8'."""
    out = set()
    for raw in _NUM.findall(text):
        v = raw.replace(",", "").rstrip(".")
        try:
            out.add(f"{float(v):.6f}".rstrip("0").rstrip("."))
        except ValueError:
            pass
    return out


_SPELLED = re.compile(
    r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|"
    r"sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred)"
    r"[\s-]+(?:\w+[\s-]+){0,3}?(?:hundred|thousand|million|billion|percent|basis points?)\b",
    re.IGNORECASE,
)


def money(usd: float) -> str:
    """410000000 -> '$410 million', 1800000000 -> '$1.8 billion'."""
    for size, word in ((1e9, "billion"), (1e6, "million")):
        if abs(usd) >= size:
            return f"${usd / size:.1f}".rstrip("0").rstrip(".") + f" {word}"
    return f"${usd:,.0f}"


def show_metric(value: float, unit: str) -> str:
    """How a metric is said aloud: 5.8x, 62%, 2028, $410 million."""
    if unit == "usd":
        return money(value)
    if unit == "year":
        return str(int(value))
    return f"{value:g}" + {"x": "x", "pct": "%"}.get(unit, "")


def same_fact(a: str, b: str) -> bool:
    """Two claims say the same thing if most of their content words overlap."""
    wa, wb = content_words(a) | numbers(a), content_words(b) | numbers(b)
    return bool(wa and wb) and len(wa & wb) / len(wa | wb) >= 0.6


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def content_words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{4,}", text.lower()) if w not in _STOP}


def _number_text(fact_sheet: FactSheet, source_ids: set[str] | None = None) -> str:
    """All text whose numbers a speaker citing `source_ids` may say (None = everything)."""
    parts = [s.excerpt for s in fact_sheet.sources if source_ids is None or s.id in source_ids]
    for m in fact_sheet.metrics:
        if source_ids is None or set(m.source_ids) & source_ids:
            parts += [show_metric(m.value, m.unit), m.formula]
    for d in fact_sheet.debt:
        if source_ids is None or d.source_id in source_ids:
            parts += [money(d.amount_usd), d.rate, str(d.maturity_year)]
    return " ".join(parts)

# ---- Validators: each returns plain-English errors; empty means pass ----

def validate_turn(
    out: dict, fact_sheet: FactSheet, history: list[LineMessage], target: Claim | None, question: str | None,
    speaker: str = "",
) -> list[str]:
    errs: list[str] = []
    text = out.get("text", "")
    lo, hi = ANSWER_SENTENCES if question else TURN_SENTENCES
    max_words = ANSWER_MAX_WORDS if question else TURN_MAX_WORDS
    sents = sentences(text)
    if not lo <= len(sents) <= hi:
        errs.append(f"text has {len(sents)} sentences; must be {lo}-{hi}.")
    if len(words(text)) > max_words:
        errs.append(f"text has {len(words(text))} words; max {max_words}.")
    if re.search(r"[*#\[\]()]|^\s*[-•]", text, re.M):
        errs.append("text contains markdown, brackets or list markers; write plain speech.")
    if m := VERDICT.search(text):
        errs.append(f"text contains a trade call or verdict ('{m.group(0)}'); remove it.")
    if m := _SPELLED.search(text):
        errs.append(f"'{m.group(0)}' is spelled out; write numbers as digits the way SOURCES do.")

    claims = out.get("claims", [])
    if not CLAIMS[0] <= len(claims) <= CLAIMS[1]:
        errs.append(f"{len(claims)} claims; must be {CLAIMS[0]}-{CLAIMS[1]}.")
    # Only the side's own last 2 turns count: fact sheets are small, so key facts must be able to come back.
    recent = _recent_claims(history, speaker)
    earlier = [c.text for c in recent]
    # Same source, same number = the same fact said again in new words.
    used = {(c.source_id, n) for c in recent for n in numbers(c.text)}
    cited: set[str] = set()
    for i, c in enumerate(claims, 1):
        source = fact_sheet.source(c.get("source_id"))
        if source is None:
            errs.append(f"claim {i}: source_id '{c.get('source_id')}' is not in SOURCES.")
            continue
        cited.add(source.id)
        if not c.get("quote") or norm(c["quote"]) not in norm(source.excerpt):
            errs.append(f'claim {i}: quote is not copied exactly from {source.id} ("{source.excerpt}").')
        if len(words(c.get("text", ""))) > CLAIM_MAX_WORDS:
            errs.append(f"claim {i}: longer than {CLAIM_MAX_WORDS} words.")
        if any(same_fact(c.get("text", ""), e) for e in earlier) or {
            (source.id, n) for n in numbers(c.get("text", ""))
        } & used:
            errs.append(f"claim {i}: repeats a fact from YOUR_RECENT_CLAIMS; bring a new one.")

    allowed = numbers(_number_text(fact_sheet, cited)) | numbers(target.text if target else "") | numbers(question or "")
    if stray := numbers(text) - allowed:
        errs.append(f"numbers {sorted(stray)} are not in any source you cited; cite the source or drop the number.")

    if target is not None:
        opening = " ".join(sents[:2])  # allow a short lead-in before the rebuttal
        if not (numbers(opening) & numbers(target.text) or content_words(opening) & content_words(target.text)):
            errs.append("first sentence does not engage TARGET_CLAIM; reuse its key number or term and answer it.")
    return errs


def _recent_claims(history: list[LineMessage], speaker: str, turns: int = 2) -> list[Claim]:
    own = [line for line in history if line.speaker == speaker][-turns:]
    return [c for line in own for c in line.claims]


def validate_question(out: dict, fact_sheet: FactSheet, history: list[LineMessage]) -> list[str]:
    errs: list[str] = []
    text = out.get("text", "").strip()
    if not text.endswith("?"):
        errs.append('text must end with "?".')
    if not QUESTION_SENTENCES[0] <= len(sentences(text)) <= QUESTION_SENTENCES[1]:
        errs.append(f"text must be {QUESTION_SENTENCES[0]}-{QUESTION_SENTENCES[1]} sentences.")
    if len(words(text)) > QUESTION_MAX_WORDS:
        errs.append(f"text is longer than {QUESTION_MAX_WORDS} words.")
    if out.get("directed_to") not in ("bull", "bear"):
        errs.append('directed_to must be "bull" or "bear".')
    known = {c.id for line in history for c in line.claims}
    ids = out.get("about_claim_ids", [])
    if not 1 <= len(ids) <= 2 or not set(ids) <= known:
        errs.append("about_claim_ids must list 1-2 ids from CLAIMS.")
    said = " ".join(c.text for line in history for c in line.claims)
    if stray := numbers(text) - numbers(_number_text(fact_sheet) + " " + said):
        errs.append(f"numbers {sorted(stray)} are not in CLAIMS, SOURCES or METRICS.")
    if m := VERDICT.search(text):
        errs.append(f"text contains a trade call or verdict ('{m.group(0)}'); remove it.")
    return errs


def validate_positions(out: dict, fact_sheet: FactSheet) -> list[str]:
    errs: list[str] = []
    allowed = numbers(_number_text(fact_sheet))
    for side in ("bull", "bear"):
        pos = out.get(side) or {}
        points = pos.get("points", [])
        if len(points) != 3:
            errs.append(f"{side}: needs exactly 3 points, got {len(points)}.")
        texts = [pos.get("thesis", "")] + [p.get("text", "") for p in points]
        for p in points:
            if fact_sheet.source(p.get("source_id")) is None:
                errs.append(f"{side}: source_id '{p.get('source_id')}' is not in SOURCES.")
        for t in texts:
            if stray := numbers(t) - allowed:
                errs.append(f"{side}: numbers {sorted(stray)} are not in SOURCES or METRICS.")
            if m := VERDICT.search(t):
                errs.append(f"{side}: contains a trade call ('{m.group(0)}').")
    return errs

# ---- Gemini call (tests swap `_generate`) ----

_client = None
last_error: str | None = None  # Google's reason for the latest failed call (never contains the key)


def _generate(system: str, user: str, schema: type[BaseModel], temperature: float) -> dict:
    global _client
    from google import genai
    from google.genai import types

    if _client is None:
        # A stuck call fails after 20 s instead of freezing the debate.
        _client = genai.Client(api_key=config.GEMINI_API_KEY, http_options=types.HttpOptions(timeout=20_000))
    resp = _client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            response_mime_type="application/json",
            response_schema=schema,
            thinking_config=types.ThinkingConfig(thinking_level="minimal"),  # speed: ~1.5 s budget between turns
        ),
    )
    return json.loads(resp.text)


def _call(
    system: str, user: str, schema: type[BaseModel], temperature: float, validate: Callable[[dict], list[str]]
) -> dict | None:
    """One call plus one retry with the errors fed back. None if both fail."""
    global last_error
    last_error = None
    prompt, errs = user, []
    for _ in range(MAX_RETRIES + 1):
        try:
            out = schema.model_validate(_generate(system, prompt, schema, temperature)).model_dump()
            errs = validate(out)
        except (ValueError, ValidationError) as e:  # bad JSON or wrong shape
            errs = [f"output did not match the schema: {str(e)[:200]}"]
        except Exception as e:  # network / API error: don't burn the retry on a re-prompt
            print(f"[agents] Gemini call failed: {e}")
            last_error = str(e)[:300]
            return None
        if not errs:
            return out
        prompt = user + "\n\nYOUR PREVIOUS ANSWER WAS REJECTED. Fix every error and answer again:\n- " + "\n- ".join(errs)
    print(f"[agents] dropped after retry: {errs}")
    return None

# ---- Context builders ----

def _facts(fact_sheet: FactSheet) -> dict:
    return {
        "COMPANY": f"{fact_sheet.company} ({fact_sheet.ticker}), figures as of {fact_sheet.as_of}",
        "SOURCES": [{"id": s.id, "kind": s.kind, "label": s.label, "excerpt": s.excerpt} for s in fact_sheet.sources],
        "METRICS": [
            {"label": m.label, "value": show_metric(m.value, m.unit), "formula": m.formula, "source_ids": m.source_ids}
            for m in fact_sheet.metrics
        ],
        "DEBT": [
            {**d.model_dump(exclude={"amount_usd"}), "amount": money(d.amount_usd)} for d in fact_sheet.debt
        ],
    }


def _transcript(history: list[LineMessage]) -> list[dict]:
    return [{"turn": l.turn, "speaker": l.speaker, "text": l.text} for l in history[-HISTORY_LINES:]]


def pick_target(history: list[LineMessage], speaker: str) -> Claim | None:
    """The claim `speaker` must answer: the strongest claim in the opponent's
    latest line. Strongest = verified > pending > contested > unsupported."""
    opponent = "bear" if speaker == "bull" else "bull"
    last = next((l for l in reversed(history) if l.speaker == opponent and l.claims), None)
    if last is None:
        return None
    rank = {"verified": 0, "pending": 1, "contested": 2, "unsupported": 3}
    return min(last.claims, key=lambda c: rank[c.label])


def to_line(text: str, claims: list[dict], speaker: str, turn: int, from_user: bool = False) -> LineMessage:
    return LineMessage(
        turn=turn,
        speaker=speaker,
        from_user=from_user,
        text=text,
        claims=[Claim(id=f"t{turn}c{i}", text=c["text"], source_id=c["source_id"]) for i, c in enumerate(claims, 1)],
    )

# ---- Public API (what the debate loop in main.py calls) ----

def generate_positions(fact_sheet: FactSheet) -> Positions:
    """Thesis + 3 cited points per side for the side panels."""
    if not config.GEMINI_API_KEY:
        return Positions.model_validate(_example("positions.json"))
    ids = [s.id for s in fact_sheet.sources]
    out = _call(
        SYSTEM_PROMPTS["positions"], json.dumps(_facts(fact_sheet), indent=1), _positions_schema(ids), 0.4,
        lambda o: validate_positions(o, fact_sheet),
    )
    if out is None:
        return Positions(bull={"thesis": "", "points": []}, bear={"thesis": "", "points": []})
    return Positions.model_validate(out)


def generate_turn(
    fact_sheet: FactSheet,
    history: list[LineMessage],
    speaker: Side,
    turn: int,
    question: str | None = None,
    target: Claim | None | Literal["auto"] = "auto",
) -> LineMessage | None:
    """One bull or bear line. `question` is a moderator or user question to
    answer. `target` is the claim to engage: "auto" picks the opponent's
    strongest latest claim, None means nothing to rebut. None if dropped."""
    if not config.GEMINI_API_KEY:
        return _example_turn(speaker, turn)
    if target == "auto":
        target = pick_target(history, speaker)
    mine = {c.id for line in history if line.speaker == speaker for c in line.claims}
    context = {
        **_facts(fact_sheet),
        "TURN": turn,
        "YOU_ARE": speaker,
        "TRANSCRIPT": _transcript(history),
        "TARGET_CLAIM": {"id": target.id, "text": target.text, "yours": target.id in mine} if target else None,
        "QUESTION": question,
        "YOUR_RECENT_CLAIMS": [c.text for c in _recent_claims(history, speaker)],
    }
    out = _call(
        SYSTEM_PROMPTS[speaker], json.dumps(context, indent=1),
        _turn_schema([s.id for s in fact_sheet.sources]), 0.8,
        lambda o: validate_turn(o, fact_sheet, history, target, question, speaker),
    )
    return None if out is None else to_line(out["text"], out["claims"], speaker, turn)


def cross_examine(fact_sheet: FactSheet, history: list[LineMessage], turn: int) -> tuple[LineMessage, Side, Claim] | None:
    """The halfway moderator question. Returns the line, the side that must
    answer, and the claim it's about. None if dropped."""
    claims = [(line.speaker, c) for line in history for c in line.claims]
    if not claims:
        return None
    if not config.GEMINI_API_KEY:
        speaker, claim = claims[-1]
        text = f"{speaker.title()}, the filing is the only thing that counts here. What backs up your point that {claim.text[0].lower() + claim.text[1:].rstrip('.')}?"
        return to_line(text, [], "moderator", turn), speaker, claim
    context = {
        **_facts(fact_sheet),
        "TRANSCRIPT": _transcript(history),
        "CLAIMS": [{"id": c.id, "speaker": s, "text": c.text, "label": c.label} for s, c in claims],
    }
    out = _call(
        SYSTEM_PROMPTS["moderator"], json.dumps(context, indent=1),
        _question_schema([c.id for _, c in claims]), 0.3,
        lambda o: validate_question(o, fact_sheet, history),
    )
    if out is None:
        return None
    about = next(c for _, c in claims if c.id == out["about_claim_ids"][0])
    return to_line(out["text"], [], "moderator", turn), out["directed_to"], about


def relay_question(question: str, turn: int) -> LineMessage:
    """A user's interrupt, shown as "You asked" and voiced by the moderator."""
    return to_line(question.strip(), [], "moderator", turn, from_user=True)


def unsupported_claims(lines: list[LineMessage]) -> list[UnsupportedClaim]:
    """Straight from the fact-checker's labels, so Gemini can't soften them."""
    return [
        UnsupportedClaim(claim_id=c.id, speaker=line.speaker, text=c.text)
        for line in lines
        if line.speaker in ("bull", "bear")
        for c in line.claims
        if c.label == "unsupported"
    ]


def write_brief(fact_sheet: FactSheet, lines: list[LineMessage]) -> CommitteeBrief:
    """TODO(Person 2, task 11): Gemini fills agreed / disputed / open questions,
    citing claim ids. Python adds the unsupported list."""
    raw = _example("committee_brief.json")
    return CommitteeBrief(
        agreed=[AgreedPoint.model_validate(x) for x in raw["agreed"]],
        disputed=[DisputedPoint.model_validate(x) for x in raw["disputed"]],
        open_questions=[OpenQuestion.model_validate(x) for x in raw["open_questions"]],
        unsupported=unsupported_claims(lines),
    )

# ---- Stubs for running without a Gemini key ----

def _example(name: str):
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def _example_turn(speaker: str, turn: int) -> LineMessage:
    examples = [LineMessage.model_validate(x) for x in _example("line_messages.json")]
    same_side = [x for x in examples if x.speaker == speaker] or examples
    pick = same_side[(turn // 2) % len(same_side)]
    return to_line(pick.text, [c.model_dump() for c in pick.claims], speaker, turn)
