import pytesseract
import pdfplumber
import os
from PIL import Image
import io

# Configure Tesseract path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_text_from_pdf_ocr(pdf_path):
    """
    Extract text from PDF using both direct extraction and OCR fallback
    """
    if not os.path.exists(pdf_path):
        return f"❌ PDF file not found at path: {pdf_path}"
    
    print(f"📄 Extracting text from: {pdf_path}")
    text = ""
    
    # First try: Direct text extraction
    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"📄 PDF has {len(pdf.pages)} pages")
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    text += page_text + "\n"
                    print(f"✅ Page {i+1}: Extracted {len(page_text)} chars directly")
    except Exception as e:
        print(f"⚠️ PDF direct extract error: {e}")
        text = ""  # Reset for OCR
    
    # If text is too short, try OCR
    if len(text.strip()) < 100:
        print("⚠️ Direct extraction gave little text, trying OCR...")
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    if page:
                        print(f"🖼️ Running OCR on page {i+1}...")
                        # Convert page to image
                        img = page.to_image(resolution=300)
                        
                        # Try different OCR configs
                        ocr_configs = [
                            "--psm 6",  # Assume uniform block of text
                            "--psm 3",  # Fully automatic
                            "--psm 4",  # Single column
                        ]
                        
                        for config in ocr_configs:
                            try:
                                ocr_text = pytesseract.image_to_string(
                                    img.original,
                                    lang="eng",  # Start with English only
                                    config=config
                                )
                                if ocr_text and ocr_text.strip():
                                    text += ocr_text + "\n"
                                    print(f"✅ Page {i+1}: OCR success with config {config}")
                                    break  # Break if we got text
                            except Exception as e:
                                print(f"⚠️ OCR config {config} failed: {e}")
                                continue
                                
        except Exception as e:
            print(f"❌ OCR error: {e}")
            text = "OCR extraction failed. The PDF might be corrupted or password protected."
    
    final_text = text.strip()
    print(f"📊 Total extracted text length: {len(final_text)} chars")
    
    if final_text:
        print(f"📊 Preview: {final_text[:200]}...")
        return final_text
    else:
        return "No text could be extracted from the PDF. It might be empty or contain only images without text."

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_text_from_pdf_ocr(pdf_path):
    text = ""

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    if len(text.strip()) < 50:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                img = page.to_image(resolution=300).original
                text += pytesseract.image_to_string(
                    img,
                    lang="hin+eng",
                    config="--psm 6"
                )

    return text.strip() or "Not mentioned in document."
