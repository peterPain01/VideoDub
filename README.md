# 🎙 VideoDub - YouTube EN→VI Subtitle Translation

Chrome Extension + Python backend that translates English YouTube subtitles into Vietnamese voice, synced to the video timeline.

## Architecture

```
┌─────────────────────────────────────┐
│  Chrome Extension (content.js)       │
│  1. Extract video ID from URL        │
│  2. Request subtitles from backend   │
│  3. Schedule TTS playback synced     │
│     to video timeline                │
└──────────┬──────────────────────────┘
           │ HTTP POST /api/subtitles
           │ Send: { videoId }
           │ Receive: translated segments + MP3 audio
┌──────────▼──────────────────────────┐
│  FastAPI Backend (main.py)           │
│  1. Fetch EN subtitles (youtube-     │
│     transcript-api)                  │
│  2. Translate EN→VI (googletrans)    │
│  3. Generate Vietnamese TTS (gTTS)   │
│  4. Return segments with MP3 audio   │
└──────────────────────────────────────┘
```

## Prerequisites

- **Python 3.10+** with pip
- **Google Chrome** browser

## Setup & Run

### 1. Backend

```bash
cd backend

# Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run the server
python main.py
```

The server starts at `http://localhost:8000`.

### 2. Chrome Extension

1. Open Chrome and go to `chrome://extensions/`
2. Enable **Developer mode** (toggle in top-right)
3. Click **Load unpacked**
4. Select the `chrome-extension/` folder

### 3. Test on YouTube

1. Open any English YouTube video **that has English subtitles/CC**
2. Click the **VideoDub** extension icon in the Chrome toolbar
3. Click **▶ Start Translation**
4. Wait for subtitles to be fetched and translated (loading spinner shown)
5. The original audio will be muted and Vietnamese audio will play synced to the video

## How It Works

1. **Video ID Extraction**: Content script reads the YouTube video ID from the URL
2. **Subtitle Fetch**: Backend uses `youtube-transcript-api` to fetch English subtitles with timestamps
3. **Translation**: Each subtitle segment is translated English → Vietnamese via Google Translate
4. **TTS**: gTTS generates Vietnamese speech (MP3) for each translated segment
5. **Sync Playback**: Extension schedules each MP3 segment to play at the correct timestamp, handling seek/pause/resume

## Project Structure

```
VideoDub/
├── chrome-extension/
│   ├── manifest.json      # Manifest V3 config
│   ├── content.js         # Subtitle-driven TTS playback
│   ├── background.js      # Service worker
│   ├── popup.html         # Toggle UI with loading states
│   └── popup.js           # Popup logic with state management
├── backend/
│   ├── main.py            # FastAPI REST server
│   ├── subtitle.py        # YouTube subtitle fetcher
│   ├── translate.py       # EN→VI translation
│   ├── tts.py             # Vietnamese TTS (gTTS)
│   └── requirements.txt   # Python dependencies
└── README.md
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No English subtitles found" | Video must have English CC (manual or auto-generated) |
| Extension not working | Reload YouTube page after loading extension |
| Loading takes too long | Long videos have many segments to translate; wait for completion |
| WebSocket connection failed | Ensure backend is running on `localhost:8000` |
| No translation output | Check backend terminal for error messages |

## Limitations

- Only works with videos that have English subtitles/captions
- Initial loading time depends on video length (translating all segments)
- Requires internet for translation (googletrans) and TTS (gTTS)
- TTS voice quality is limited by gTTS
