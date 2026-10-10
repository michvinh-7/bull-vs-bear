"""FastAPI app: the producer. Runs the debate and calls every other service.

Endpoints
  GET  /health                  liveness check for Railway
  GET  /companies               the pre-cached demo companies
  GET  /companies/search?q=     up to 10 companies matching a name or ticker
  POST /debates                 start a debate -> {debate_id}; 400 empty, 404 unknown ticker
  GET  /debates/{id}            full debate for replay (fact sheet, lines, brief)
  GET  /debates/{id}/brief      committee brief only
  WS   /ws/debates/{id}         streams the debate; accepts interrupts
"""
import asyncio
import uuid

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from . import agents, companies, config, store, verify, voice
from .companies import Company
from .facts import build_fact_sheet
from .schemas import (
    CommitteeBrief,
    Debate,
    StartDebateRequest,
    StartDebateResponse,
)

app = FastAPI(title="Bull vs Bear")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_ORIGIN, "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    # Which services are configured, never the keys themselves.
    return {
        "ok": True,
        "gemini": {"model": config.GEMINI_MODEL, "key": "set" if config.GEMINI_API_KEY else "missing"},
        "voice": config.VOICE_ENABLED,
        "storage": "supabase" if store._client else "memory",
    }


@app.get("/companies", response_model=list[Company], response_model_exclude_none=True)
def list_companies():
    return companies.DEMO_COMPANIES


@app.get("/companies/search", response_model=list[Company], response_model_exclude_none=True)
def search_companies(q: str = Query(..., min_length=1, max_length=50)):
    return companies.search(q)


@app.post("/debates", response_model=StartDebateResponse)
def start_debate(req: StartDebateRequest):
    ticker = req.ticker.strip().upper()
    if not ticker:
        raise HTTPException(400, "Ticker is required")
    if not companies.is_known(ticker):
        raise HTTPException(404, f"No public company with ticker {ticker}")
    debate = Debate(id=uuid.uuid4().hex[:12], ticker=ticker, max_turns=config.MAX_TURNS)
    store.save_debate(debate)
    return StartDebateResponse(debate_id=debate.id)


@app.get("/debates/{debate_id}", response_model=Debate)
def get_debate(debate_id: str):
    debate = store.load_debate(debate_id)
    if not debate:
        raise HTTPException(404, "Debate not found")
    return debate


@app.get("/debates/{debate_id}/brief", response_model=CommitteeBrief)
def get_brief(debate_id: str):
    debate = store.load_debate(debate_id)
    if not debate or not debate.brief:
        raise HTTPException(404, "Brief not ready")
    return debate.brief


@app.websocket("/ws/debates/{debate_id}")
async def debate_socket(ws: WebSocket, debate_id: str):
    """Server -> client messages, in order:
         {"type": "fact_sheet", "data": FactSheet}
         {"type": "positions",  "data": Positions}
         {"type": "turn_start", "turn": int, "speaker": str, "max_turns": int}   (show "thinking…")
         {"type": "line",       "data": LineMessage}                             (labels + audio ready)
         ... turn_start / line repeat ...
         {"type": "brief",      "data": CommitteeBrief}
         {"type": "error",      "message": str}
       Client -> server messages:
         {"type": "interrupt", "question": str}

    Order of lines: bull and bear alternate for max_turns lines. Halfway, the
    moderator cross-examines one side; that side answers and the other
    rebuts. A user interrupt is relayed by the moderator ("You asked"), the
    side that was due answers it, the other side responds, then the debate
    resumes. Each interrupt adds 3 lines; at most MAX_INTERRUPTS per debate.
    """
    await ws.accept()
    debate = store.load_debate(debate_id)
    if not debate:
        await ws.send_json({"type": "error", "message": "Debate not found"})
        await ws.close()
        return

    # Finished debates replay straight from storage.
    if debate.status == "done":
        await _replay(ws, debate)
        return

    interrupts: asyncio.Queue[str] = asyncio.Queue()
    listener = asyncio.create_task(_listen_for_interrupts(ws, interrupts))

    try:
        debate.fact_sheet = await asyncio.to_thread(build_fact_sheet, debate.ticker)
        await ws.send_json({"type": "fact_sheet", "data": debate.fact_sheet.model_dump()})
        debate.positions = await asyncio.to_thread(agents.generate_positions, debate.fact_sheet)
        await ws.send_json({"type": "positions", "data": debate.positions.model_dump()})

        sheet = debate.fact_sheet
        planned = debate.max_turns + 1  # analyst lines + the halfway question; shown as "Turn x of y"
        interrupts_used = 0

        async def start(speaker: str) -> int:
            turn = len(debate.lines) + 1
            await ws.send_json({"type": "turn_start", "turn": turn, "speaker": speaker, "max_turns": planned})
            return turn

        async def emit(line) -> bool:
            """Fact-check and voice in parallel, save, then send the line complete."""
            if line is None:  # Gemini broke the rules twice: drop the turn, never show broken data
                return False
            claims, audio_url = await asyncio.gather(
                asyncio.to_thread(verify.check_claims, line.claims, sheet),
                asyncio.to_thread(voice.speak, line.text, line.speaker, debate.id, line.turn)
                if config.VOICE_ENABLED
                else asyncio.sleep(0, result=""),
            )
            line.claims, line.audio_url = claims, audio_url
            debate.lines.append(line)
            store.save_debate(debate)
            await ws.send_json({"type": "line", "data": line.model_dump()})
            return True

        api_failures = 0

        async def analyst(side: str, question: str | None = None, target="auto") -> bool:
            nonlocal api_failures
            turn = await start(side)
            line = await asyncio.to_thread(agents.generate_turn, sheet, debate.lines, side, turn, question, target)
            # Gemini itself failing (not a rule break) twice in a row: stop and say why, instead of
            # quietly finishing with no lines.
            api_failures = api_failures + 1 if line is None and agents.last_error else 0
            if api_failures >= 2:
                raise RuntimeError(
                    f"The debate engine is unavailable right now ({agents.last_error}). "
                    "Try again in a minute, or replay a saved debate."
                )
            return await emit(line)

        next_side, spoken, cross_examined = "bull", 0, False
        redos = 2  # a dropped turn gets a fresh try, so one side doesn't speak twice in a row
        while spoken < debate.max_turns:
            if not interrupts.empty():
                question = interrupts.get_nowait()
                if interrupts_used < config.MAX_INTERRUPTS:
                    interrupts_used += 1
                    planned += 3
                    await emit(agents.relay_question(question, await start("moderator")))
                    await analyst(next_side, question, target=None)  # answers the user, nothing to rebut
                    await analyst(_other(next_side), question)  # answers too, and engages the first answer
                continue

            if spoken == debate.max_turns // 2 and not cross_examined:
                cross_examined = True
                asked = await asyncio.to_thread(agents.cross_examine, sheet, debate.lines, await start("moderator"))
                if asked:
                    line, side, about = asked
                    await emit(line)
                    await analyst(side, line.text, about)  # defends or rebuts the claim the question is about
                    next_side, spoken = _other(side), spoken + 1
                    continue
                planned -= 1  # moderator dropped: no extra line after all

            if await analyst(next_side):
                next_side, spoken = _other(next_side), spoken + 1
            elif redos:
                redos -= 1  # dropped: same side tries again without using up the debate
            else:
                spoken += 1  # out of redos: use up the slot, but the same side still speaks next
                # so nobody speaks twice in a row

        debate.brief = await asyncio.to_thread(agents.write_brief, debate.fact_sheet, debate.lines)
        debate.status = "done"
        store.save_debate(debate)
        await ws.send_json({"type": "brief", "data": debate.brief.model_dump()})
    except WebSocketDisconnect:
        pass
    except Exception as e:  # keep the demo alive; log and tell the client
        debate.status = "error"
        store.save_debate(debate)
        await ws.send_json({"type": "error", "message": str(e)})
    finally:
        listener.cancel()


def _other(side: str) -> str:
    return "bear" if side == "bull" else "bull"


async def _listen_for_interrupts(ws: WebSocket, queue: asyncio.Queue):
    try:
        while True:
            msg = await ws.receive_json()
            if msg.get("type") == "interrupt" and msg.get("question"):
                await queue.put(msg["question"])
    except (WebSocketDisconnect, RuntimeError):
        pass


async def _replay(ws: WebSocket, debate: Debate):
    if debate.fact_sheet:
        await ws.send_json({"type": "fact_sheet", "data": debate.fact_sheet.model_dump()})
    if debate.positions:
        await ws.send_json({"type": "positions", "data": debate.positions.model_dump()})
    for line in debate.lines:
        await ws.send_json({"type": "line", "data": line.model_dump()})
        await asyncio.sleep(0.5)
    if debate.brief:
        await ws.send_json({"type": "brief", "data": debate.brief.model_dump()})
