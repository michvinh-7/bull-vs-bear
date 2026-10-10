"""FastAPI app: the producer. Runs the debate and calls every other service.

Endpoints
  GET  /health                  liveness check for Railway
  GET  /companies               the pre-cached demo companies
  POST /debates                 start a debate -> {debate_id}
  GET  /debates/{id}            full debate for replay (fact sheet, lines, brief)
  GET  /debates/{id}/brief      committee brief only
  WS   /ws/debates/{id}         streams the debate; accepts interrupts
"""
import asyncio
import uuid

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from . import agents, config, store, verify, voice
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

DEMO_COMPANIES = [
    # TODO(Person 1): pick the 3 demo companies and fill in real tickers.
    {"ticker": "NWRC", "company": "Northwind Retail Corp (sample)"},
]


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/companies")
def companies():
    return DEMO_COMPANIES


@app.post("/debates", response_model=StartDebateResponse)
def start_debate(req: StartDebateRequest):
    debate = Debate(id=uuid.uuid4().hex[:12], ticker=req.ticker.upper(), max_turns=config.MAX_TURNS)
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

        async def emit(line):
            """Fact-check and voice in parallel, save, then send the line complete."""
            if line is None:  # Gemini broke the rules twice: drop the turn, never show broken data
                return
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

        async def analyst(side: str, question: str | None = None, target="auto"):
            turn = await start(side)
            await emit(await asyncio.to_thread(agents.generate_turn, sheet, debate.lines, side, turn, question, target))

        next_side, spoken, cross_examined = "bull", 0, False
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

            await analyst(next_side)
            next_side, spoken = _other(next_side), spoken + 1

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
