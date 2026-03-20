"""
translate.py - English to Vietnamese translation using Google Translate (via deep-translator).

Optimisations:
  - In-memory cache: identical segments are never re-translated across requests.
  - Chunked parallel batches: uncached texts are split into chunks of CHUNK_SIZE
    and sent concurrently via asyncio.gather, avoiding one large sequential call.
  - Retry with exponential backoff: each chunk retries up to MAX_RETRIES times
    on failure before falling back to the original English text.
"""

import asyncio
import logging
import os
import time

from deep_translator import GoogleTranslator

# ── Config ────────────────────────────────────────────────────────────────────
CHUNK_SIZE = int(os.getenv("TRANSLATION_CHUNK_SIZE", 50))
MAX_RETRIES = 3
CACHE_MAX   = int(os.getenv("TRANSLATION_CACHE_MAX_SIZE", 5000))

# ── In-memory translation cache ───────────────────────────────────────────────
# key: stripped EN text  →  value: VI translation
_cache: dict[str, str] = {}


def _evict_if_full() -> None:
    """Drop oldest entries when cache exceeds CACHE_MAX."""
    if len(_cache) > CACHE_MAX:
        overflow = len(_cache) - CACHE_MAX
        for key in list(_cache.keys())[:overflow]:
            del _cache[key]


# ── Sync chunk translator (runs in thread pool) ───────────────────────────────

def _translate_chunk(texts: list[str]) -> list[str]:
    """
    Translate one chunk of texts via Google Translate with retry.
    Returns original texts if all retries are exhausted.
    """
    translator = GoogleTranslator(source="en", target="vi")
    delay = 1.0
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            results = translator.translate_batch(texts)
            return [(r if r else texts[i]) for i, r in enumerate(results)]
        except Exception as e:
            if attempt == MAX_RETRIES:
                logging.warning(
                    f"[Translate] Chunk failed after {MAX_RETRIES} retries: {e}"
                )
                return texts
            logging.warning(
                f"[Translate] Chunk attempt {attempt} failed ({e}), "
                f"retrying in {delay:.0f}s..."
            )
            time.sleep(delay)
            delay *= 2
    return texts  # unreachable but satisfies type checker


async def _translate_chunk_async(texts: list[str]) -> list[str]:
    return await asyncio.to_thread(_translate_chunk, texts)


# ── Public API ────────────────────────────────────────────────────────────────

async def translate_batch(texts: list[str]) -> list[str]:
    """
    Translate a list of English texts to Vietnamese.

    1. Texts already in cache are returned immediately.
    2. Remaining texts are split into chunks and translated in parallel.
    3. Results are merged back in original order and the cache is updated.
    """
    if not texts:
        return []

    cleaned = [t.strip() if t and t.strip() else "" for t in texts]

    # ── 1. Separate cached vs uncached ───────────────────────────────────────
    uncached_indices: list[int] = []
    uncached_texts: list[str]   = []

    for i, text in enumerate(cleaned):
        if text and text not in _cache:
            uncached_indices.append(i)
            uncached_texts.append(text)

    hits  = len(cleaned) - len(uncached_texts)
    total = len(cleaned)
    logging.info(f"[Translate] Cache hit: {hits}/{total}  Miss: {len(uncached_texts)}/{total}")

    # ── 2. Translate uncached texts in parallel chunks ────────────────────────
    if uncached_texts:
        chunks = [
            uncached_texts[i : i + CHUNK_SIZE]
            for i in range(0, len(uncached_texts), CHUNK_SIZE)
        ]
        chunk_results = await asyncio.gather(*[_translate_chunk_async(c) for c in chunks])

        # Flatten chunk results and write to cache
        translated_flat = [vi for chunk in chunk_results for vi in chunk]
        for text, vi in zip(uncached_texts, translated_flat):
            _cache[text] = vi
        _evict_if_full()

    # ── 3. Assemble final list in original order ──────────────────────────────
    return [
        _cache.get(text, text) if text else cleaned[i]
        for i, text in enumerate(cleaned)
    ]
