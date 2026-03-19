"""
google_tts.py - Google TTS provider using gTTS.

Free, no API key required. Lower quality but reliable fallback.
"""

import io
from tts.base import TTSProvider


class GoogleTTSProvider(TTSProvider):
    """Google Text-to-Speech provider using gTTS (free, no API key)."""

    @property
    def name(self) -> str:
        return "google"

    def synthesize(self, text: str, voice_id: str | None = None) -> bytes:
        """
        Convert text to speech using Google TTS.

        Args:
            text: Vietnamese text to convert
            voice_id: Ignored (gTTS doesn't support voice selection)

        Returns:
            MP3 audio bytes
        """
        if not text or not text.strip():
            return b""

        try:
            from gtts import gTTS

            tts = gTTS(text=text, lang="vi", slow=False)
            mp3_buffer = io.BytesIO()
            tts.write_to_fp(mp3_buffer)
            mp3_buffer.seek(0)
            return mp3_buffer.read()

        except Exception as e:
            print(f"[TTS Google] Error: {e}")
            return b""

    def list_voices(self) -> list[dict]:
        """gTTS only supports one voice per language."""
        return [
            {
                "id": "vi-default",
                "name": "Vietnamese (Default)",
                "language": "vi",
                "provider": self.name,
            }
        ]
