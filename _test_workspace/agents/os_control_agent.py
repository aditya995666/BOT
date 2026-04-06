# 📦 IMPORTS

import os
import subprocess
import webbrowser
import pyautogui
import psutil
import time
import cv2
import numpy as np
import pytesseract
import platform
from datetime import datetime
from ultralytics import YOLO
import re

# PDF creation
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet

# Memory
from memory.memory_manager import MemoryManager

memory = MemoryManager()

pyautogui.FAILSAFE = False
os.makedirs("captures", exist_ok=True)
os.makedirs("files", exist_ok=True)

# Windows users ke liye tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


# 🤖 OS CONTROL AGENT

class OSControlAgent:

    def __init__(self):
        self.live_writing = False
        self.current_file = None
        self.pending_screenshot_name = None
        self.pending_webscan_name = None

    # 🟢 BASIC OS CONTROL

    def open_app(self, app_name: str):
        try:
            app_name_lower = app_name.lower().strip()
            
            # 🌐 WEBSITES - webbrowser module use karo
            websites = {
                "google": "https://www.google.com",
                "youtube": "https://www.youtube.com",
                "github": "https://github.com",
                "stackoverflow": "https://stackoverflow.com",
                "gmail": "https://mail.google.com",
                "reddit": "https://reddit.com",
                "twitter": "https://twitter.com",
                "facebook": "https://facebook.com",
                "instagram": "https://instagram.com",
                "linkedin": "https://linkedin.com",
                "amazon": "https://amazon.com",
                "flipkart": "https://flipkart.com",
                "chatgpt": "https://chat.openai.com",
                "gemini": "https://gemini.google.com",
                "bing": "https://bing.com",
                "yahoo": "https://yahoo.com",
                "wikipedia": "https://wikipedia.org",
                "netflix": "https://netflix.com",
                "hotstar": "https://hotstar.com",
                "prime": "https://primevideo.com",
            }
            
            # Check if it's a known website
            if app_name_lower in websites:
                url = websites[app_name_lower]
                webbrowser.open(url)
                return f"🌐 {app_name} opened in browser ✅"
            
            # Check if it's any URL (contains .com, .in, etc.)
            if '.' in app_name_lower and not app_name_lower.endswith('.exe'):
                if not app_name_lower.startswith('http'):
                    url = 'https://' + app_name_lower
                else:
                    url = app_name_lower
                webbrowser.open(url)
                return f"🌐 Opened {url} ✅"
            
            # 🖥️ WINDOWS APPLICATIONS
            apps = {
                "notepad": "notepad.exe",
                "chrome": "chrome.exe",
                "firefox": "firefox.exe",
                "edge": "msedge.exe",
                "browser": "chrome.exe",
                "cmd": "cmd.exe",
                "terminal": "cmd.exe",
                "command prompt": "cmd.exe",
                "explorer": "explorer.exe",
                "file explorer": "explorer.exe",
                "calculator": "calc.exe",
                "calc": "calc.exe",
                "paint": "mspaint.exe",
                "vscode": "code",
                "vs code": "code",
                "visual studio code": "code",
                "spotify": "Spotify.exe",
                "whatsapp": "WhatsApp.exe",
                "telegram": "Telegram.exe",
                "discord": "Discord.exe",
                "slack": "slack.exe",
                "zoom": "Zoom.exe",
                "teams": "Teams.exe",
                "outlook": "OUTLOOK.EXE",
                "word": "WINWORD.EXE",
                "excel": "EXCEL.EXE",
                "powerpoint": "POWERPNT.EXE",
            }
            
            app_exe = apps.get(app_name_lower, app_name)
            
            if platform.system() == "Windows":
                # Try with start command
                subprocess.Popen(f'start "" "{app_exe}"', shell=True)
            else:
                subprocess.Popen([app_exe])
            
            time.sleep(2)
            return f"✅ {app_name} opened successfully"
            
        except Exception as e:
            return f"❌ Failed to open {app_name}: {str(e)}"

    # 🔍 SEARCH IN CURRENT BROWSER TAB

    def search_in_current_tab(self, query: str):
        """Search in currently active browser tab (Google, YouTube, etc.)"""
        try:
            time.sleep(0.5)
            
            # Ctrl+L to select address bar
            pyautogui.hotkey('ctrl', 'l')
            time.sleep(0.3)
            
            # Type the search query
            pyautogui.write(query)
            time.sleep(0.3)
            
            # Press Enter to search
            pyautogui.press('enter')
            
            return f"🔍 Searched for '{query}' ✅"
            
        except Exception as e:
            return f"❌ Search failed: {e}"

    def search_on_youtube(self, query: str):
        """Search directly on YouTube"""
        try:
            # Open YouTube first
            webbrowser.open("https://www.youtube.com")
            time.sleep(2)
            
            # Click on search box (Tab key to navigate)
            pyautogui.hotkey('ctrl', 'l')  # Address bar
            time.sleep(0.3)
            
            # Type search
            pyautogui.write(query)
            time.sleep(0.3)
            
            pyautogui.press('enter')
            
            return f"🎬 Searched YouTube for '{query}' ✅"
            
        except Exception as e:
            return f"❌ YouTube search failed: {e}"

    def close_app(self, app_name: str):
        closed = False
        for proc in psutil.process_iter(['name']):
            if app_name.lower() in proc.info['name'].lower():
                proc.kill()
                closed = True
        return f"{app_name} closed" if closed else f"{app_name} not running"

    def type_text(self, text: str):
        time.sleep(1.5)
        pyautogui.write(text, interval=0.05)
        return "Typed successfully ✅"

    def click_mouse(self):
        pyautogui.click()
        return "Mouse clicked ✅"

    def create_file(self, filename: str, content: str = ""):
        # Ensure filename has extension
        if '.' not in filename:
            filename = filename + '.txt'
        
        # Save in files folder
        filepath = os.path.join("files", filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return filepath

    def append_to_file(self, filename: str, content: str):
        try:
            # 🔥 FIX: Pehle current_file check karo (priority)
            filepath = None
            
            # 1. Check current_file first (most recent)
            if self.current_file and os.path.exists(self.current_file):
                filepath = self.current_file
                print(f"📝 Using current_file: {filepath}")
            
            # 2. Check in current directory (where create_and_open_file saves)
            if not filepath:
                current_dir_path = os.path.join(os.getcwd(), filename)
                if os.path.exists(current_dir_path):
                    filepath = current_dir_path
                    print(f"📝 Found in current dir: {filepath}")
            
            # 3. Check in files folder
            if not filepath:
                files_folder_path = os.path.join("files", filename)
                if os.path.exists(files_folder_path):
                    filepath = files_folder_path
                    print(f"📝 Found in files folder: {filepath}")
            
            # 4. Check in current_dir/files folder
            if not filepath:
                cwd_files_path = os.path.join(os.getcwd(), "files", filename)
                if os.path.exists(cwd_files_path):
                    filepath = cwd_files_path
                    print(f"📝 Found in cwd/files: {filepath}")
            
            # 5. Agar koi file nahi mili to nayi banao (current directory mein)
            if not filepath:
                filepath = os.path.join(os.getcwd(), filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write("")
                print(f"📝 Created new file: {filepath}")
            
            print(f"📝 Writing to file: {filepath}")
            
            # Write content
            with open(filepath, "a", encoding="utf-8") as f:
                # Check if file already has content
                f.seek(0, 2)  # Go to end
                if f.tell() > 0:  # If file not empty
                    f.write("\n")
                f.write(content)
            
            # Update current_file
            self.current_file = filepath
            
            # Verify content was written
            with open(filepath, "r", encoding="utf-8") as f:
                file_content = f.read()
                if content in file_content:
                    return f"✅ '{content}' likh diya {os.path.basename(filepath)} mein"
                else:
                    return f"⚠️ Write attempted but verification failed for {os.path.basename(filepath)}"
            
        except Exception as e:
            print(f"❌ Append error: {e}")
            return f"❌ File mein likhne mein error: {str(e)}"

    def run_python(self, file: str):
        subprocess.Popen(["python", file])
        return f"Running {file} ✅"

    def shutdown(self):
        system = platform.system()
        if system == "Windows":
            os.system("shutdown /s /t 5")
        elif system == "Linux":
            os.system("shutdown -h +1")
        elif system == "Darwin":
            os.system("sudo shutdown -h now")
        return "Shutdown command sent in 5 seconds ✅"

    # 📷 CAMERA CONTROL

    def open_camera_live(self):
        try:
            # Load YOLO model (ye automatically 80+ objects detect karega)
            model = YOLO("yolov8n.pt")  # nano model - fast and light
            cap = cv2.VideoCapture(0)
            
            if not cap.isOpened():
                return "Camera not found ❌"

            print("🎥 Camera started - YOLO detecting objects automatically...")
            
            # Focal length constant (adjust this for your camera)
            FOCAL_LENGTH = 600  # Isko increase karo to distance zyada aayega

            while True:
                ret, frame = cap.read()
                if not ret:
                    break
            
                results = model(frame, stream=True)
            
                for r in results:
                    boxes = r.boxes
                
                    if boxes is not None:
                        for box in boxes:
                            # Get bounding box
                            x1, y1, x2, y2 = box.xyxy[0].tolist()
                            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                        
                            cls = int(box.cls[0])
                            conf = float(box.conf[0])
                            class_name = model.names[cls]
                        
                            # Calculate box width
                            box_width = x2 - x1
                        
                            # 🔥 IMPROVED DISTANCE CALCULATION
                            if box_width > 0:
                                distance_cm = round((FOCAL_LENGTH * 30) / box_width, 1)
                            
                                # Add dynamic scaling for very far objects
                                if distance_cm > 1000:
                                    distance_cm = round((FOCAL_LENGTH * 30 * 1.5) / box_width, 1)
                            else:
                                distance_cm = 0
                            
                            if distance_cm < 50:
                                color = (0, 0, 255)  # Red - very close
                                distance_text = f"{distance_cm}cm ⚠️"
                            elif distance_cm < 200:
                                color = (0, 255, 255)  # Yellow - medium
                                distance_text = f"{distance_cm}cm 📏"
                            elif distance_cm < 500:
                                color = (0, 255, 0)  # Green - far
                                distance_text = f"{distance_cm}cm 🔭"
                            else:
                                color = (255, 0, 255)  # Purple - very far
                                distance_text = f"{distance_cm}cm 🌌"
                        
                            # Draw bounding box
                            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                        
                            # Main label
                            label = f"{class_name}: {conf:.2f} | {distance_text}"
                        
                            # Put text above box
                            y_pos = y1 - 10 if y1 - 10 > 10 else y1 + 10
                            cv2.putText(frame, label, (x1, y_pos), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                        
                            # Extra info for far objects
                            if distance_cm > 500:
                                cv2.putText(frame, "🚀 Very Far", (x1, y2 + 20),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 255), 1)
                            elif distance_cm > 200:
                                cv2.putText(frame, "📡 Far", (x1, y2 + 20),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
            
                # Show info on screen
                cv2.putText(frame, "JARVIS AI Vision - Auto Object Detection", 
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(frame, "Press Q or ESC to close", 
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            
                # Show frame
                cv2.imshow("JARVIS AI Vision - Object Detection with Distance", frame)

                # Check for exit key
                key = cv2.waitKey(1) & 0xFF
                if key == 27 or key == ord('q') or key == ord('Q'):
                    break

            cap.release()
            cv2.destroyAllWindows()
            cv2.waitKey(1)
            return "Camera closed ✅"
            
        except Exception as e:
            return f"Camera error: {e}"

    def capture_webcam(self):
        cam = cv2.VideoCapture(0)
        ret, frame = cam.read()
        cam.release()
        if not ret:
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"captures/webcam_{timestamp}.png"
        cv2.imwrite(path, frame)
        return path

    # 🖥 SCREEN CAPTURE + OCR

    def capture_screen(self, filename=None):
        screenshot = pyautogui.screenshot()
        img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

        if filename:
            # Clean filename
            filename = re.sub(r'[^\w\-_\.]', '', filename)
            if not filename.endswith('.png'):
                filename += '.png'
            path = os.path.join("captures", filename)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = f"captures/screen_{timestamp}.png"
        
        cv2.imwrite(path, img)
        text = pytesseract.image_to_string(img)
        return path, text

    def take_screenshot(self, filename=None):
        path, text = self.capture_screen(filename)
        return f"Screenshot saved: {path} ✅"

    # 📄 CREATE ACTIVITY PDF

    def create_activity_pdf(self, screen_img: str, webcam_img: str | None, screen_text: str, filename=None):
        if filename:
            filename = re.sub(r'[^\w\-_\.]', '', filename)
            if not filename.endswith('.pdf'):
                filename += '.pdf'
            pdf_path = os.path.join("captures", filename)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pdf_path = f"captures/activity_{timestamp}.pdf"

        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("JARVIS Activity Capture", styles['Title']))
        story.append(Spacer(1, 12))
        story.append(Paragraph("Screen Text Extracted:", styles['Heading2']))
        story.append(Paragraph(screen_text or "No text extracted", styles['BodyText']))
        story.append(Spacer(1, 12))
        story.append(Image(screen_img, width=500, height=300))
        story.append(Spacer(1, 12))

        if webcam_img:
            story.append(Paragraph("Webcam Capture:", styles['Heading2']))
            story.append(Image(webcam_img, width=500, height=300))

        doc.build(story)
        return pdf_path

    # 🧠 SAVE TO MEMORY

    def save_activity_to_memory(self, pdf_path: str, screen_text: str):
        memory.store(
            content=f"ACTIVITY CAPTURE\nPDF: {pdf_path}\nText:\n{screen_text}",
            source_agent="os_control_agent",
            content_type="activity_log",
            confidence=0.95
        )

    # 🚀 FILE OPERATIONS
    
    def create_and_open_file(self, filename: str, content: str = ""):
        try:
            # Ensure filename has extension
            if '.' not in filename:
                filename = filename + '.txt'
            
            # Clean filename
            filename = re.sub(r'[^\w\-_\.]', '', filename)
            
            # 🔥 FIX: Always use "files" folder (consistent with append_to_file)
            filepath = os.path.join(os.getcwd(), "files", filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Check if file already exists
            if os.path.exists(filepath):
                # Just open existing file
                os.startfile(filepath)
                self.current_file = filepath
                print(f"📂 Opened existing: {filepath}")
                return f"{filename} opened ✅"
            
            # Create new file
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            
            # Open the file
            os.startfile(filepath)
            time.sleep(1)
            self.current_file = filepath
            print(f"📂 Created and opened: {filepath}")
            
            return f"{filename} created and opened ✅"
        except Exception as e:
            print(f"❌ File error: {e}")
            return f"Error: {e}"
        
    def write_to_current_file(self, content: str):
        """Write content to current active file"""
        if not self.current_file:
            return "No active file. First create/open a file."
        
        try:
            with open(self.current_file, "a", encoding="utf-8") as f:
                f.write("\n" + content)
            return f"✅ Written to {os.path.basename(self.current_file)}"
        except Exception as e:
            return f"Error writing to file: {e}"

    # 🚀 FULL ACTIVITY CAPTURE
    
    def run_full_activity_capture(self, filename=None):
        try:
            screen_img, screen_text = self.capture_screen()
            webcam_img = self.capture_webcam()
            pdf_path = self.create_activity_pdf(screen_img, webcam_img, screen_text, filename)
            self.save_activity_to_memory(pdf_path, screen_text)
            return f"📸 Full activity captured. PDF: {pdf_path}"
        except Exception as e:
            return f"Activity capture error: {e}"
    
    def run_web_scan(self, filename=None):
        """Scan webpage and save as PDF with filename"""
        try:
            # Take screenshot of browser
            time.sleep(2)  # Wait for browser to be ready
            screen_img, screen_text = self.capture_screen()
            
            # Create PDF with filename
            if filename:
                filename = re.sub(r'[^\w\-_\.]', '', filename)
                if not filename.endswith('.pdf'):
                    filename += '.pdf'
                pdf_path = os.path.join("captures", filename)
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                pdf_path = f"captures/webscan_{timestamp}.pdf"
            
            # Create PDF
            doc = SimpleDocTemplate(pdf_path, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            story.append(Paragraph("Web Page Scan", styles['Title']))
            story.append(Spacer(1, 12))
            story.append(Paragraph("Extracted Text:", styles['Heading2']))
            story.append(Paragraph(screen_text or "No text extracted", styles['BodyText']))
            story.append(Spacer(1, 12))
            story.append(Image(screen_img, width=500, height=300))
            
            doc.build(story)
            
            return f"🌐 Web scan saved as: {pdf_path}"
        except Exception as e:
            return f"Web scan error: {e}"