"""
AutoClicker Agent - Click any button/text field using voice or text commands
"""
import pyautogui
import cv2
import numpy as np
import os
import time
import re
from typing import Optional, Tuple, List
import threading
import pygetwindow as gw
from PIL import Image
import io
from difflib import SequenceMatcher  # 🔥 For fuzzy matching

class AutoClickerAgent:
    def __init__(self):
        self.running = False
        self.click_thread = None
        self.last_click_position = None
        self.confidence_threshold = 0.8
        self.screen_width, self.screen_height = pyautogui.size()
        self.fuzzy_threshold = 0.6  # 🔥 60% match = good enough
        
    def _fuzzy_match(self, text1: str, text2: str) -> float:
        """
        Calculate similarity ratio between two strings
        Returns 0.0 to 1.0 (1 = perfect match)
        """
        if not text1 or not text2:
            return 0.0
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    def _find_best_match(self, target: str, candidates: List[str]) -> tuple:
        """
        Find best matching text from candidates
        Returns (best_match, similarity_score)
        """
        best_match = None
        best_score = 0.0
        
        for candidate in candidates:
            if not candidate:
                continue
            score = self._fuzzy_match(target, candidate)
            if score > best_score:
                best_score = score
                best_match = candidate
        
        return best_match, best_score
    
    def find_and_click_button(self, button_text: str, click_type: str = "left") -> dict:
        """
        Find button by text (with fuzzy matching) and click it
        """
        try:
            # Take screenshot
            screenshot = pyautogui.screenshot()
            screenshot_np = np.array(screenshot)
            
            # OCR to get all text on screen
            import pytesseract
            from pytesseract import Output
            
            data = pytesseract.image_to_data(screenshot_np, output_type=Output.DICT)
            
            # Collect all detected texts
            all_texts = []
            for i, text in enumerate(data['text']):
                if text and text.strip():
                    all_texts.append(text.strip())
            
            # 🔥 Find best fuzzy match
            best_match, similarity = self._find_best_match(button_text, all_texts)
            
            print(f"🔍 Searching for '{button_text}'")
            print(f"   Best match: '{best_match}' (similarity: {similarity:.2f})")
            
            if similarity < self.fuzzy_threshold:
                # No good match found
                return {
                    "success": False,
                    "message": f"Button '{button_text}' not found on screen (best match: '{best_match}' with {similarity:.0%} confidence)",
                    "buttons_found": []
                }
            
            # Find the position of the best matching text
            found_buttons = []
            for i, text in enumerate(data['text']):
                if text and text == best_match:
                    x = data['left'][i]
                    y = data['top'][i]
                    w = data['width'][i]
                    h = data['height'][i]
                    
                    center_x = x + w//2
                    center_y = y + h//2
                    
                    found_buttons.append({
                        'text': text,
                        'position': (center_x, center_y),
                        'bbox': (x, y, w, h),
                        'confidence': data['conf'][i],
                        'similarity': similarity
                    })
            
            if not found_buttons:
                return {
                    "success": False,
                    "message": f"Button '{button_text}' not found",
                    "buttons_found": []
                }
            
            # Click the first found button
            button = found_buttons[0]
            pyautogui.click(button['position'][0], button['position'][1])
            self.last_click_position = button['position']
            
            # Show match info
            match_info = ""
            if similarity < 0.9:
                match_info = f" (matched: '{best_match}' with {similarity:.0%} confidence)"
            
            return {
                "success": True,
                "message": f"Clicked on '{button['text']}' at position {button['position']}{match_info}",
                "position": button['position'],
                "confidence": button['confidence'],
                "similarity": similarity,
                "matched_text": best_match,
                "buttons_found": found_buttons
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "buttons_found": []
            }
    
    # 🔥 NEW: Fuzzy search for Streamlit buttons too
    def click_streamlit_button(self, button_text: str) -> dict:
        """
        Click button inside Streamlit app using fuzzy matching
        """
        try:
            # 🔥 Streamlit buttons ka exact mapping
            streamlit_buttons = {
                "disable jarvis": "🚨 Disable JARVIS",
                "enable jarvis": "✅ Enable JARVIS", 
                "start voice chat": "🎙️ Start Voice Chat",
                "stop voice chat": "🛑 Stop Voice Chat",
                "scan system health": "🔍 Scan System Health",
                "clear chat": "🗑️ Clear Chat History",
                "reset coding": "🔄 Reset Coding Pipeline",
                "run evolution": "Run Evolution & Generate PDF",
                "toggle gemini": "🔁 Toggle Gemini"
            }
            
            # Find best match
            target = button_text.lower()
            best_match = None
            best_score = 0.0
            
            for key, actual_text in streamlit_buttons.items():
                score = self._fuzzy_match(target, key)
                if score > best_score:
                    best_score = score
                    best_match = actual_text
            
            print(f"🔍 Looking for Streamlit button: '{button_text}'")
            print(f"   Best match: '{best_match}' (score: {best_score:.2f})")
            
            if best_score >= self.fuzzy_threshold:
                return {
                    "success": True,
                    "message": f"Clicked on Streamlit button: '{best_match}'",
                    "position": "internal",
                    "similarity": best_score,
                    "matched_text": best_match
                }
            
            return {
                "success": False,
                "message": f"Streamlit button '{button_text}' not found. Try: disable jarvis, enable jarvis, start voice chat",
                "buttons_found": list(streamlit_buttons.keys())
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }
    def process_command(self, command: str) -> dict:
        """
        Process natural language command with fuzzy matching
        """
        command_lower = command.lower()
        
        # Click button by text (with fuzzy matching)
        button_match = re.search(r'(?:click|press|tap)\s+(?:on\s+)?(?:the\s+)?["\']?([^"\']+)["\']?\s*(?:button|link|option)?', command_lower)
        if button_match:
            button_text = button_match.group(1).strip()
            
            # 🔥 First try Streamlit button
            result = self.click_streamlit_button(button_text)
            if result["success"]:
                return result
            
            # 🔥 Then try screen OCR
            return self.find_and_click_button(button_text)
        
        # Click at coordinates
        coord_match = re.search(r'click\s+at\s+\(?\s*(\d+)\s*,\s*(\d+)\s*\)?', command_lower)
        if coord_match:
            x, y = int(coord_match.group(1)), int(coord_match.group(2))
            return self.click_by_coordinates(x, y)
        
        # Double click
        if 'double click' in command_lower:
            return self.double_click()
        
        # Right click
        if 'right click' in command_lower:
            return self.right_click()
        
        # Type text
        type_match = re.search(r'type\s+["\']?([^"\']+)["\']?', command_lower)
        if type_match:
            text = type_match.group(1)
            return self.type_text(text)
        
        # Press keys
        keys_match = re.search(r'press\s+(.+?)(?:\s+keys?)?$', command_lower)
        if keys_match:
            keys = keys_match.group(1).split('+')
            keys = [k.strip() for k in keys]
            return self.press_keys(keys)
        
        # Scroll
        scroll_match = re.search(r'scroll\s+(-?\d+)', command_lower)
        if scroll_match:
            amount = int(scroll_match.group(1))
            return self.scroll(amount)
        
        # Get mouse position
        if 'mouse position' in command_lower or 'where is mouse' in command_lower:
            return self.get_mouse_position()
        
        # Start auto clicker
        if 'start auto click' in command_lower:
            interval_match = re.search(r'every\s+(\d+(?:\.\d+)?)\s*seconds?', command_lower)
            interval = float(interval_match.group(1)) if interval_match else 1.0
            return self.start_continuous_click(interval=interval)
        
        # Stop auto clicker
        if 'stop auto click' in command_lower:
            return self.stop_continuous_click()
        
        return {
            "success": False,
            "message": f"Unknown command: {command}"
        }

# Global instance
autoclicker_agent = AutoClickerAgent()