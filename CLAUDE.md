# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VideoDub is a YouTube EN→VI dubbing tool consisting of two components:
- **Backend**: Python FastAPI server that fetches subtitles, translates EN→VI, and generates Vietnamese TTS audio
- **Chrome Extension**: Manifest V3 extension that plays the dubbed audio synchronized with YouTube video playback

## Backend

### Setup & Running

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env  # then edit .env

# Run the server
python main.py
# Or with auto-reload for development:
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The server runs on `http://localhost:8000`. Health check: `GET /`.

### API Endpoints

- `GET /` — health check, returns TTS provider name
- `GET /api/voices` — list available TTS voices for current provider
- `POST /api/subtitles` — main endpoint; body: `{"videoId": "...", "voiceId": "..."}` (voiceId optional)

### Backend Architecture

The pipeline in `main.py:60` flows through four stages:
1. `subtitle.py` — fetches English subtitles from YouTube via `youtube-transcript-api`
2. `translate.py` — translates each segment EN→VI via `deep-translator` (Google Translate)
3. `text_processor.py` — merges short fragments into natural sentences (max 8s per segment)
4. `tts.py` — generates Vietnamese MP3 audio; returns base64-encoded bytes

**Note**: `tts.py` is imported in `main.py` but does not yet exist in the repo. It must export `text_to_speech(text, voice_id)`, `list_voices()`, and `get_provider_name()`.

### TTS Providers (configured via `.env`)

| `TTS_PROVIDER` | Notes |
|---|---|
| `edge` | Default; free, neural quality; uses `edge-tts`; voice: `vi-VN-HoaiMyNeural` |
| `google` | Free fallback; uses `gTTS` |
| `elevenlabs` | Premium; requires `ELEVENLABS_API_KEY` |
| `local` | Custom model; requires `LOCAL_SERVER_URL` |

TTS results are cached in memory (configurable via `TTS_CACHE_MAX_SIZE`, default 500).

## Chrome Extension

### Loading the Extension

1. Open Chrome → `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked" → select the `chrome-extension/` folder

### Extension Architecture

- `content.js` — injected into all `youtube.com` pages; handles the full dubbing lifecycle:
  - Calls `POST http://localhost:8000/api/subtitles` to get translated segments
  - Pre-decodes all base64 audio to `Blob` URLs and creates `Audio` elements
  - Syncs audio playback to `video.currentTime` using `setTimeout` + a 500ms polling interval
  - Handles seek/pause/resume events to re-schedule audio
  - Mutes original video during dubbing
- `popup.js` / `popup.html` — toggle button UI; communicates with `content.js` via `chrome.runtime.sendMessage`
- `background.js` — service worker (Manifest V3)

Message types between popup and content script: `START_DUB`, `STOP_DUB`, `GET_STATUS`, `STATUS_UPDATE`.

The backend URL is hardcoded in `content.js:30` as `http://localhost:8000/api/subtitles`.
