import speech_recognition as sr
import pyttsx3
import tempfile
import os
import traceback

from agents.voice_chat_agent import voice_brain

engine = pyttsx3.init()
engine.setProperty("rate", 170)
engine.setProperty("volume", 1)


def transcribe_audio(audio_bytes, lang="hi-IN"):

    print("🎧 [STEP 1] Transcription started")

    try:
        r = sr.Recognizer()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        print("📁 Temp audio file created:", tmp_path)

        with sr.AudioFile(tmp_path) as source:
            audio = r.record(source)

        print("🌐 Sending to Google API...")

        text = r.recognize_google(audio, language=lang)

        os.remove(tmp_path)

        print("✅ 🎙️ Transcribed:", text)
        return text.strip()

    except Exception as e:
        print("❌ Transcription error:")
        traceback.print_exc()
        return None


def speak_voice(text):

    print("🔊 [STEP 4] TTS Started")

    try:
        engine.stop()
        engine.say(text[:300])
        engine.runAndWait()
        print("✅ TTS Finished")

    except Exception as e:
        print("❌ TTS error:")
        traceback.print_exc()


def process_voice(audio_bytes, voice_enabled=True):

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🎤 VOICE PIPELINE STARTED")
    print("📥 Audio bytes received:", len(audio_bytes))

    user_text = transcribe_audio(audio_bytes)

    if not user_text:
        print("❌ No transcription result")
        return "Voice samajh nahi aayi."

    print("👤 User said:", user_text)

    print("🧠 [STEP 2] Sending to router...")
    response = voice_brain(user_text, voice_mode=True)

    print("🤖 Router response:", response)

    if voice_enabled:
        speak_voice(response)

    print("🏁 VOICE PIPELINE FINISHED")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━")

    return {
        "user_text": user_text,
        "jarvis_response": response
    }
import time
import speech_recognition as sr
import pyttsx3
from agents.voice_chat_agent import voice_brain
# Import the voice brain

def listen_voice(lang="hi-IN", timeout=6):
    """Capture user speech from the microphone and convert to text."""
    r = sr.Recognizer()
    try:
        with sr.Microphone() as src:
            r.adjust_for_ambient_noise(src, duration=0.6)
            audio = r.listen(src, timeout=timeout)

        text = r.recognize_google(audio, language=lang)
        return text.strip()

    except sr.WaitTimeoutError:
        return None
    except sr.UnknownValueError:
        return None
    except Exception as e:
        print("Mic Error:", e)
        return None

import pyttsx3

engine = pyttsx3.init()
engine.setProperty('rate', 170)

def speak_text(text, lang="hi"):
    if not text or not text.strip():
        return None

    print("🗣️ Speaking...")
    engine.say(text)
    engine.runAndWait()


def voice_chat_loop():
    print("🎙️ JARVIS Voice Ready (say 'stop' to exit)")

    while True:
        user_text = listen_voice()

        if not user_text:
            print("No speech detected...")
            continue

        print("👤 You:", user_text)

        # universal stop words
        if any(x in user_text.lower() for x in ["stop","exit","band","close"]):
            speak_text("ठीक है, फिर मिलते हैं 🙂")
            break

        # 🔥 NOW ROUTER IS USED
        # 🤖 SEND TO ROUTER (BRAIN)
        ai_reply = voice_brain(
    user_text + " (reply short and conversational for voice)"
)

        print("🤖 JARVIS:", ai_reply)

# 🔊 SPEAK RESPONSE
        speak_text(ai_reply)



        time.sleep(1.2)


if __name__ == "__main__":
    voice_chat_loop()
