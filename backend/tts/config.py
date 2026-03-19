"""
config.py - TTS configuration loaded from environment variables.

All TTS settings are centralized here. Override via .env file.
"""

import os
from dotenv import load_dotenv

# Load .env file from backend directory
load_dotenv()

# ── Provider Selection ────────────────────────────────────
# Options: "edge" (default), "elevenlabs", "google", "local"
# If "elevenlabs" is selected but no API key is set, falls back to "google"
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "edge")

# ── ElevenLabs Configuration ─────────────────────────────
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # "Rachel" multilingual
ELEVENLABS_MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")

# ── Local Model Configuration ────────────────────────────
LOCAL_MODEL_PATH = os.getenv("LOCAL_MODEL_PATH", "")
LOCAL_SERVER_URL = os.getenv("LOCAL_SERVER_URL", "http://localhost:5555")

# ── Edge TTS Configuration ────────────────────────────────
EDGE_TTS_VOICE = os.getenv("EDGE_TTS_VOICE", "vi-VN-HoaiMyNeural")
EDGE_TTS_RATE  = os.getenv("EDGE_TTS_RATE",  "+0%")    # e.g. "+10%" faster
EDGE_TTS_PITCH = os.getenv("EDGE_TTS_PITCH", "+0Hz")   # e.g. "+5Hz" higher

# ── Cache Configuration ──────────────────────────────────
TTS_CACHE_MAX_SIZE = int(os.getenv("TTS_CACHE_MAX_SIZE", "500"))

# ── Voice Presets ─────────────────────────────────────────
# Pre-defined voice options for quick switching.
# Add your own voice IDs from ElevenLabs Voice Library.
VOICE_PRESETS = {
    "default": {
        "id": ELEVENLABS_VOICE_ID,
        "name": "Default Voice",
        "description": "Default multilingual voice",
    },
    # ── Edge TTS Vietnamese voices ──
    "female_vi": {
        "id": "vi-VN-HoaiMyNeural",
        "name": "Vietnamese Female (HoaiMy)",
        "description": "Microsoft neural Vietnamese female voice",
    },
    "male_vi": {
        "id": "vi-VN-NamMinhNeural",
        "name": "Vietnamese Male (NamMinh)",
        "description": "Microsoft neural Vietnamese male voice",
    },
}
