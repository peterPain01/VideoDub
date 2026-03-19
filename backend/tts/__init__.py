"""
tts - Pluggable Text-to-Speech package.

Usage:
    from tts import text_to_speech, list_voices

    audio_bytes = text_to_speech("Xin chào thế giới")
    voices = list_voices()

To change provider, set TTS_PROVIDER in .env:
    TTS_PROVIDER=edge         # Free, Microsoft neural Vietnamese voices (default)
    TTS_PROVIDER=google       # Free, no API key (fallback)
    TTS_PROVIDER=elevenlabs   # Premium, requires ELEVENLABS_API_KEY
    TTS_PROVIDER=local        # Your own local model
"""

from tts.engine import create_engine

# Initialize engine at import time (singleton)
_engine = create_engine()


def text_to_speech(text: str, voice_id: str | None = None) -> bytes:
    """
    Convert text to speech audio (MP3 bytes).

    Drop-in replacement for the old tts.text_to_speech() function.

    Args:
        text: Vietnamese text to convert
        voice_id: Optional voice ID for the current provider

    Returns:
        MP3 audio as bytes
    """
    return _engine.text_to_speech(text, voice_id)


def list_voices() -> list[dict]:
    """List available voices from the active provider."""
    return _engine.list_voices()


def get_provider_name() -> str:
    """Get the name of the active TTS provider."""
    return _engine.provider_name
