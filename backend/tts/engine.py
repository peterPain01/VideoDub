"""
engine.py - TTS Engine with provider routing, caching, and fallback.

The engine wraps a primary TTSProvider with:
- LRU cache to avoid duplicate API calls
- Automatic fallback to Google TTS on failure
- Runtime provider switching
"""

import hashlib
from collections import OrderedDict

from tts.base import TTSProvider
from tts import config


class TTSEngine:
    """
    TTS Engine with caching and fallback.

    Usage:
        engine = TTSEngine(primary=elevenlabs_provider, fallback=google_provider)
        audio = engine.text_to_speech("Xin chào")
    """

    def __init__(self, primary: TTSProvider, fallback: TTSProvider | None = None):
        self._primary = primary
        self._fallback = fallback
        self._cache: OrderedDict[str, bytes] = OrderedDict()
        self._cache_max_size = config.TTS_CACHE_MAX_SIZE
        print(f"[TTS Engine] Primary: {primary.name}"
              f"{f', Fallback: {fallback.name}' if fallback else ''}"
              f", Cache: {self._cache_max_size} entries")

    @property
    def provider_name(self) -> str:
        return self._primary.name

    def text_to_speech(self, text: str, voice_id: str | None = None) -> bytes:
        """
        Convert text to speech with caching and fallback.

        Args:
            text: Text to synthesize
            voice_id: Optional voice ID (provider-specific)

        Returns:
            MP3 audio bytes
        """
        if not text or not text.strip():
            return b""

        # Check cache
        cache_key = self._make_cache_key(text, voice_id)
        if cache_key in self._cache:
            self._cache.move_to_end(cache_key)
            print(f"[TTS Engine] Cache hit for: '{text[:40]}...'")
            return self._cache[cache_key]

        # Try primary provider
        audio = self._primary.synthesize(text, voice_id)

        if audio:
            self._put_cache(cache_key, audio)
            return audio

        # Try fallback
        if self._fallback:
            print(f"[TTS Engine] Primary failed, trying fallback ({self._fallback.name})...")
            audio = self._fallback.synthesize(text, voice_id)
            if audio:
                self._put_cache(cache_key, audio)
                return audio

        print(f"[TTS Engine] All providers failed for: '{text[:50]}'")
        return b""

    def list_voices(self) -> list[dict]:
        """List voices from primary provider + presets."""
        voices = []

        # Add presets
        for preset_key, preset in config.VOICE_PRESETS.items():
            voices.append({
                "id": preset["id"],
                "name": preset["name"],
                "description": preset.get("description", ""),
                "preset_key": preset_key,
                "provider": self._primary.name,
            })

        # Try to get provider voices
        try:
            provider_voices = self._primary.list_voices()
            # Avoid duplicates
            preset_ids = {v["id"] for v in voices}
            for v in provider_voices:
                if v["id"] not in preset_ids:
                    voices.append(v)
        except Exception as e:
            print(f"[TTS Engine] Error listing provider voices: {e}")

        return voices

    def _make_cache_key(self, text: str, voice_id: str | None) -> str:
        """Create a cache key from text + voice_id."""
        raw = f"{self._primary.name}:{voice_id or 'default'}:{text}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _put_cache(self, key: str, value: bytes):
        """Add to cache, evicting oldest if full."""
        if len(self._cache) >= self._cache_max_size:
            self._cache.popitem(last=False)
        self._cache[key] = value


def create_engine() -> TTSEngine:
    """
    Factory: create a TTSEngine based on configuration.

    Reads TTS_PROVIDER from config and instantiates the right provider.
    Always uses GoogleTTSProvider as fallback.
    """
    from tts.providers.google_tts import GoogleTTSProvider
    fallback = GoogleTTSProvider()

    provider_name = config.TTS_PROVIDER.lower()

    if provider_name == "elevenlabs":
        if not config.ELEVENLABS_API_KEY:
            print("[TTS Engine] No ELEVENLABS_API_KEY set, falling back to Google TTS")
            return TTSEngine(primary=fallback, fallback=None)

        from tts.providers.elevenlabs import ElevenLabsProvider
        primary = ElevenLabsProvider(
            api_key=config.ELEVENLABS_API_KEY,
            default_voice_id=config.ELEVENLABS_VOICE_ID,
            model_id=config.ELEVENLABS_MODEL,
        )
        return TTSEngine(primary=primary, fallback=fallback)

    elif provider_name == "local":
        from tts.providers.local_model import LocalModelProvider
        primary = LocalModelProvider(
            model_path=config.LOCAL_MODEL_PATH,
            server_url=config.LOCAL_SERVER_URL,
        )
        return TTSEngine(primary=primary, fallback=fallback)

    elif provider_name == "google":
        return TTSEngine(primary=fallback, fallback=None)

    elif provider_name == "edge":
        from tts.providers.edge_tts import EdgeTTSProvider
        primary = EdgeTTSProvider(
            voice=config.EDGE_TTS_VOICE,
            rate=config.EDGE_TTS_RATE,
            pitch=config.EDGE_TTS_PITCH,
        )
        return TTSEngine(primary=primary, fallback=fallback)

    else:
        # Default: Edge TTS (free, high quality Microsoft neural voices)
        from tts.providers.edge_tts import EdgeTTSProvider
        primary = EdgeTTSProvider(
            voice=config.EDGE_TTS_VOICE,
            rate=config.EDGE_TTS_RATE,
            pitch=config.EDGE_TTS_PITCH,
        )
        return TTSEngine(primary=primary, fallback=fallback)
