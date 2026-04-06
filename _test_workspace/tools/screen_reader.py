# tools/screen_reader.py
import pytesseract
import pyautogui
import cv2
import numpy as np

def read_screen():
    screenshot = pyautogui.screenshot()
    img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    text = pytesseract.image_to_string(img)
    return text.strip()