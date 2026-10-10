# Bull vs Bear

An AI credit committee. A user picks a company; a bull and a bear analyst debate its debt out loud
from SEC filings and news; a moderator fact-checks every claim and hands back a committee brief.

> Most AI tells you what to think; ours shows you what to check.

Built for Hack Knight (Finance, Gemini and ElevenLabs tracks).

## Repo layout

```
bull-vs-bear/
├── frontend/              # Person 3: Next.js (home, debate room, brief)
│   ├── app/               #   pages: /, /debate/[id], /brief/[id]
│   └── lib/               #   types.ts (shared shapes), useDebate.ts (WebSocket + audio queue), mock/
├── backend/               # Person 2: FastAPI
│   ├── app/
│   │   ├── main.py        #   Person 2: endpoints + debate loop
│   │   ├── schemas.py     #   the 3 shared shapes (pydantic)
│   │   ├── edgar.py       #   Person 1: SEC EDGAR
│   │   ├── metrics.py     #   Person 1: debt-to-EBITDA, coverage, floating %, maturities, total immediate liquidity
│   │   ├── facts.py       #   Person 1: builds the fact sheet
│   │   ├── verify.py      #   Person 1: Hugging Face fact-checking
│   │   ├── agents.py      #   Person 2: Gemini bull / bear / moderator / brief
│   │   ├── voice.py       #   Person 2: ElevenLabs
│   │   └── store.py       #   Person 2: Supabase (in-memory fallback)
│   └── tests/
├── shared/
│   ├── schemas/           # JSON Schemas, generated from backend/app/schemas.py
│   └── examples/          # Fake data everyone builds against
├── .env.example           # Key names only, never real keys
└── backend/railway.json   # Backend deploy (Railway)
```

Everything runs end to end out of the box on stub data. Each `TODO(Person N)` marks where real work goes.

## Run it locally

**Backend** (Python 3.12+)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env        # fill in the keys you have; blanks are fine to start
uvicorn app.main:app --reload  # http://localhost:8000/docs
pytest                         # checks shared shapes + metrics
```

**Frontend** (Node 20+)

```bash
cd frontend
npm install
cp .env.local.example .env.local   # NEXT_PUBLIC_USE_MOCK=true runs without a backend
npm run dev                        # http://localhost:3000
npm test                           # unit tests (Vitest)
npm run typecheck
```

Set `NEXT_PUBLIC_USE_MOCK=false` to talk to the real backend.

## API

| Method | Path | Returns |
|---|---|---|
| GET | `/health` | `{ok: true}` plus which services are configured |
| GET | `/companies` | pre-cached demo companies |
| GET | `/companies/search?q=` | up to 10 matching companies |
| GET | `/models` | Gemini models the user can pick, with prices |
| POST | `/debates` `{ticker, model?, gemini_api_key?}` | `{debate_id}` |
| GET | `/debates/{id}` | full debate for replay, including `model` and `usage` |
| GET | `/debates/{id}/brief` | committee brief |
| WS | `/ws/debates/{id}` | streams `fact_sheet`, `positions`, `turn_start` + `line` per turn, `usage`, `brief`; accepts `interrupt` and `played` |

## Settings: model, your own key, and usage

The gear icon on every page opens Settings.

- **Gemini model.** Flash (default), Flash-Lite or Pro, listed by `GET /models` with prices. Applies to the next debate.
  Pro needs a key with Pro access and is slow (about 45 s to the first line), so use Flash for live demos.
- **Your own Gemini API key** (optional). The browser keeps it in `sessionStorage` (this tab only) and sends it
  only to our backend with `POST /debates`. The backend holds it in memory for that one debate and drops it when
  the debate ends; it's never saved, logged or returned. ElevenLabs voices still use the team's key.
- **Usage.** Every Gemini call and voice clip in a debate is counted (`backend/app/usage.py`): calls, input,
  output and thinking tokens, voice characters, and an estimated cost. The live debate shows "This debate";
  finished debates add to "All debates in this browser" (`localStorage`, resettable). Costs use Google's
  published prices (thinking billed as output), recorded in `usage.MODELS` with the date they were checked.
  **Update those prices when Google changes them** (Flash's introductory price ends Dec 31, 2026).

A real 8-line debate on Flash-Lite made 19 Gemini calls (rejected lines are retried) and cost about $0.02.

## Shared data shapes

See [shared/README.md](shared/README.md) for the shapes, how ids connect them, the WebSocket protocol and how to change them.

## Ground rules

- **The AI never does math.** Gemini reads and argues; Python calculates.
- **The AI never decides.** No buy, sell or verdict anywhere. The brief ends with *"This summarizes the debate. It is not investment advice."*
- **Every claim cites a source.** No citation means it's labeled Unsupported.
- **API keys stay on the backend.** The browser never talks to Gemini or ElevenLabs.
- **Test with text before voice.** Keep `VOICE_ENABLED=false` until the debate reads well.
- **Deploy in the first two hours.** Frontend → Vercel (root `frontend/`), backend → Railway (root `/backend`, config `/backend/railway.json`).
- **Cache every demo run.** If the network fails on stage, replay a saved debate.
- **Cut, don't slip.** Drop in this order: voice interrupts, WebSockets (switch to generate-then-play), contradiction pass, topic tagging.

## Who owns what

| Person | Role | Owns |
|---|---|---|
| Person 1 | Data and finance | `edgar.py`, `metrics.py`, `facts.py`, `verify.py`, demo number checks |
| Person 2 | AI and backend | `main.py`, `agents.py`, `voice.py`, `store.py`, WebSocket stream |
| Person 3 | Frontend and demo | `frontend/`, audio queue, claim labels, interrupt bar, hosting, pitch deck |

## Git workflow

- `main` always deploys. Work on a branch (`p1/metrics`, `p2/agents`, `p3/debate-room`) and open a PR.
- Keep PRs small and merge often. Stay in your own files to avoid conflicts.
- Never commit `.env`.
