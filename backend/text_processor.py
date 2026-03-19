"""
text_processor.py - Merge short subtitle segments into natural sentences.

YouTube subtitles are often broken into very short fragments like:
  "Hello" → "how are" → "you today"

This module merges them into complete sentences before TTS:
  "Hello, how are you today."

This produces much more natural-sounding speech.
"""

import re


def merge_subtitle_segments(segments: list[dict], max_duration: float = 8.0) -> list[dict]:
    """
    Merge short subtitle segments into longer, natural sentences.

    Segments are merged when:
    - Current segment doesn't end with sentence-ending punctuation (.!?)
    - Merged duration doesn't exceed max_duration
    - Gap between segments is small (< 2 seconds)

    Args:
        segments: List of {"text": "...", "start": float, "duration": float}
        max_duration: Maximum duration for a merged segment (seconds)

    Returns:
        List of merged segments with same structure
    """
    if not segments:
        return []

    merged = []
    current = None

    for seg in segments:
        text = seg["text"].strip()
        if not text:
            continue

        if current is None:
            # Start a new group
            current = {
                "text": text,
                "start": seg["start"],
                "duration": seg["duration"],
                "original_texts": [text],
            }
            continue

        # Check if we should merge with current group
        current_end = current["start"] + current["duration"]
        gap = seg["start"] - current_end
        merged_duration = (seg["start"] + seg["duration"]) - current["start"]

        should_merge = (
            not _ends_with_sentence_punctuation(current["text"])
            and gap < 2.0
            and merged_duration <= max_duration
        )

        if should_merge:
            # Merge: append text, extend duration
            current["text"] = _join_texts(current["text"], text)
            current["duration"] = (seg["start"] + seg["duration"]) - current["start"]
            current["original_texts"].append(text)
        else:
            # Finalize current group and start new one
            current["text"] = _normalize_text(current["text"])
            merged.append(current)
            current = {
                "text": text,
                "start": seg["start"],
                "duration": seg["duration"],
                "original_texts": [text],
            }

    # Don't forget the last group
    if current:
        current["text"] = _normalize_text(current["text"])
        merged.append(current)

    print(f"[TextProcessor] Merged {len(segments)} segments → {len(merged)} sentences")
    return merged


def _ends_with_sentence_punctuation(text: str) -> bool:
    """Check if text ends with sentence-ending punctuation."""
    text = text.rstrip()
    return bool(text) and text[-1] in ".!?…"


def _join_texts(a: str, b: str) -> str:
    """Join two text fragments naturally."""
    a = a.rstrip()
    b = b.strip()

    # If a ends with punctuation that's not sentence-ending, just space-join
    if a and a[-1] in ",-;:":
        return f"{a} {b}"

    # Otherwise, space-join
    return f"{a} {b}"


def _normalize_text(text: str) -> str:
    """
    Normalize text for TTS:
    - Add period if no sentence-ending punctuation
    - Capitalize first letter
    - Clean up whitespace
    """
    text = text.strip()
    if not text:
        return text

    # Clean up multiple spaces
    text = re.sub(r'\s+', ' ', text)

    # Remove artifacts like [Music], [Applause], etc.
    text = re.sub(r'\[.*?\]', '', text).strip()
    if not text:
        return text

    # Capitalize first letter
    text = text[0].upper() + text[1:] if len(text) > 1 else text.upper()

    # Add period if missing sentence-ending punctuation
    if not _ends_with_sentence_punctuation(text):
        text += "."

    return text
