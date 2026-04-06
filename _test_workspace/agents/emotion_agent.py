from brain.gemini_llm import GeminiBrain
from utils.prompt_templates import EMOTION_PROMPT

brain = GeminiBrain()

def detect_emotion(text):
    return brain.think(EMOTION_PROMPT.format(query=text))