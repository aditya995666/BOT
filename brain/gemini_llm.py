import os
import sys
import time
import json
import threading
from dotenv import load_dotenv

try:
    from system_prompt import SYSTEM_PROMPT
    print("✅ System prompt loaded from system_prompt.py")
except ImportError:
    print("⚠️ system_prompt.py not found, using default")
    SYSTEM_PROMPT = "You are JARVIS, a helpful AI assistant."

try:
    import streamlit as st
except ImportError:
    st = None

load_dotenv()


def _ai_model_choice() -> str:
    """Prefer Streamlit session when running inside Streamlit; else env or Groq default."""
    if st is not None:
        try:
            return st.session_state.get("ai_model", "groq")
        except Exception:
            pass
    return os.getenv("AI_MODEL", "groq")


def _safe_print(msg: str) -> None:
    try:
        sys.stdout.write(f"{msg}\n")
    except UnicodeEncodeError:
        enc = getattr(sys.stdout, "encoding", None) or "ascii"
        safe_msg = msg.encode(enc, errors="replace").decode(enc, errors="replace")
        sys.stdout.write(f"{safe_msg}\n")


class GeminiBrain:
    """GROQ BRAIN - Same interface as GeminiBrain - NO CODE CHANGES NEEDED IN OTHER FILES"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, model_name="llama-3.1-8b-instant"):
        if self._initialized:
            return
        
        _safe_print(f"\n{'='*50}")
        _safe_print("GROQ BRAIN INITIALIZING")
        _safe_print(f"{'='*50}")
        init_start = time.time()
        
        self.model_name = model_name
        self.max_retries = 3
        self.retry_delay = 2
        
        _safe_print(f"Model: {model_name}")
        _safe_print(f"Max Retries: {self.max_retries}")
        _safe_print(f"Free Tier: 14,400 requests/day")

        # Groq client
        try:
            _safe_print("Loading API key...")
            api_start = time.time()
            from groq import Groq
            self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            self.gemini_available = True
            api_elapsed = time.time() - api_start
            _safe_print(f"✅ Groq API loaded in {api_elapsed:.2f}s")
        except ImportError:
            self.groq_client = None
            self.gemini_available = False
            _safe_print("❌ Groq package not installed. Run: pip install groq")
        except Exception as e:
            self.groq_client = None
            self.gemini_available = False
            _safe_print(f"❌ Groq API key missing or invalid: {e}")
        
        init_elapsed = time.time() - init_start
        _safe_print(f"GroqBrain initialized in {init_elapsed:.2f}s")
        _safe_print(f"{'='*50}\n")
        
        self._initialized = True

    def _format_history(self, history):
        if not history:
            return []
        messages = []
        for msg in history:
            if isinstance(msg, dict):
                role = msg.get("role", "user")
                content = msg.get("content", "")
            else:
                role = "user" if len(messages) % 2 == 0 else "assistant"
                content = str(msg)
            messages.append({"role": role, "content": content})
        return messages

    def _ensure_json_response(self, answer, prompt):
        if "Respond ONLY in JSON" in prompt:
            try:
                cleaned = answer.strip()
                if "```json" in cleaned:
                    parts = cleaned.split("```json", 1)
                    if len(parts) > 1:
                        cleaned = parts[1].split("```", 1)[0].strip()
                elif "```" in cleaned:
                    parts = cleaned.split("```", 2)
                    if len(parts) > 1:
                        cleaned = parts[1].strip()
                
                if cleaned.startswith("{") and cleaned.endswith("}"):
                    json.loads(cleaned)
                    return cleaned
                
                raise ValueError("Not valid JSON")
            except:
                query_lower = prompt.lower()
                if any(greet in query_lower for greet in ["hello", "hi", "hey", "namaste"]):
                    fallback = {"unclear": False, "question": None}
                else:
                    fallback = {"unclear": True, "question": "Could you please clarify?"}
                return json.dumps(fallback)
        return answer

    def _call_groq(self, prompt, messages=None):
        """Groq API call with retry and detailed logs"""
        call_start = time.time()
        prompt_preview = prompt[:100].replace('\n', ' ')
        _safe_print(f"\n[GROQ API] Calling model: {self.model_name}")
        _safe_print(f"   Prompt preview: {prompt_preview}...")
        _safe_print(f"   Prompt length: {len(prompt)} chars")
        
        for attempt in range(self.max_retries):
            attempt_start = time.time()
            _safe_print(f"   Attempt {attempt + 1}/{self.max_retries}...")
            
            try:
                api_start = time.time()
                
                # Build messages
                if messages is None:
                    chat_messages = [{"role": "user", "content": prompt}]
                else:
                    chat_messages = messages + [{"role": "user", "content": prompt}]
                
                response = self.groq_client.chat.completions.create(
                    model=self.model_name,
                    messages=chat_messages,
                    temperature=0.7,
                    max_tokens=4096
                )
                api_elapsed = time.time() - api_start
                
                if response and response.choices:
                    response_text = response.choices[0].message.content.strip()
                    total_elapsed = time.time() - call_start
                    _safe_print(f"   API call succeeded in {api_elapsed:.2f}s")
                    _safe_print(f"   Response length: {len(response_text)} chars")
                    _safe_print(f"   Total time: {total_elapsed:.2f}s")
                    return response_text
                else:
                    _safe_print("   Empty response received")
                    return None
                    
            except Exception as e:
                error_str = str(e)
                attempt_elapsed = time.time() - attempt_start
                _safe_print(f"   Attempt {attempt + 1} failed in {attempt_elapsed:.2f}s")
                _safe_print(f"   Error: {error_str[:150]}")
                
                if attempt < self.max_retries - 1:
                    _safe_print(f"   Retrying in {self.retry_delay}s...")
                    time.sleep(self.retry_delay)
                else:
                    _safe_print(f"   All {self.max_retries} attempts failed")
                    return None
        
        _safe_print(f"[GROQ API] Failed after {self.max_retries} attempts")
        return None

    def _build_prompt_with_history(self, prompt, history):
        """Helper to build prompt with history"""
        safe_history = []
        if history:
            for msg in history:
                if isinstance(msg, dict):
                    safe_history.append(msg)
                else:
                    safe_history.append({"role": "user", "content": str(msg)})
        
        full_prompt = prompt
        if safe_history:
            history_lines = []
            for msg in safe_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                history_lines.append(f"{role}: {content}")
            full_prompt = "\n".join(history_lines) + "\n\n" + prompt
        
        if history:
            _safe_print(f"History included: {len(safe_history)} messages")
        
        return full_prompt, safe_history

    def think(self, prompt: str, history: list = None) -> str:
        """Main method to call Groq API - Same interface as Gemini"""
        think_start = time.time()
        _safe_print(f"\n{'='*50}")
        _safe_print("GROQ THINK STARTED")
        _safe_print(f"{'='*50}")
        
        if not self.gemini_available:
            _safe_print("Groq not available")
            if "Respond ONLY in JSON" in prompt:
                if any(greet in prompt.lower() for greet in ["hello", "hi", "hey"]):
                    return json.dumps({"unclear": False, "question": None})
                return json.dumps({"unclear": True, "question": "Groq API key issue"})
            return "⚠️ Groq API key missing. Add GROQ_API_KEY to .env file"
        
        # 🔥 CRITICAL: Add system prompt to EVERY request
        full_prompt_with_system = f"{SYSTEM_PROMPT}\n\nUser: {prompt}\n\nJARVIS:"
        
        full_prompt, safe_history = self._build_prompt_with_history(full_prompt_with_system, history)
        answer = self._call_groq(full_prompt, safe_history if safe_history else None)
        
        total_elapsed = time.time() - think_start
        
        if answer:
            _safe_print(f"GROQ THINK COMPLETED in {total_elapsed:.2f}s")
            _safe_print(f"{'='*50}\n")
            return self._ensure_json_response(answer, prompt)
        else:
            _safe_print(f"GROQ THINK FAILED in {total_elapsed:.2f}s")
            _safe_print(f"{'='*50}\n")
            if "Respond ONLY in JSON" in prompt:
                return json.dumps({"unclear": True, "question": "Groq API error"})
            return "⚠️ Groq API error. Please try again."

    def generate(self, prompt: str, history: list = None):
        return self.think(prompt, history)