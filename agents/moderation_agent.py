import re
from agents.master_agent import master_agent  # Direct import

# API patterns - sirf ye detect karna hai
API_PATTERNS = [
    r"sk-[a-zA-Z0-9]{20,}",  # OpenAI keys
    r"api[_-]?key\s*[=:]\s*['\"]?[A-Za-z0-9-_]{20,}['\"]?",  # API keys
    r"token\s*[=:]\s*['\"]?[A-Za-z0-9-_]{20,}['\"]?",  # Tokens
    r"Bearer\s+[A-Za-z0-9\._\-]{20,}",  # Bearer tokens
    r"AIza[A-Za-z0-9\-_]{35}",  # Google API keys
    r"gh[pousr]_[A-Za-z0-9]{36}",  # GitHub tokens
]

def moderate_content(text: str):
    """Moderate content - ONLY block API keys, everything else ALLOW"""
    
    if not text or not isinstance(text, str):
        return {"verdict": "SAFE", "action": "ALLOW"}

    text = str(text)
    
    # 🔍 Check for API keys only
    for pattern in API_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            # Found API key - ask Master Agent
            print(f"🚨 API Key Detected: {matches[0][:20]}... → Sending to Master Agent")
            
            decision = master_agent.review_api_key(text, matches[0])
            
            if decision["action"] == "BAN":
                return {
                    "verdict": "BLOCKED",
                    "action": "BAN",
                    "reason": decision["reason"]
                }
            else:
                return {
                    "verdict": "SAFE",
                    "action": "ALLOW",
                    "reason": decision["reason"]
                }
    
    # ✅ No API key - ALWAYS ALLOW
    return {
        "verdict": "SAFE",
        "action": "ALLOW",
        "reason": "No sensitive content detected"
    }
# agents/moderation_agent.py
import re

# 🔴 Porn / Adult keywords (expandable)
PORN_KEYWORDS = [
    "porn", "sex", "xxx", "xnxx", "xvideos", "onlyfans",
    "nude", "nudity", "blowjob", "handjob", "anal",
    "pussy", "penis", "dick", "cock", "boobs",
    "orgasm", "cum", "moaning", "erotic",
    "adult video", "sex video", "porn video"
]

def normalize(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = text.replace("0", "o").replace("1", "i").replace("3", "e")
    text = re.sub(r"[^a-z ]", "", text)
    return text

def moderate_content(text: str):
    text = normalize(text)

    for kw in PORN_KEYWORDS:
        if kw in text:
            return {
                "verdict": "EXPLICIT",
                "action": "BAN"
            }

    return {
        "verdict": "SAFE",
        "action": "ALLOW"
    }
