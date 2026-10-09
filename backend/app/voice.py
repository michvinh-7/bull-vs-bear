"""ElevenLabs voices: one per character. Owner: Person 2 (Person 1 is backup).

Test with text before voice: leave VOICE_ENABLED=false until the debate reads well.
"""
import httpx

from . import config, store

VOICES = {
    "bull": config.VOICE_ID_BULL,
    "bear": config.VOICE_ID_BEAR,
    "moderator": config.VOICE_ID_MODERATOR,
}


def speak(text: str, speaker: str, debate_id: str, turn: int) -> str:
    """Turn a line into speech, upload it, and return a public audio URL ("" on failure)."""
    voice_id = VOICES.get(speaker)
    if not config.ELEVENLABS_API_KEY or not voice_id:
        return ""
    r = httpx.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={"xi-api-key": config.ELEVENLABS_API_KEY, "accept": "audio/mpeg"},
        json={"text": text, "model_id": "eleven_turbo_v2_5"},
        timeout=60,
    )
    if r.status_code != 200:
        return ""
    return store.upload_audio(r.content, f"{debate_id}/{turn:02d}-{speaker}.mp3")
