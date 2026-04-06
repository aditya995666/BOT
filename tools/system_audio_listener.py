# tools/system_audio_listener.py (RENAMED FILE)
import sounddevice as sd
import numpy as np
import whisper
import scipy.io.wavfile as wavfile
import tempfile
import threading
import queue
import time

class SystemAudioListener:
    def __init__(self, model_size="base"):
        try:
            self.model = whisper.load_model(model_size)
        except Exception as e:
            print(f"⚠️ Whisper model loading error: {e}")
            self.model = None
        self.audio_queue = queue.Queue()
        self.is_listening = False
        self.sample_rate = 16000
    
    def audio_callback(self, indata, frames, time, status):
        """Callback for sounddevice stream"""
        if status:
            print(f"Audio status: {status}")
        self.audio_queue.put(indata.copy())
    
    def start_listening(self, duration=10):
        """
        Listen to system audio for specified duration
        Returns transcribed text
        """
        if self.model is None:
            return "Whisper model not available"
            
        self.is_listening = True
        audio_data = []
        
        try:
            with sd.InputStream(callback=self.audio_callback,
                              channels=1,
                              samplerate=self.sample_rate,
                              dtype='float32'):
                print(f"Listening for {duration} seconds...")
                time.sleep(duration)
                self.is_listening = False
                
                # Collect all audio data
                while not self.audio_queue.empty():
                    audio_data.append(self.audio_queue.get())
                
                if audio_data:
                    audio_array = np.concatenate(audio_data, axis=0)
                    
                    # Save to temporary file
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                        wavfile.write(tmp.name, self.sample_rate, 
                                     (audio_array * 32767).astype(np.int16))
                        
                        # Transcribe
                        result = self.model.transcribe(tmp.name)
                        return result.get("text", "").strip()
        
        except Exception as e:
            print(f"Audio listening error: {e}")
            self.is_listening = False
        
        return ""

def listen_system_audio(duration=5):
    """Simple function to listen to system audio"""
    listener = SystemAudioListener()
    return listener.start_listening(duration)