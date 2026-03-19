"""
base.py - Abstract base class for TTS providers.

All TTS providers must implement this interface.
To add a new provider:
  1. Create a new file in tts/providers/
  2. Subclass TTSProvider
  3. Implement synthesize() and list_voices()
  4. Register in config.py PROVIDER_REGISTRY
"""

from abc import ABC, abstractmethod


class TTSProvider(ABC):
    """Abstract base class for Text-to-Speech providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the provider."""
        ...

    @abstractmethod
    def synthesize(self, text: str, voice_id: str | None = None) -> bytes:
        """
        Convert text to speech audio.

        Args:
            text: Text to convert to speech
            voice_id: Optional voice identifier (provider-specific)

        Returns:
            MP3 audio as bytes, or empty bytes on failure
        """
        ...

    @abstractmethod
    def list_voices(self) -> list[dict]:
        """
        List available voices for this provider.

        Returns:
            List of dicts with at least: {"id": "...", "name": "...", "language": "..."}
        """
        ...

    def __repr__(self):
        return f"<TTSProvider: {self.name}>"
