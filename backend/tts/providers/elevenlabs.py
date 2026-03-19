"""
elevenlabs.py - ElevenLabs TTS provider.

High-quality, natural-sounding Vietnamese voice via ElevenLabs API.
Requires an API key set in .env as ELEVENLABS_API_KEY.
"""

from tts.base import TTSProvider


class ElevenLabsProvider(TTSProvider):
    """ElevenLabs Text-to-Speech provider (premium, API key required)."""

    def __init__(self, api_key: str, default_voice_id: str, model_id: str = "eleven_multilingual_v2"):
        if not api_key:
            raise ValueError("ElevenLabs API key is required")
        self._api_key = api_key
        self._default_voice_id = default_voice_id
        self._model_id = model_id
        self._client = None

    @property
    def name(self) -> str:
        return "elevenlabs"

    def _get_client(self):
        """Lazy-initialize the ElevenLabs client."""
        if self._client is None:
            from elevenlabs import ElevenLabs
            self._client = ElevenLabs(api_key=self._api_key)
        return self._client

    def synthesize(self, text: str, voice_id: str | None = None) -> bytes:
        """
        Convert text to speech using ElevenLabs API.

        Args:
            text: Vietnamese text to convert
            voice_id: ElevenLabs voice ID (uses default if not provided)

        Returns:
            MP3 audio bytes
        """
        if not text or not text.strip():
            return b""

        try:
            client = self._get_client()
            vid = voice_id or self._default_voice_id

            # Generate audio — returns an iterator of bytes chunks
            audio_iterator = client.text_to_speech.convert(
                text=text,
                voice_id=vid,
                model_id=self._model_id,
                output_format="mp3_44100_128",
            )

            # Collect all chunks into bytes
            audio_bytes = b"".join(audio_iterator)
            return audio_bytes

        except Exception as e:
            print(f"[TTS ElevenLabs] Error: {e}")
            return b""

    def list_voices(self) -> list[dict]:
        """List available ElevenLabs voices."""
        try:
            client = self._get_client()
            response = client.voices.get_all()
            voices = []
            for voice in response.voices:
                voices.append({
                    "id": voice.voice_id,
                    "name": voice.name,
                    "language": "multilingual",
                    "provider": self.name,
                })
            return voices

        except Exception as e:
            print(f"[TTS ElevenLabs] Error listing voices: {e}")
            return [{
                "id": self._default_voice_id,
                "name": "Default Voice",
                "language": "vi",
                "provider": self.name,
            }]
