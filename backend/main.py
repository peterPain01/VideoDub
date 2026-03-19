"""
main.py - FastAPI backend for VideoDub.

REST endpoint that fetches YouTube subtitles, translates EN→VI,
generates Vietnamese speech (TTS), and returns translated subtitle
segments with audio.
"""

import asyncio
import base64
import traceback
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from subtitle import fetch_subtitles
from translate import translate_text
from text_processor import merge_subtitle_segments
from tts import text_to_speech, list_voices, get_provider_name

app = FastAPI(title="VideoDub Backend")

# Allow CORS for the Chrome extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SubtitleRequest(BaseModel):
    videoId: str
    voiceId: str | None = None


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "VideoDub Backend",
        "ttsProvider": get_provider_name(),
    }


@app.get("/api/voices")
async def get_voices():
    """List available TTS voices."""
    voices = list_voices()
    return {
        "provider": get_provider_name(),
        "voices": voices,
    }


@app.post("/api/subtitles")
async def get_translated_subtitles(request: SubtitleRequest):
    """
    Fetch YouTube subtitles, translate to Vietnamese, and generate TTS.

    Flow:
    1. Fetch English subtitles from YouTube
    2. Translate each segment to Vietnamese
    3. Merge short segments into natural sentences
    4. Generate Vietnamese TTS audio for each merged segment
    5. Return list of translated segments with base64 MP3 audio
    """
    video_id = request.videoId
    voice_id = request.voiceId
    print(f"[VideoDub] Subtitle request for video: {video_id}")

    # Step 1: Fetch English subtitles
    subtitles = await asyncio.to_thread(fetch_subtitles, video_id)

    if not subtitles:
        raise HTTPException(
            status_code=404,
            detail="No English subtitles found for this video. "
                   "This extension only works with videos that have English captions."
        )

    print(f"[VideoDub] Fetched {len(subtitles)} raw subtitle segments")

    # Step 2: Translate each segment
    translated_segments = []
    for seg in subtitles:
        original_text = seg["text"]
        if not original_text or not original_text.strip():
            continue

        translated_text = translate_text(original_text)
        if not translated_text or not translated_text.strip():
            continue

        translated_segments.append({
            "text": translated_text,
            "start": seg["start"],
            "duration": seg["duration"],
            "originalText": original_text,
        })

    print(f"[VideoDub] Translated {len(translated_segments)} segments")

    # Step 3: Merge short segments into natural sentences
    merged = merge_subtitle_segments(translated_segments)

    # Step 4: Generate TTS for each merged segment
    results = []
    for i, segment in enumerate(merged):
        try:
            text = segment["text"]

            # Generate TTS audio (caching handled inside engine)
            mp3_bytes = text_to_speech(text, voice_id)

            if not mp3_bytes:
                continue

            audio_b64 = base64.b64encode(mp3_bytes).decode("utf-8")

            results.append({
                "start": segment["start"],
                "duration": segment["duration"],
                "originalText": " | ".join(segment.get("original_texts", [text])),
                "translatedText": text,
                "audioBase64": audio_b64,
            })

            if (i + 1) % 20 == 0:
                print(f"[VideoDub] Generated TTS for {i + 1}/{len(merged)} segments...")

        except Exception as e:
            print(f"[VideoDub] Error processing segment {i}: {e}")
            traceback.print_exc()
            continue

    print(f"[VideoDub] Done! Returning {len(results)} translated segments "
          f"(provider: {get_provider_name()})")

    return {
        "videoId": video_id,
        "totalSegments": len(results),
        "provider": get_provider_name(),
        "segments": results,
    }


if __name__ == "__main__":
    print("[VideoDub] Starting backend server on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
