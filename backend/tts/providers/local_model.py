"""
local_model.py - Local TTS model provider (stub).

Placeholder for future local TTS engines such as:
- VITS / VITS2
- Coqui TTS
- Bark
- Piper
- Any HTTP-based local TTS server

To implement:
1. Install your local TTS model
2. Fill in synthesize() with your model's inference code
3. Set TTS_PROVIDER=local in .env
"""

from tts.base import TTSProvider


class LocalModelProvider(TTSProvider):
    """
    Local TTS model provider (stub for future implementation).

    Example implementation for a local HTTP TTS server:

        def synthesize(self, text, voice_id=None):
            import requests
            response = requests.post(
                "http://localhost:5555/tts",
                json={"text": text, "voice": voice_id or "default"},
            )
            return response.content
    """

    def __init__(self, model_path: str = "", server_url: str = "http://localhost:5555"):
        self._model_path = model_path
        self._server_url = server_url

    @property
    def name(self) -> str:
        return "local"

    def synthesize(self, text: str, voice_id: str | None = None) -> bytes:
        """
        Convert text to speech using a local model.

        Override this method with your local TTS implementation.
        """
        # ── Option A: Local HTTP TTS server ──
        # Uncomment and configure for your setup:
        #
        # import requests
        # try:
        #     response = requests.post(
        #         f"{self._server_url}/tts",
        #         json={"text": text, "voice": voice_id or "default"},
        #         timeout=30,
        #     )
        #     response.raise_for_status()
        #     return response.content
        # except Exception as e:
        #     print(f"[TTS Local] Error: {e}")
        #     return b""

        # ── Option B: Direct model inference ──
        # Load and run your model here (e.g. VITS, Coqui, Piper)

        raise NotImplementedError(
            "Local TTS model is not configured yet. "
            "Edit tts/providers/local_model.py to add your model, "
            "or set TTS_PROVIDER=google in .env to use Google TTS."
        )

    def list_voices(self) -> list[dict]:
        """List available local voices."""
        return [
            {
                "id": "local-default",
                "name": "Local Model (not configured)",
                "language": "vi",
                "provider": self.name,
            }
        ]
