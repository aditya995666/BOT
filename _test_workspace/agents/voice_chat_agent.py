"""
UNIVERSAL VOICE AGENT - Sare features voice mode mein
Coding, Browser, AutoClicker, Research, Document, PDF, OS, Evolution, Sab kuch!
"""

import speech_recognition as sr
import pyttsx3
import tempfile
import os
import traceback
import re

from agents.router import router

# Initialize TTS engine
engine = pyttsx3.init()
engine.setProperty("rate", 170)
engine.setProperty("volume", 1)

def transcribe_audio(audio_bytes, lang="hi-IN"):
    """Convert audio to text"""
    print("🎧 Transcription started")
    try:
        r = sr.Recognizer()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        
        with sr.AudioFile(tmp_path) as source:
            audio = r.record(source)
        
        text = r.recognize_google(audio, language=lang)
        os.remove(tmp_path)
        print(f"✅ Transcribed: {text}")
        return text.strip()
    except Exception as e:
        print(f"❌ Transcription error: {e}")
        return None

def speak_voice(text):
    """Convert text to speech"""
    print("🔊 Speaking...")
    try:
        # Clean text for speech (remove markdown, code blocks, etc.)
        clean_text = re.sub(r'```.*?```', '[Code block]', text, flags=re.DOTALL)
        clean_text = re.sub(r'[#*`_]', '', clean_text)
        clean_text = clean_text[:400]  # Limit length
        
        engine.stop()
        engine.say(clean_text)
        engine.runAndWait()
        print("✅ Speech done")
    except Exception as e:
        print(f"❌ TTS error: {e}")

def voice_brain(user_text: str, voice_mode=False):
    """
    MAIN VOICE FUNCTION - Handles ALL features
    Coding, Browser, AutoClicker, Research, Document, PDF, OS, Evolution, etc.
    """
    print(f"🧠 Processing voice command: {user_text}")
    
    # Send to router with voice_mode flag
    response = router.route(
        query=user_text,
        context={
            "voice_mode": voice_mode,
            "source": "voice"
        }
    )
    
    print(f"🤖 Router response type: {type(response)}")
    
    # Extract response text for ALL possible response formats
    response_text = _extract_response_text(response)
    
    return response_text

def _extract_response_text(response):
    """Extract text from ANY response format"""
    
    if isinstance(response, str):
        return response
    
    if isinstance(response, dict):
        # Case 1: Direct content
        if "content" in response:
            return response["content"]
        
        # Case 2: Result with content
        if "result" in response:
            result = response["result"]
            if isinstance(result, dict):
                if "content" in result:
                    return result["content"]
                if "message" in result:
                    return result["message"]
                if "text" in result:
                    return result["text"]
                if "answer" in result:
                    return result["answer"]
                # For coding agent
                if "generated_code" in result:
                    return f"Code generated: {result.get('explanation', '')}"
            return str(result)
        
        # Case 3: Message field
        if "message" in response:
            return response["message"]
        
        # Case 4: Text field
        if "text" in response:
            return response["text"]
        
        # Case 5: Answer field
        if "answer" in response:
            return response["answer"]
        
        # Case 6: For form filling
        if "next_field" in response:
            next_field = response["next_field"]
            if isinstance(next_field, dict):
                return next_field.get("question", "Please provide value")
            return str(next_field)
        
        # Case 7: For autoclicker
        if "handled" in response:
            return response.get("content", "Command executed")
        
        # Default
        return str(response)
    
    return str(response)

def process_voice(audio_bytes, voice_enabled=True):
    """Process voice input and return response"""
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🎤 VOICE PIPELINE STARTED")
    
    user_text = transcribe_audio(audio_bytes)
    
    if not user_text:
        return "Voice samajh nahi aayi."
    
    print(f"👤 User said: {user_text}")
    
    response = voice_brain(user_text, voice_mode=True)
    
    print(f"🤖 Response: {response[:200]}...")
    
    if voice_enabled:
        speak_voice(response)
    
    print("🏁 VOICE PIPELINE FINISHED")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    return {
        "user_text": user_text,
        "jarvis_response": response
    }
# agents/voice_chat_agent.py
# 🎤 Voice device for JARVIS (NO THINKING HERE)

from agents.router import router

def voice_brain(user_text: str):
    """
    Voice agent now sends text directly to Router.
    Router decides everything.
    """
    response = router.route(query=user_text)

    if isinstance(response, dict):
        return response.get("result", {}).get("content", "")
    
    return str(response)
