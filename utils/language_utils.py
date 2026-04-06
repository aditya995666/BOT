import re

def detect_language(text: str) -> str:
    """
    Returns: 'hi', 'en', or 'hinglish'
    """
    # Hindi unicode range
    if re.search(r'[\u0900-\u097F]', text):
        return "hi"

    # Hinglish (English letters but Hindi words)
    hinglish_words = [
        "kya", "kaise", "kyu", "hai", "nahi", "batao", "samjhao"
    ]
    if any(w in text.lower() for w in hinglish_words):
        return "hinglish"

    return "en"
