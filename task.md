# VideoDub: Switch from Audio Capture to YouTube Subtitle-Based Translation

## Tasks

- [/] Plan the architecture change
  - [x] Read existing codebase
  - [x] Research `youtube-transcript-api` library
  - [/] Write implementation plan
  - [ ] Get user approval
- [ ] Implement backend changes
  - [ ] Add `youtube-transcript-api` to [requirements.txt](file:///c:/Learning/VideoDub/backend/requirements.txt)
  - [ ] Create `subtitle.py` — fetch YouTube subtitles with timestamps
  - [ ] Replace WebSocket pipeline in [main.py](file:///c:/Learning/VideoDub/backend/main.py) with REST endpoint for subtitle fetch + translate
  - [ ] Keep [tts.py](file:///c:/Learning/VideoDub/backend/tts.py) and [translate.py](file:///c:/Learning/VideoDub/backend/translate.py) (still needed)
  - [ ] Remove [stt.py](file:///c:/Learning/VideoDub/backend/stt.py) (no longer needed)
  - [ ] Remove `faster-whisper` from [requirements.txt](file:///c:/Learning/VideoDub/backend/requirements.txt)
- [ ] Implement Chrome extension changes
  - [ ] Rewrite [content.js](file:///c:/Learning/VideoDub/chrome-extension/content.js) — remove Web Audio capture, add subtitle-driven TTS playback
  - [ ] Update [popup.js](file:///c:/Learning/VideoDub/chrome-extension/popup.js) / [popup.html](file:///c:/Learning/VideoDub/chrome-extension/popup.html) if needed
  - [ ] Update [manifest.json](file:///c:/Learning/VideoDub/chrome-extension/manifest.json) if needed
- [ ] Update [README.md](file:///c:/Learning/VideoDub/README.md)
- [ ] Verify end-to-end
