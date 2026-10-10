# Shared data shapes

**Source of truth:** `backend/app/schemas.py`. The JSON Schemas here are generated from it.
Any change gets announced to the whole team.

To change a shape:
1. Edit `backend/app/schemas.py`
2. `cd backend && python -m scripts.export_schemas`
3. Update `frontend/lib/types.ts` and the examples in `shared/examples/`
4. `cd frontend && npm run sync-shapes`
5. `cd backend && pytest`: fails if schemas are stale, examples don't parse, or ids don't resolve

| Shape | Sent | Made by |
|---|---|---|
| `fact_sheet` | once, first | Person 1 (EDGAR + metrics + news) |
| `positions` | once, before turn 1 | Person 2 (Gemini) |
| `line_message` | once per turn | Person 2 (Gemini text) + Person 1 (labels) + ElevenLabs (audio) |
| `committee_brief` | once, last | Person 2 (Gemini) + Python (unsupported list) |

## How ids connect everything

```
fact_sheet.sources[].id  ("S3")  <── metrics[].source_ids, debt[].source_id,
                                     positions.*.points[].source_id, claims[].source_id
claims[].id  ("t2c1")            <── brief.agreed[].claim_ids, disputed[].claim_ids, unsupported[].claim_id
```

A claim cites a **source id**, never free text. The fact-checker reads that source's
`excerpt` (real filing text), not anything the debater wrote. A missing or unknown
`source_id` makes the claim Unsupported automatically.

## WebSocket protocol (`/ws/debates/{id}`)

Server → client, in order:

```
{"type": "fact_sheet", "data": FactSheet}
{"type": "positions",  "data": Positions}
{"type": "turn_start", "turn": 1, "speaker": "bull", "max_turns": 8}   ← show "Bull is thinking…"
{"type": "line",       "data": LineMessage}                            ← labels + audio already attached
... turn_start / line repeat ...
{"type": "usage",      "data": Usage}                                  ← after positions, each line, and before the brief
{"type": "brief",      "data": CommitteeBrief}
{"type": "error",      "message": "..."}
```

Client → server:
- `{"type": "interrupt", "question": "..."}`: becomes the next moderator line with
  `from_user: true`; the side that was due answers it.
- `{"type": "played", "turn": 3}` (optional): line 3 finished playing, for pacing.

`Usage` (running totals for the debate; also saved on the debate as `usage`):
```
{"model": "gemini-3.6-flash", "calls": 19, "input_tokens": 43151, "output_tokens": 3272,
 "thinking_tokens": 0, "voice_chars": 0, "cost_usd": 0.0211}      ← cost_usd is null if the price is unknown
```

Starting a debate: `POST /debates {"ticker": "NWRC", "model": "gemini-3.6-flash", "gemini_api_key": "..."}`.
`model` must be one of `GET /models` (400 otherwise); both fields are optional. The key is never stored or echoed.

## v2 changes (proposed for hour 0)

| Was | Now | Why |
|---|---|---|
| claim has `source` + `passage` written by Gemini | claim has `source_id`; passage is `sources[].excerpt` | The debater could invent the quote it's graded against. Now the fact-checker only sees real filing text, and Gemini's `source_id` can be constrained to an enum of valid ids. |
| `metrics[].source` free text | `source_ids[]` + `label`, `unit`, `formula` | Frontend formats by unit instead of hardcoding names; `formula` shows Python's working ("the AI never does math", visibly) |
| `debt_details: []` untyped | `debt[]` with seniority, fixed/floating, maturity | The whole debate is secured vs unsecured and fixed vs floating. Debaters need it structured. |
| `news[]` separate | news items are `sources` with `kind: "news"` | News gets cited and fact-checked the same way as filings |
| no period | `as_of` | Shows how old the figures are ("FY2025") |
| no thesis data | new `positions` shape | Fills the side panels in the mockup |
| claims have no id; brief is plain strings | `claims[].id`; brief items carry `claim_ids` | Click a brief item to see the source; brief stays traceable |
| `unsupported: [string]` written by Gemini | built in Python from labels | Gemini can't soften or drop unsupported claims |
| `open_questions: [string]` | `{question, where_to_look}` | The pitch is "shows you what to check", so the brief says where to check |
| `disputed: {bull, bear}` | adds `topic` | Readable headers; topic tagging comes almost free |
| moderator lines all look the same | `from_user` | UI can show "You asked" for interrupts |
| — | `turn_start` message | Gemini plus TTS takes seconds per turn; the UI shows who's thinking instead of freezing |
| "Points scored" in mockup | frontend counts verified claims per side | Scoring is a verdict; counting verified claims isn't |
