"""
main.py - FastAPI backend for VideoDub.

REST endpoint that fetches YouTube subtitles, translates EN→VI,
generates Vietnamese speech (TTS), and returns translated subtitle
segments with audio.
"""

import asyncio
import base64
import logging
import os
import time
import traceback
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

from subtitle import fetch_subtitles
from translate import translate_batch
from text_processor import log_transcript, merge_en_segments
from tts import text_to_speech, list_voices, get_provider_name


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = FastAPI(title="VideoDub Backend")

# Allow CORS for the Chrome extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Ensure CORS headers are present even on unhandled errors."""
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers={"Access-Control-Allow-Origin": "*"},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Ensure CORS headers are present on HTTP errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers={"Access-Control-Allow-Origin": "*"},
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
    t_start = time.perf_counter()
    print(f"[VideoDub] Subtitle request for video: {video_id}")

    # Step 1: Fetch English subtitles
    subtitles = await asyncio.to_thread(fetch_subtitles, video_id)

    if not subtitles:
        raise HTTPException(
            status_code=404,
            detail="No English subtitles found for this video. "
                   "This extension only works with videos that have English captions."
        )

    raw_segments = [s for s in subtitles if s.get("text", "").strip()]
    t1 = time.perf_counter()
    print(f"[Step 1] Fetch subtitles → {len(raw_segments)} segments  ({t1 - t_start:.2f}s)")

    # Step 2: Merge EN segments into natural sentences BEFORE translation
    #         (reduces translation API calls ~4x vs translating raw segments)
    merged_en = merge_en_segments(raw_segments)
    t2 = time.perf_counter()
    print(f"[Step 2] Merge EN → {len(raw_segments)} segments → {len(merged_en)} sentences  ({t2 - t1:.2f}s)")

    # Step 3: Translate merged EN sentences → VI
    en_texts = [s["text"] for s in merged_en]
    vi_texts = await translate_batch(en_texts)

    merged_segments = [
        {"text": vi, "en_text": en["text"], "start": en["start"], "duration": en["duration"]}
        for en, vi in zip(merged_en, vi_texts)
        if vi and vi.strip()
    ]

    for i, s in enumerate(merged_segments):
        end = s["start"] + s["duration"]
        logging.info(
            f"[Sentence {i+1:03d}] {s['start']:.2f}s – {end:.2f}s ({s['duration']:.2f}s)\n"
            f"  EN: {s['en_text']}\n"
            f"  VI: {s['text']}"
        )

    log_transcript(video_id, raw_segments, merged_segments)

    t3 = time.perf_counter()
    print(f"[Step 3] Translate → {len(merged_segments)}/{len(merged_en)} sentences  ({t3 - t2:.2f}s)")

    # Step 4: Generate TTS for all segments in parallel
    async def _tts_one(segment):
        try:
            mp3_bytes = await asyncio.to_thread(text_to_speech, segment["text"], voice_id)
            return segment, mp3_bytes
        except Exception as e:
            print(f"[VideoDub] TTS error for segment '{segment['text'][:40]}': {e}")
            return segment, None

    tts_results = await asyncio.gather(*[_tts_one(s) for s in merged_segments])

    results = []
    for segment, mp3_bytes in tts_results:
        if not mp3_bytes:
            continue
        audio_b64 = base64.b64encode(mp3_bytes).decode("utf-8")
        results.append({
            "start": segment["start"],
            "duration": segment["duration"],
            "originalText": segment["en_text"],
            "translatedText": segment["text"],
            "audioBase64": audio_b64,
        })

    t4 = time.perf_counter()
    print(f"[Step 4] TTS → {len(results)}/{len(merged_segments)} segments  ({t4 - t3:.2f}s)")
    print(f"[Total]  {t4 - t_start:.2f}s  (provider: {get_provider_name()})")

    return {
        "videoId": video_id,
        "totalSegments": len(results),
        "provider": get_provider_name(),
        "segments": results,
    }


if __name__ == "__main__":
    print("[VideoDub] Starting backend server on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
