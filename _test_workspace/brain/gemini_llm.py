import os
import requests
from dotenv import load_dotenv
from google import genai
import streamlit as st
import time
import json
# brain/gemini_llm.py - ये file होनी चाहिए:
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

class GeminiBrain:

    def __init__(self, model_name="gemini-2.5-flash"):
        self.model_name = model_name
        self.ollama_chat = "http://localhost:11434/api/chat"          # ← Best for chat/history
        self.ollama_generate = "http://localhost:11434/api/generate"  # Backup
        self.ollama_models = "http://localhost:11434/api/tags"

        # Gemini client (quota ke liye optional)
        try:
            self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        except:
            self.client = None
            print("Gemini API key nahi mila ya quota issue")

    def get_ollama_models(self):
        try:
            r = requests.get(self.ollama_models, timeout=10)
            if r.status_code == 200:
                return [m["name"] for m in r.json()["models"]]
            return []
        except Exception as e:
            print(f"Ollama tags fail: {e}")
            return []

    def _format_history(self, history):
        """🔥 FIXED: Handle both string and dict messages in history"""
        if not history:
            return []
        messages = []
        for msg in history:
            if isinstance(msg, dict):
                # Dictionary message
                role = msg.get("role", "user")
                content = msg.get("content", "")
            else:
                # String message - convert to proper format
                role = "user" if len(messages) % 2 == 0 else "assistant"
                content = str(msg)
            messages.append({"role": role, "content": content})
        return messages

    def _ensure_json_response(self, answer, prompt):
        """FIX: Force JSON response for clarification queries"""
        # Agar prompt mein "Respond ONLY in JSON" hai
        if "Respond ONLY in JSON" in prompt:
            try:
                # Pehle check karo ki answer already JSON hai ya nahi
                # Extra text hatao jo JSON ke around ho sakta hai
                cleaned = answer.strip()
                
                # Agar ```json ya ``` ke andar hai to nikaalo
                if "```json" in cleaned:
                    parts = cleaned.split("```json", 1)
                    if len(parts) > 1:
                        cleaned = parts[1].split("```", 1)[0].strip()
                elif "```" in cleaned:
                    parts = cleaned.split("```", 2)
                    if len(parts) > 1:
                        cleaned = parts[1].strip()
                
                # Check if it starts with { and ends with }
                if cleaned.startswith("{") and cleaned.endswith("}"):
                    json.loads(cleaned)  # Validate
                    return cleaned
                
                # Agar valid JSON nahi hai to fallback banao
                raise ValueError("Not valid JSON")
                
            except:
                # Fallback JSON based on query
                print("⚠️ Creating fallback JSON for clarification")
                
                # Greeting detection
                query_lower = prompt.lower()
                if any(greet in query_lower for greet in ["hello", "hi", "hey", "namaste", "khaa ho"]):
                    fallback = {"unclear": False, "question": None}
                else:
                    # Default unclear with question
                    fallback = {"unclear": True, "question": "Could you please clarify what you need help with?"}
                
                return json.dumps(fallback)
        
        # Normal response - no JSON forcing
        return answer

    def think(self, prompt: str, history: list = None) -> str:
        model_choice = st.session_state.get("ai_model", "gemini")

        # 🔥 FIX: Handle history safely - convert any non-dict items to strings first
        safe_history = []
        if history:
            for msg in history:
                if isinstance(msg, dict):
                    safe_history.append(msg)
                else:
                    # Convert string to dict format
                    safe_history.append({"role": "user", "content": str(msg)})
        
        # Build prompt with safe history
        full_prompt = prompt
        if safe_history:
            history_lines = []
            for msg in safe_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                history_lines.append(f"{role}: {content}")
            full_prompt = "\n".join(history_lines) + "\n\n" + prompt

        if model_choice == "gemini":
            print("🔥 GEMINI CALLED")
            if not self.client:
                # Return fallback JSON if clarification query
                if "Respond ONLY in JSON" in prompt:
                    if any(greet in prompt.lower() for greet in ["hello", "hi", "hey"]):
                        return json.dumps({"unclear": False, "question": None})
                    return json.dumps({"unclear": True, "question": "Gemini API key issue - please clarify"})
                return "Gemini client load nahi hua (API key check karo)"

            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=full_prompt
                )
                if hasattr(response, "text") and response.text:
                    answer = response.text.strip()
                    # Ensure JSON for clarification queries
                    return self._ensure_json_response(answer, prompt)
                return "Gemini ne empty response diya"
            except Exception as e:
                print("Gemini Error:", e)
                # Return fallback JSON if clarification query
                if "Respond ONLY in JSON" in prompt:
                    return json.dumps({"unclear": True, "question": f"Gemini error: {str(e)}"})
                return f"⚠ Gemini error: {str(e)}"

        if model_choice == "ollama":
            print("🧠 OLLAMA CALLED")

            models = self.get_ollama_models()
            if not models:
                # Return fallback JSON if clarification query
                if "Respond ONLY in JSON" in prompt:
                    return json.dumps({"unclear": True, "question": "Ollama server not running"})
                return "❌ Ollama server nahi chal raha. 'ollama serve' chala ke dekho"

            ollama_model = st.session_state.get("ollama_model")
            if not ollama_model or ollama_model not in models:
                # Prefer loaded models from your list
                preferred = [m for m in models if any(x in m for x in ["tinyllama", "deepseek-coder", "phi3"])]
                ollama_model = preferred[0] if preferred else models[0]
                print(f"Auto-selected: {ollama_model}")

            # Use /api/chat (best for your models)
            payload = {
                "model": ollama_model,
                "messages": self._format_history(safe_history) + [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_ctx": 2048  # TinyLlama ke liye safe
                }
            }

            print(f"→ Using model: {ollama_model} | Prompt len: {len(prompt)}")

            try:
                start = time.time()
                response = requests.post(
                    self.ollama_chat,
                    json=payload,
                    timeout=300  # 5 minutes safe for first load
                )

                print(f"→ Time: {time.time() - start:.1f}s | Status: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    answer = data.get("message", {}).get("content", "").strip()
                    if answer:
                        print(f"→ Answer preview: {answer[:100]}...")
                        # Ensure JSON for clarification queries
                        return self._ensure_json_response(answer, prompt)
                    
                    # Empty answer - return fallback for clarification
                    if "Respond ONLY in JSON" in prompt:
                        return json.dumps({"unclear": True, "question": "Model returned empty response"})
                    return "Ollama ne reply diya lekin content khali tha"

                else:
                    error_msg = f"Ollama error {response.status_code}: {response.text[:200]}"
                    if "Respond ONLY in JSON" in prompt:
                        return json.dumps({"unclear": True, "question": error_msg})
                    return error_msg

            except requests.exceptions.Timeout:
                timeout_msg = "❌ Timeout (5 min). Model warm-up ho raha, thoda wait karo."
                if "Respond ONLY in JSON" in prompt:
                    return json.dumps({"unclear": True, "question": "Request timeout"})
                return timeout_msg
            except Exception as e:
                print(f"Ollama Exception: {e}")
                if "Respond ONLY in JSON" in prompt:
                    return json.dumps({"unclear": True, "question": f"Ollama failed: {str(e)}"})
                return f"❌ Ollama failed: {str(e)}"

        # Default return for no model selected
        if "Respond ONLY in JSON" in prompt:
            return json.dumps({"unclear": True, "question": "No model selected"})
        return "⚠ Model select karo (Gemini ya Ollama)"

    def generate(self, prompt: str, history: list = None):
        return self.think(prompt, history)
    def __init__(self, model_name="gemini-2.5-flash"):
        self.client = genai.Client(
            api_key=os.getenv("GEMINI_API_KEY")
        )
        self.model_name = model_name

    def think(self, prompt: str, history: list = None) -> str:
        # Format history properly
        formatted_history = ""
        if history:
            if isinstance(history, list):
                formatted_history = "\n".join(history)
            else:
                formatted_history = str(history)
        
        full_prompt = formatted_history + "\n\n" + prompt if formatted_history else prompt
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=full_prompt
            )
            return response.text
        except Exception as e:
            return f"Error: {str(e)}"
