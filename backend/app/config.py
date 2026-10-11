"""Reads settings from environment variables (.env locally, dashboard on Railway)."""
import os

from dotenv import load_dotenv

load_dotenv()


def _env(name: str, default: str) -> str:
    """Stray spaces pasted into a dashboard value would silently break a key or voice id."""
    return os.getenv(name, default).strip()


GEMINI_API_KEY = _env("GEMINI_API_KEY", "")
GEMINI_MODEL = _env("GEMINI_MODEL", "gemini-3.5-flash")

ELEVENLABS_API_KEY = _env("ELEVENLABS_API_KEY", "")
VOICE_ID_BULL = _env("ELEVENLABS_VOICE_BULL", "")
VOICE_ID_BEAR = _env("ELEVENLABS_VOICE_BEAR", "")
VOICE_ID_MODERATOR = _env("ELEVENLABS_VOICE_MODERATOR", "")

SUPABASE_URL = _env("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = _env("SUPABASE_SERVICE_KEY", "")

HF_API_TOKEN = _env("HF_API_TOKEN", "")

# SEC requires a descriptive User-Agent with contact info on every request.
SEC_USER_AGENT = _env("SEC_USER_AGENT", "BullVsBear hackathon contact@example.com")

FRONTEND_ORIGIN = _env("FRONTEND_ORIGIN", "http://localhost:3000")

# Turn voice off while iterating on debate text to save ElevenLabs credits.
VOICE_ENABLED = _env("VOICE_ENABLED", "false").lower() == "true"

MAX_TURNS = int(_env("MAX_TURNS", "8"))  # bull + bear lines, not counting moderator or interrupts

# Off switch for the NLI fact-checker (e.g. if it runs the server out of memory): labels stay "pending".
FACT_CHECK = _env("FACT_CHECK", "true").lower() == "true"

# Longest a line waits for fact-check labels before going out with "pending".
FACT_CHECK_TIMEOUT = float(_env("FACT_CHECK_TIMEOUT", "8"))

# Keep the debate one line ahead of playback (off = generate as fast as possible, for tests/scripts).
PACING = _env("PACING", "true").lower() == "true"

# Each user interrupt adds 3 lines (question + both sides); capped to protect voice credits.
MAX_INTERRUPTS = int(_env("MAX_INTERRUPTS", "3"))
