"""
subtitle.py - Fetch YouTube subtitles/captions.

Uses youtube-transcript-api to fetch English subtitles (manual or auto-generated)
for a given YouTube video ID.
"""

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter


def fetch_subtitles(video_id: str) -> list[dict]:
    """
    Fetch English subtitles for a YouTube video.

    Tries manually created English subs first, then falls back to
    auto-generated English subs.

    Args:
        video_id: YouTube video ID (e.g., 'dQw4w9WgXcQ')

    Returns:
        List of subtitle segments: [{"text": "...", "start": 0.5, "duration": 2.1}, ...]
        Returns empty list if no English subtitles are available.
    """
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id, languages=['en'])

        segments = []
        for snippet in transcript:
            segments.append({
                "text": snippet.text,
                "start": snippet.start,
                "duration": snippet.duration,
            })

        print(f"[VideoDub Subtitle] Fetched {len(segments)} subtitle segments for video {video_id}")
        return segments

    except Exception as e:
        print(f"[VideoDub Subtitle] Error fetching subtitles for {video_id}: {e}")
        return []
