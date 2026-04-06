# tools/activity_capture.py
import pyautogui
import cv2
import numpy as np
import pytesseract
from datetime import datetime

import os
from memory.memory_manager import MemoryManager

memory = MemoryManager()

# folder ensure
os.makedirs("captures", exist_ok=True)


def capture_screen():
    screenshot = pyautogui.screenshot()
    img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"captures/screen_{timestamp}.png"

    cv2.imwrite(path, img)

    text = pytesseract.image_to_string(img)

    return path, text
def capture_webcam():
    cam = cv2.VideoCapture(0)

    ret, frame = cam.read()
    cam.release()

    if not ret:
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"captures/webcam_{timestamp}.png"

    cv2.imwrite(path, frame)
    return path


from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet

def create_activity_pdf(screen_img, webcam_img, screen_text):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_path = f"captures/activity_{timestamp}.pdf"

    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    styles = getSampleStyleSheet()

    story = []
    story.append(Paragraph("JARVIS Activity Capture", styles['Title']))
    story.append(Spacer(1,12))

    story.append(Paragraph("Screen Text Extracted:", styles['Heading2']))
    story.append(Paragraph(screen_text, styles['BodyText']))
    story.append(Spacer(1,12))

    story.append(Image(screen_img, width=400, height=250))
    story.append(Spacer(1,12))

    if webcam_img:
        story.append(Paragraph("Webcam Capture:", styles['Heading2']))
        story.append(Image(webcam_img, width=400, height=250))

    doc.build(story)

    return pdf_path

def run_full_activity_capture():
    try:
        # 1️⃣ capture screen
        screen_img, screen_text = capture_screen()

        # 2️⃣ capture webcam
        webcam_img = capture_webcam()

        # 3️⃣ create PDF
        pdf_path = create_activity_pdf(screen_img, webcam_img, screen_text)

        # 4️⃣ save to JARVIS memory
        save_activity_to_memory(pdf_path, screen_text)

        return {
            "status": "success",
            "pdf_path": pdf_path,
            "message": f"📸 Activity captured.\nPDF saved: {pdf_path}"
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

def save_activity_to_memory(pdf_path, screen_text):
    """
    Store activity capture into JARVIS long-term memory.
    """

    memory.store(
        content=f"""
ACTIVITY CAPTURE

PDF File: {pdf_path}

Extracted Screen Text:
{screen_text}
""",
        source_agent="activity_capture_agent",
        content_type="activity_log",
        confidence=0.95
    )


def run_full_activity_capture():
    try:
        # 1️⃣ capture screen
        screen_img, screen_text = capture_screen()

        # 2️⃣ capture webcam
        webcam_img = capture_webcam()

        # 3️⃣ create PDF
        pdf_path = create_activity_pdf(screen_img, webcam_img, screen_text)

        # 4️⃣ save to JARVIS memory
        save_activity_to_memory(pdf_path, screen_text)

        return {
            "status": "success",
            "pdf_path": pdf_path,
            "message": "📸 Activity captured, PDF created and memory stored."
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
