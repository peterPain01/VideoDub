# Switch VideoDub from Audio Capture to YouTube Subtitle-Based Translation

The current architecture captures audio via Web Audio API → sends WAV to backend → Whisper STT → translate → TTS. This often produces empty transcriptions (as seen in logs). The new approach fetches YouTube's existing subtitles (English captions) directly, translates them, and plays Vietnamese TTS synced to the video timeline.

> [!IMPORTANT]
> Videos **without English subtitles/captions** (manual or auto-generated) will not work. The user has accepted this limitation.

## New Architecture

```
┌─────────────────────────────────────┐
│  Chrome Extension (content.js)       │
│  1. Extract video ID from URL        │
│  2. Request subtitles from backend   │
│  3. Schedule TTS playback by         │
│     subtitle timestamps              │
│  4. Mute original audio, play TTS    │
└──────────┬──────────────────────────┘
           │ HTTP (POST /api/subtitles)
           │ Send: { videoId }
           │ Receive: [ {start, duration, viText, mp3Base64} ]
┌──────────▼──────────────────────────┐
│  FastAPI Backend (main.py)           │
│  1. Fetch EN subtitles (youtube-     │
│     transcript-api)                  │
│  2. Translate each segment EN→VI     │
│  3. Generate TTS for each segment    │
│  4. Return translated subtitle list  │
│     with MP3 audio                   │
└──────────────────────────────────────┘
```

## Proposed Changes

### Backend

---

#### [MODIFY] [requirements.txt](file:///c:/Learning/VideoDub/backend/requirements.txt)
- Remove `faster-whisper==1.1.0` (no longer needed — saves ~75MB model download + FFmpeg requirement)
- Add `youtube-transcript-api` for fetching YouTube subtitles

---

#### [NEW] [subtitle.py](file:///c:/Learning/VideoDub/backend/subtitle.py)
- Fetch English subtitles for a YouTube video ID using `youtube-transcript-api`
- Returns list of `{text, start, duration}` segments
- Try manually created English subs first, fall back to auto-generated

---

#### [MODIFY] [main.py](file:///c:/Learning/VideoDub/backend/main.py)
- Remove WebSocket `/ws` endpoint
- Add new REST endpoint: `POST /api/subtitles`
  - Request body: `{ "videoId": "dQw4w9WgXcQ" }`
  - Pipeline: fetch subtitles → translate each segment → generate TTS for each → return JSON array
  - Response: `[ { "start": 0.5, "duration": 2.1, "originalText": "...", "translatedText": "...", "audioBase64": "..." } ]`
- Keep health check `GET /`

---

#### [KEEP] [translate.py](file:///c:/Learning/VideoDub/backend/translate.py) — no changes needed.

#### [KEEP] [tts.py](file:///c:/Learning/VideoDub/backend/tts.py) — no changes needed.

#### [DELETE] [stt.py](file:///c:/Learning/VideoDub/backend/stt.py) — Whisper STT no longer needed.

---

### Chrome Extension

---

#### [MODIFY] [content.js](file:///c:/Learning/VideoDub/chrome-extension/content.js)
Complete rewrite — remove all Web Audio / WebSocket code. New logic:
1. Extract video ID from `window.location`
2. On `START_DUB`:
   - **Pause the YouTube video** immediately so it doesn't play ahead while backend processes
   - Record the current `videoElement.currentTime` as the resume point
   - Call backend `POST /api/subtitles` with video ID
3. Receive translated subtitle segments with TTS audio (base64)
4. Mute original video
5. **Resume the YouTube video** from the saved position once all audio segments are preloaded
6. Schedule each TTS audio segment to play at the correct `start` time relative to video `currentTime`
7. Handle video seek/pause/resume by re-scheduling audio playback
8. On `STOP_DUB`: cancel all scheduled items, unmute video, resume if paused

---

#### [MODIFY] [popup.html](file:///c:/Learning/VideoDub/chrome-extension/popup.html)
- Add a loading indicator for when subtitles are being fetched/translated
- Show "No subtitles" error if backend returns empty

---

#### [MODIFY] [popup.js](file:///c:/Learning/VideoDub/chrome-extension/popup.js)
- Minor updates to handle new loading/error states from content script

---

#### [MODIFY] [manifest.json](file:///c:/Learning/VideoDub/chrome-extension/manifest.json)
- No changes needed (already has correct permissions)

---

#### [KEEP] [background.js](file:///c:/Learning/VideoDub/chrome-extension/background.js) — no changes needed.

---

### Documentation

#### [MODIFY] [README.md](file:///c:/Learning/VideoDub/README.md)
- Update architecture diagram
- Remove FFmpeg prerequisite
- Note that videos without subtitles won't work

## Verification Plan

### Manual Verification
1. Start backend: `cd backend && venv\Scripts\activate && python main.py`
2. Test subtitle fetch directly: `curl -X POST http://localhost:8000/api/subtitles -H "Content-Type: application/json" -d "{\"videoId\": \"dQw4w9WgXcQ\"}"`
3. Load extension in Chrome, open a YouTube video with English subtitles
4. Click Start Translation — verify loading state shows, then Vietnamese audio plays synced to video
5. Test seek, pause, resume
6. Test on a video without subtitles — verify error message appears
