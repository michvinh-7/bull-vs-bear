"""Runs one real debate through the WebSocket loop and prints it. Text only:
voices off, nothing saved to Supabase. Use it to tune the prompts.

Run from backend/:
  python -m scripts.debate_text                         sample company, MAX_TURNS lines
  python -m scripts.debate_text NWRC 6                  ticker and number of bull/bear lines
  python -m scripts.debate_text NWRC 6 "Why does floating debt matter?"   with a user interrupt
"""
import sys
import textwrap
import time

from fastapi.testclient import TestClient

from app import config, main, store
from app.schemas import Debate

config.VOICE_ENABLED = False
store._client = None  # in-memory only

ticker = sys.argv[1] if len(sys.argv) > 1 else "NWRC"
turns = int(sys.argv[2]) if len(sys.argv) > 2 else config.MAX_TURNS
question = sys.argv[3] if len(sys.argv) > 3 else None

if not config.GEMINI_API_KEY:
    sys.exit("GEMINI_API_KEY is empty in backend/.env: this would only replay the examples.")

store.save_debate(Debate(id="cli", ticker=ticker, max_turns=turns))
start = time.perf_counter()
with TestClient(main.app).websocket_connect("/ws/debates/cli") as ws:
    if question:
        ws.send_json({"type": "interrupt", "question": question})
    last = start
    while True:
        msg = ws.receive_json()
        now = time.perf_counter()
        if msg["type"] == "positions":
            for side in ("bull", "bear"):
                p = msg["data"][side]
                print(f"[{side.upper()} THESIS] {p['thesis']}")
                for pt in p["points"]:
                    print(f"   - {pt['text']}  ({pt['source_id']})")
            print()
        elif msg["type"] == "turn_start":
            last = now
        elif msg["type"] == "line":
            line = msg["data"]
            who = "YOU ASKED" if line["from_user"] else line["speaker"].upper()
            print(f"{line['turn']}. {who}  ({now - last:.1f}s)")
            print(textwrap.indent(textwrap.fill(line["text"], 90), "   "))
            for c in line["claims"]:
                print(f"     · [{c['source_id']}] {c['text']}")
            print()
        elif msg["type"] == "error":
            sys.exit(f"ERROR: {msg['message']}")
        elif msg["type"] == "brief":
            break

lines = store.load_debate("cli").lines
analysts = [l for l in lines if l.speaker != "moderator"]
print(f"{len(lines)} lines ({turns + 1 + (3 if question else 0)} planned; any gap = dropped turns) "
      f"in {time.perf_counter() - start:.0f}s; {sum(len(l.text) for l in lines)} characters "
      f"(what ElevenLabs would charge).")
