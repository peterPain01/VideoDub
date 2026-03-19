"""
edge_tts.py - Microsoft Edge TTS provider using neural voices.

Uses the `edge-tts` package to access Microsoft's neural TTS voices
(vi-VN-HoaiMyNeural, vi-VN-NamMinhNeural) with no API key required.
"""

import asyncio
import concurrent.futures

from tts.base import TTSProvider


class EdgeTTSProvider(TTSProvider):
    """
    Free TTS provider using Microsoft Edge neural voices.

    Voices: vi-VN-HoaiMyNeural (female), vi-VN-NamMinhNeural (male)
    Rate:   "+0%" default, e.g. "+10%" faster, "-10%" slower
    Pitch:  "+0Hz" default, e.g. "+5Hz" higher
    """

    def __init__(
        self,
        voice: str = "vi-VN-HoaiMyNeural",
        rate: str = "+0%",
        pitch: str = "+0Hz",
    ):
        self._voice = voice
        self._rate = rate
        self._pitch = pitch

    @property
    def name(self) -> str:
        return "edge"

    def synthesize(self, text: str, voice_id: str | None = None) -> bytes:
        """
        Synthesize text to MP3 bytes via Edge TTS.

        Runs the async edge-tts call in a dedicated thread so it works
        whether or not an event loop is already running (e.g. uvicorn).

        Args:
            text: Text to synthesize
            voice_id: Optional voice override; uses self._voice if not given

        Returns:
            MP3 audio bytes, or b"" on failure
        """
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, self._synthesize_async(text, voice_id))
                return future.result()
        except Exception as e:
            print(f"[Edge TTS] Synthesis failed: {e}")
            return b""

    async def _synthesize_async(self, text: str, voice_id: str | None) -> bytes:
        import edge_tts

        voice = voice_id or self._voice
        communicate = edge_tts.Communicate(text, voice, rate=self._rate, pitch=self._pitch)

        audio_chunks = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])

        return b"".join(audio_chunks)

    def list_voices(self) -> list[dict]:
        return [
            {
                "id": "vi-VN-HoaiMyNeural",
                "name": "Vietnamese Female (HoaiMy)",
                "language": "vi",
                "provider": "edge",
            },
            {
                "id": "vi-VN-NamMinhNeural",
                "name": "Vietnamese Male (NamMinh)",
                "language": "vi",
                "provider": "edge",
            },
        ]
