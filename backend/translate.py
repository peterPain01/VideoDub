"""
translate.py - English to Vietnamese translation.

Uses deep-translator (Google Translate) for translation.
Compatible with modern httpx versions (no pinned dependency conflicts).
"""

from deep_translator import GoogleTranslator

# Initialize translator (reusable, thread-safe)
translator = GoogleTranslator(source="en", target="vi")


def translate_text(text: str) -> str:
    """
    Translate English text to Vietnamese.

    Args:
        text: English text to translate

    Returns:
        Vietnamese translated text
    """
    if not text or text.strip() == "":
        return ""

    try:
        translated = translator.translate(text)
        return translated or ""

    except Exception as e:
        print(f"[VideoDub Translate] Translation failed: {e}")
        # Return original text if translation fails
        return text
