"""
tts.py - Text-to-Speech module for VideoDub.

Supports multiple TTS providers: edge (default), google, elevenlabs, local.
Configured via TTS_PROVIDER environment variable.
"""

import asyncio
import io
import os
import hashlib
import logging
from collections import OrderedDict

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Configuration
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "edge").lower()
TTS_CACHE_MAX_SIZE = int(os.getenv("TTS_CACHE_MAX_SIZE", "500"))

# Edge TTS settings
EDGE_TTS_VOICE = os.getenv("EDGE_TTS_VOICE", "vi-VN-HoaiMyNeural")
EDGE_TTS_RATE = os.getenv("EDGE_TTS_RATE", "+0%")
EDGE_TTS_PITCH = os.getenv("EDGE_TTS_PITCH", "+0Hz")

# ElevenLabs settings
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
ELEVENLABS_MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")

# Local TTS settings
LOCAL_SERVER_URL = os.getenv("LOCAL_SERVER_URL", "http://localhost:5555")

# In-memory LRU cache
_cache: OrderedDict = OrderedDict()


def _cache_key(text: str, voice_id: str | None) -> str:
    raw = f"{TTS_PROVIDER}:{voice_id or ''}:{text}"
    return hashlib.md5(raw.encode()).hexdigest()


def _cache_get(key: str) -> bytes | None:
    if key in _cache:
        _cache.move_to_end(key)
        return _cache[key]
    return None


def _cache_set(key: str, value: bytes) -> None:
    if key in _cache:
        _cache.move_to_end(key)
    else:
        _cache[key] = value
        while len(_cache) > TTS_CACHE_MAX_SIZE:
            _cache.popitem(last=False)


# ── Provider implementations ────────────────────────────────────────────────

def _tts_edge(text: str, voice_id: str | None) -> bytes:
    import edge_tts

    voice = voice_id or EDGE_TTS_VOICE

    async def _generate() -> bytes:
        communicate = edge_tts.Communicate(text, voice, rate=EDGE_TTS_RATE, pitch=EDGE_TTS_PITCH)
        buf = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        return buf.getvalue()

    # Called from a thread (via asyncio.to_thread), so we create a fresh loop.
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_generate())
    finally:
        loop.close()


def _tts_google(text: str, voice_id: str | None) -> bytes:
    from gtts import gTTS

    buf = io.BytesIO()
    gTTS(text=text, lang="vi").write_to_fp(buf)
    return buf.getvalue()


def _tts_elevenlabs(text: str, voice_id: str | None) -> bytes:
    from elevenlabs.client import ElevenLabs

    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    vid = voice_id or ELEVENLABS_VOICE_ID
    audio = client.generate(text=text, voice=vid, model=ELEVENLABS_MODEL)
    buf = io.BytesIO()
    for chunk in audio:
        buf.write(chunk)
    return buf.getvalue()


def _tts_local(text: str, voice_id: str | None) -> bytes:
    import json
    import urllib.request

    payload = json.dumps({"text": text, "voice_id": voice_id}).encode()
    req = urllib.request.Request(
        f"{LOCAL_SERVER_URL}/tts",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return resp.read()


# ── Public API ───────────────────────────────────────────────────────────────

def text_to_speech(text: str, voice_id: str | None = None) -> bytes:
    """Generate TTS audio. Returns raw MP3 bytes."""
    if not text or not text.strip():
        return b""

    key = _cache_key(text, voice_id)
    cached = _cache_get(key)
    if cached is not None:
        return cached

    if TTS_PROVIDER == "edge":
        data = _tts_edge(text, voice_id)
    elif TTS_PROVIDER == "google":
        data = _tts_google(text, voice_id)
    elif TTS_PROVIDER == "elevenlabs":
        data = _tts_elevenlabs(text, voice_id)
    elif TTS_PROVIDER == "local":
        data = _tts_local(text, voice_id)
    else:
        logger.warning("Unknown TTS provider '%s', falling back to edge", TTS_PROVIDER)
        data = _tts_edge(text, voice_id)

    if data:
        _cache_set(key, data)
    return data


def list_voices() -> list:
    """Return available voices for the current provider."""
    if TTS_PROVIDER == "edge":
        import edge_tts

        async def _get():
            return await edge_tts.list_voices()

        loop = asyncio.new_event_loop()
        try:
            voices = loop.run_until_complete(_get())
        finally:
            loop.close()
        vi_voices = [v for v in voices if v.get("Locale", "").startswith("vi-")]
        return [{"id": v["ShortName"], "name": v["FriendlyName"]} for v in vi_voices]

    if TTS_PROVIDER == "google":
        return [{"id": "vi", "name": "Vietnamese (Google TTS)"}]

    if TTS_PROVIDER == "elevenlabs":
        try:
            from elevenlabs.client import ElevenLabs
            client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
            result = client.voices.get_all()
            return [{"id": v.voice_id, "name": v.name} for v in result.voices]
        except Exception as exc:
            logger.error("Failed to list ElevenLabs voices: %s", exc)
            return [{"id": ELEVENLABS_VOICE_ID, "name": "Default ElevenLabs Voice"}]

    if TTS_PROVIDER == "local":
        return [{"id": "default", "name": "Local TTS Voice"}]

    return []


def get_provider_name() -> str:
    """Return human-readable name of the current TTS provider."""
    return {
        "edge": "Microsoft Edge TTS",
        "google": "Google TTS",
        "elevenlabs": "ElevenLabs",
        "local": "Local TTS",
    }.get(TTS_PROVIDER, TTS_PROVIDER)
