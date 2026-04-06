import os
import requests
from dotenv import load_dotenv
from google import genai
import streamlit as st
import time
import json
import anthropic

load_dotenv()

class GeminiBrain:

    def __init__(self, model_name="gemini-2.5-flash"):
        self.model_name = model_name

        # Gemini client
        try:
            self.gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
            self.gemini_available = True
            print("✅ Gemini API loaded")
        except:
            self.gemini_client = None
            self.gemini_available = False
            print("⚠️ Gemini API key missing")

        # Claude client
        try:
            self.claude_client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
            self.claude_available = True
            print("✅ Claude AI loaded")
        except:
            self.claude_client = None
            self.claude_available = False
            print("⚠️ Claude API key missing")

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

    def _call_claude(self, prompt, history=None):
        """Claude API call"""
        try:
            messages = []
            if history:
                for msg in history:
                    if isinstance(msg, dict):
                        role = "user" if msg.get("role") == "user" else "assistant"
                        messages.append({"role": role, "content": msg.get("content", "")})
            
            messages.append({"role": "user", "content": prompt})
            
            response = self.claude_client.messages.create(
                model="claude-3-sonnet-20241029",
                max_tokens=4096,
                messages=messages
            )
            return response.content[0].text
        except Exception as e:
            print(f"Claude Error: {e}")
            return None

    def _call_gemini(self, prompt):
        """Gemini API call"""
        try:
            response = self.gemini_client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            if hasattr(response, "text") and response.text:
                return response.text.strip()
            return None
        except Exception as e:
            print(f"Gemini Error: {e}")
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
        return full_prompt

    def think(self, prompt: str, history: list = None) -> str:
        # Model choice from session state
        model_choice = st.session_state.get("ai_model", "gemini")
        
        # For Claude
        if model_choice == "claude":
            print("🤖 CLAUDE CALLED")
            if not self.claude_available:
                if "Respond ONLY in JSON" in prompt:
                    return json.dumps({"unclear": True, "question": "Claude API key missing"})
                return "⚠️ Claude API key not configured. Add CLAUDE_API_KEY to .env file"
            
            full_prompt = self._build_prompt_with_history(prompt, history)
            answer = self._call_claude(full_prompt, history)
            
            if answer:
                return self._ensure_json_response(answer, prompt)
            else:
                if "Respond ONLY in JSON" in prompt:
                    return json.dumps({"unclear": True, "question": "Claude API error"})
                return "⚠️ Claude API error. Please try again."
        
        # For Gemini (default)
        print("🔥 GEMINI CALLED")
        if not self.gemini_available:
            if "Respond ONLY in JSON" in prompt:
                if any(greet in prompt.lower() for greet in ["hello", "hi", "hey"]):
                    return json.dumps({"unclear": False, "question": None})
                return json.dumps({"unclear": True, "question": "Gemini API key issue"})
            return "⚠️ Gemini API key missing. Add GEMINI_API_KEY to .env file"
        
        full_prompt = self._build_prompt_with_history(prompt, history)
        answer = self._call_gemini(full_prompt)
        
        if answer:
            return self._ensure_json_response(answer, prompt)
        else:
            if "Respond ONLY in JSON" in prompt:
                return json.dumps({"unclear": True, "question": "Gemini API error"})
            return "⚠️ Gemini API error. Please try again."

    def generate(self, prompt: str, history: list = None):
        return self.think(prompt, history)