"""Reads settings from environment variables (.env locally, dashboard on Railway)."""
import os

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
VOICE_ID_BULL = os.getenv("ELEVENLABS_VOICE_BULL", "")
VOICE_ID_BEAR = os.getenv("ELEVENLABS_VOICE_BEAR", "")
VOICE_ID_MODERATOR = os.getenv("ELEVENLABS_VOICE_MODERATOR", "")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

HF_API_TOKEN = os.getenv("HF_API_TOKEN", "")

# SEC requires a descriptive User-Agent with contact info on every request.
SEC_USER_AGENT = os.getenv("SEC_USER_AGENT", "BullVsBear hackathon contact@example.com")

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")

# Turn voice off while iterating on debate text to save ElevenLabs credits.
VOICE_ENABLED = os.getenv("VOICE_ENABLED", "false").lower() == "true"

MAX_TURNS = int(os.getenv("MAX_TURNS", "8"))  # bull + bear lines, not counting moderator or interrupts

# Off switch for the NLI fact-checker (e.g. if it runs the server out of memory): labels stay "pending".
FACT_CHECK = os.getenv("FACT_CHECK", "true").lower() == "true"

# Longest a line waits for fact-check labels before going out with "pending".
FACT_CHECK_TIMEOUT = float(os.getenv("FACT_CHECK_TIMEOUT", "8"))

# Keep the debate one line ahead of playback (off = generate as fast as possible, for tests/scripts).
PACING = os.getenv("PACING", "true").lower() == "true"

# Each user interrupt adds 3 lines (question + both sides); capped to protect voice credits.
MAX_INTERRUPTS = int(os.getenv("MAX_INTERRUPTS", "3"))
