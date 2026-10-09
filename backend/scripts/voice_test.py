"""Checks ElevenLabs before the debate depends on it, and helps pick the 3 voices.

Run from backend/:
  python -m scripts.voice_test                          key, credits, and the voices on the account
  python -m scripts.voice_test sample bull ID [ID ...]  one sample clip per voice, timed, saved to voice_samples/
  python -m scripts.voice_test upload ID                voice one clip and upload it to the Supabase audio bucket

Samples cost ~150 characters each. VOICE_ENABLED does not need to be on.
"""
import sys
import time
from pathlib import Path

import httpx

from app import config, store

API = "https://api.elevenlabs.io/v1"
MODEL = "eleven_turbo_v2_5"  # same model voice.py uses
OUT = Path(__file__).resolve().parents[1] / "voice_samples"
TARGET_SECONDS = 1.5  # contract: under ~1.5 s of silence between turns

LINES = {
    "bull": "Leverage is down to 2.1 times, and 80 percent of the debt is fixed rate. "
            "Higher rates barely touch them. That's page 47 of the 10-K.",
    "bear": "Fixed today, sure. But 1.2 billion matures in 2027, and they'll refinance it at "
            "double the coupon. Look at the maturity table on page 52.",
    "moderator": "Both sides agree leverage has fallen. The open question is refinancing risk "
                 "in 2027. Bull, how do they cover that wall?",
}


def _headers() -> dict:
    if not config.ELEVENLABS_API_KEY:
        sys.exit("ELEVENLABS_API_KEY is empty in backend/.env")
    return {"xi-api-key": config.ELEVENLABS_API_KEY}


def _tts(voice_id: str, text: str) -> tuple[bytes, float]:
    start = time.perf_counter()
    r = httpx.post(
        f"{API}/text-to-speech/{voice_id}",
        headers={**_headers(), "accept": "audio/mpeg"},
        json={"text": text, "model_id": MODEL},
        timeout=60,
    )
    seconds = time.perf_counter() - start
    if r.status_code != 200:
        sys.exit(f"text-to-speech failed for {voice_id}: {r.status_code} {r.text[:300]}")
    return r.content, seconds


def check() -> None:
    r = httpx.get(f"{API}/user/subscription", headers=_headers(), timeout=30)
    if r.status_code == 200:
        sub = r.json()
        left = sub["character_limit"] - sub["character_count"]
        print(f"Key OK. Plan: {sub.get('tier')}. Credits: {left:,} of {sub['character_limit']:,} characters left.")
    elif r.status_code == 401:
        print("Credits: not shown (key has no User read permission, or the key is invalid).")
    else:
        print(f"Credits: could not read ({r.status_code}).")

    r = httpx.get(f"{API}/voices", headers=_headers(), timeout=30)
    if r.status_code != 200:
        sys.exit(f"Listing voices failed: {r.status_code} {r.text[:300]}")
    voices = r.json()["voices"]
    print(f"\n{len(voices)} voices:\n")
    print(f"{'voice_id':<22} {'name':<22} {'gender':<8} {'accent':<12} description")
    for v in sorted(voices, key=lambda v: v["name"]):
        labels = v.get("labels") or {}
        desc = labels.get("description") or labels.get("descriptive") or labels.get("use_case") or ""
        print(f"{v['voice_id']:<22} {v['name'][:22]:<22} {labels.get('gender', ''):<8} "
              f"{labels.get('accent', '')[:12]:<12} {desc}")
    print("\nNext: python -m scripts.voice_test sample bull <voice_id> <voice_id> ...")


def sample(role: str, voice_ids: list[str]) -> None:
    if role not in LINES:
        sys.exit(f"role must be one of: {', '.join(LINES)}")
    OUT.mkdir(exist_ok=True)
    for voice_id in voice_ids:
        audio, seconds = _tts(voice_id, LINES[role])
        path = OUT / f"{role}-{voice_id}.mp3"
        path.write_bytes(audio)
        flag = "OK" if seconds <= TARGET_SECONDS else f"slow (target {TARGET_SECONDS}s)"
        print(f"{path.relative_to(OUT.parent)}  {seconds:.2f}s  {flag}")
    print(f"\nOpen {OUT} and listen.")


def upload(voice_id: str) -> None:
    audio, seconds = _tts(voice_id, LINES["moderator"])
    url = store.upload_audio(audio, "voice-test/sample.mp3")
    if not url:
        sys.exit("Upload skipped: SUPABASE_URL / SUPABASE_SERVICE_KEY are empty in backend/.env")
    print(f"Voiced in {seconds:.2f}s and uploaded. Open this link and check it plays:\n{url}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        check()
    elif args[0] == "sample" and len(args) >= 3:
        sample(args[1], args[2:])
    elif args[0] == "upload" and len(args) == 2:
        upload(args[1])
    else:
        sys.exit(__doc__)
