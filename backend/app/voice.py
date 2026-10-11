"""ElevenLabs voices: one per character. Owner: Person 2 (Person 1 is backup).

Test with text before voice: leave VOICE_ENABLED=false until the debate reads well.
Voice never breaks the debate: any failure returns "" and the line plays as text.
"""
import time

import httpx

from . import config, store, usage

VOICES = {
    "bull": config.VOICE_ID_BULL,
    "bear": config.VOICE_ID_BEAR,
    "moderator": config.VOICE_ID_MODERATOR,
}
RETRY_STATUS = {429, 500, 502, 503, 504}
RETRY_WAIT = 1.0
_sleep = time.sleep  # tests swap this


def _tts(voice_id: str, text: str) -> bytes | None:
    """One retry on rate limits, server errors and timeouts; None if it still fails."""
    for attempt in (1, 2):
        try:
            r = httpx.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={"xi-api-key": config.ELEVENLABS_API_KEY, "accept": "audio/mpeg"},
                json={"text": text, "model_id": "eleven_turbo_v2_5"},
                timeout=15,
            )
        except httpx.HTTPError as e:
            print(f"[voice] request failed ({type(e).__name__}), attempt {attempt}")
        else:
            if r.status_code == 200:
                return r.content
            print(f"[voice] ElevenLabs {r.status_code}: {r.text[:120]}")
            if r.status_code not in RETRY_STATUS:
                return None  # bad key, out of credits, bad voice id: retrying won't help
        if attempt == 1:
            _sleep(RETRY_WAIT)
    return None


def setup() -> dict:
    """Which voice settings the server can see, never their values: shown on /health."""
    return {"key": "set" if config.ELEVENLABS_API_KEY else "missing",
            **{speaker: "set" if vid else "missing" for speaker, vid in VOICES.items()}}


def speak(text: str, speaker: str, debate_id: str, turn: int) -> str:
    """Turn a line into speech, upload it, and return a public audio URL ("" on any failure)."""
    voice_id = VOICES.get(speaker)
    if not config.ELEVENLABS_API_KEY or not voice_id:
        missing = "ELEVENLABS_API_KEY" if not config.ELEVENLABS_API_KEY else f"ELEVENLABS_VOICE_{speaker.upper()}"
        print(f"[voice] skipped, {missing} is empty: line plays as text")
        return ""
    audio = _tts(voice_id, text)
    if audio is None:
        return ""
    usage.record_voice(text)  # ElevenLabs bills per character once the clip is made
    try:
        return store.upload_audio(audio, f"{debate_id}/{turn:02d}-{speaker}.mp3")
    except Exception as e:
        print(f"[voice] upload failed: {e}")
        return ""
