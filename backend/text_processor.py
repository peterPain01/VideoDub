"""
text_processor.py - Segment merging and transcript logging for VideoDub.
"""

import os
from datetime import datetime

MAX_MERGE_DURATION = 8.0  # seconds


def merge_segments(segments: list[dict]) -> list[dict]:
    """
    Merge consecutive short subtitle segments into natural sentences.

    Rules:
    - Accumulate segments until adding the next would exceed MAX_MERGE_DURATION.
    - Always flush when the current text ends with sentence-ending punctuation.
    - Merged segment: start = first segment's start, duration = span to last segment's end.

    Args:
        segments: List of dicts with keys: text, en_text, start, duration.

    Returns:
        New list of merged segments with the same keys.
    """
    if not segments:
        return []

    _SENTENCE_END = {".", "!", "?", "…"}
    _SOFT_PAUSE = {",", ";", ":"}

    merged = []
    bucket = []

    def flush():
        if not bucket:
            return
        start = bucket[0]["start"]
        end = bucket[-1]["start"] + bucket[-1]["duration"]
        merged.append({
            "text": " ".join(s["text"] for s in bucket),
            "en_text": " ".join(s["en_text"] for s in bucket),
            "start": start,
            "duration": round(end - start, 3),
        })
        bucket.clear()

    for seg in segments:
        bucket.append(seg)
        stripped = seg["text"].rstrip()
        last_char = stripped[-1] if stripped else ""

        if last_char in _SENTENCE_END:
            # Always flush at a real sentence boundary
            flush()
        elif last_char in _SOFT_PAUSE:
            # Flush at soft pause only when already over the duration limit
            span = (bucket[-1]["start"] + bucket[-1]["duration"]) - bucket[0]["start"]
            if span >= MAX_MERGE_DURATION:
                flush()

    flush()
    return merged


def log_transcript(
    video_id: str,
    raw_segments: list[dict],
    translated_segments: list[dict],
) -> str:
    """
    Write a human-readable transcript log (raw EN → translated VI).

    File: logs/transcript_{videoId}_{YYYYMMDD_HHMMSS}.txt

    Returns the log file path.
    """
    logs_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(logs_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(logs_dir, f"transcript_{video_id}_{timestamp}.txt")

    lines = [
        "=" * 72,
        f"  VideoDub Transcript Log",
        f"  Video   : {video_id}",
        f"  Date    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"  Raw segs: {len(raw_segments)}  →  Translated: {len(translated_segments)}",
        "=" * 72,
        "",
    ]

    lines.append("─" * 72)
    lines.append(f"  RAW ENGLISH  ({len(raw_segments)} segments)")
    lines.append("─" * 72)
    for i, seg in enumerate(raw_segments):
        end = seg["start"] + seg["duration"]
        lines.append(f"[{i:03d}] {seg['start']:7.2f}s – {end:7.2f}s  ({seg['duration']:.2f}s)")
        lines.append(f"       {seg['text']!r}")
    lines.append("")

    lines.append("─" * 72)
    lines.append(f"  TRANSLATED VIETNAMESE  ({len(translated_segments)} segments)")
    lines.append("─" * 72)
    for i, seg in enumerate(translated_segments):
        end = seg["start"] + seg["duration"]
        lines.append(f"[{i:03d}] {seg['start']:7.2f}s – {end:7.2f}s  ({seg['duration']:.2f}s)")
        lines.append(f"       EN: {seg.get('en_text', '')!r}")
        lines.append(f"       VI: {seg['text']!r}")
    lines.append("")
    lines.append("=" * 72)

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"[TextProcessor] Transcript log → {path}")
    return path
