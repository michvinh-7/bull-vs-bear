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
│   │   ├── metrics.py     #   Person 1: leverage, coverage, floating %, maturities, liquidity
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
└── render.yaml            # Backend deploy
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
```

Set `NEXT_PUBLIC_USE_MOCK=false` to talk to the real backend.

## API

| Method | Path | Returns |
|---|---|---|
| GET | `/health` | `{ok: true}` |
| GET | `/companies` | pre-cached demo companies |
| POST | `/debates` `{ticker}` | `{debate_id}` |
| GET | `/debates/{id}` | full debate for replay |
| GET | `/debates/{id}/brief` | committee brief |
| WS | `/ws/debates/{id}` | streams `fact_sheet`, `positions`, `turn_start` + `line` per turn, `brief`; accepts `{type: "interrupt", question}` |

## Shared data shapes

See [shared/README.md](shared/README.md) for the shapes, how ids connect them, the WebSocket protocol and how to change them.

## Ground rules

- **The AI never does math.** Gemini reads and argues; Python calculates.
- **The AI never decides.** No buy, sell or verdict anywhere. The brief ends with *"This summarizes the debate. It is not investment advice."*
- **Every claim cites a source.** No citation means it's labeled Unsupported.
- **API keys stay on the backend.** The browser never talks to Gemini or ElevenLabs.
- **Test with text before voice.** Keep `VOICE_ENABLED=false` until the debate reads well.
- **Deploy in the first two hours.** Frontend → Vercel (root `frontend/`), backend → Render (`render.yaml`).
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
