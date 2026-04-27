# utils/ocr_utils.py - COMPLETE IMPROVED VERSION (No Duplicate)

import pytesseract
import pdfplumber
import os
from PIL import Image, ImageEnhance, ImageFilter
import io
import traceback
from typing import Optional, Tuple

# Configure Tesseract path - Auto-detect with fallback
def set_tesseract_path():
    possible_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"D:\Program Files\Tesseract-OCR\tesseract.exe",
        r"D:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            print(f"✅ Tesseract found at: {path}")
            return True
    
    # Try system PATH
    try:
        pytesseract.get_tesseract_version()
        print("✅ Tesseract found in system PATH")
        return True
    except:
        print("❌ Tesseract not found! Please install Tesseract-OCR")
        return False

set_tesseract_path()

def preprocess_image_for_ocr(image):
    """Preprocess image for better OCR accuracy"""
    try:
        # Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        
        # Apply sharpening
        image = image.filter(ImageFilter.SHARPEN)
        
        # Resize if too large (improves performance)
        max_size = 2000
        if max(image.size) > max_size:
            ratio = max_size / max(image.size)
            new_size = tuple(int(dim * ratio) for dim in image.size)
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        return image
    except Exception as e:
        print(f"⚠️ Image preprocessing warning: {e}")
        return image

def extract_text_from_pdf_ocr(pdf_path: str, use_ocr_fallback: bool = True, lang: str = "eng") -> str:
    """
    Extract text from PDF using direct extraction first, then OCR fallback
    
    Args:
        pdf_path: Path to PDF file
        use_ocr_fallback: If True, use OCR when direct extraction fails
        lang: Language for OCR ("eng", "hin", "eng+hin")
    
    Returns:
        Extracted text from PDF
    """
    if not os.path.exists(pdf_path):
        return f"❌ PDF file not found at path: {pdf_path}"
    
    print(f"📄 Extracting text from: {os.path.basename(pdf_path)}")
    
    direct_text = ""
    ocr_text = ""
    total_pages = 0
    pages_with_direct = 0
    pages_with_ocr = 0
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            print(f"📄 Total pages: {total_pages}")
            
            for page_num, page in enumerate(pdf.pages, 1):
                page_content = ""
                
                # Step 1: Try direct text extraction (fastest)
                try:
                    page_direct = page.extract_text()
                    if page_direct and len(page_direct.strip()) > 50:
                        page_content = page_direct
                        pages_with_direct += 1
                        print(f"✅ Page {page_num}: Direct extraction - {len(page_direct)} chars")
                except Exception as e:
                    print(f"⚠️ Page {page_num} direct extraction error: {e}")
                
                # Step 2: If direct extraction gave little/no text and OCR is enabled
                if (not page_content or len(page_content.strip()) < 50) and use_ocr_fallback:
                    print(f"🖼️ Page {page_num}: Running OCR...")
                    try:
                        # Extract image from page
                        img = page.to_image(resolution=200)  # 200 DPI is enough, 300 is heavy
                        img_obj = img.original
                        
                        # Preprocess image
                        img_obj = preprocess_image_for_ocr(img_obj)
                        
                        # Try OCR with multiple configs
                        ocr_configs = [
                            "--psm 6 --oem 3",   # Uniform block of text
                            "--psm 3 --oem 3",   # Fully automatic
                            "--psm 4 --oem 3",   # Single column
                            "--psm 12 --oem 3",  # Sparse text
                        ]
                        
                        for config in ocr_configs:
                            try:
                                ocr_result = pytesseract.image_to_string(
                                    img_obj,
                                    lang=lang,
                                    config=config
                                )
                                if ocr_result and len(ocr_result.strip()) > 20:
                                    page_content = ocr_result
                                    pages_with_ocr += 1
                                    print(f"✅ Page {page_num}: OCR success - {len(ocr_result)} chars with config: {config}")
                                    break
                            except Exception as e:
                                continue
                                
                    except Exception as e:
                        print(f"❌ Page {page_num} OCR failed: {e}")
                
                # Add page separator for better context
                if page_content and page_content.strip():
                    direct_text += f"\n[Page {page_num}]\n{page_content.strip()}\n"
                else:
                    direct_text += f"\n[Page {page_num}]\n[No extractable text]\n"
        
        # Combine results
        final_text = direct_text.strip()
        
        # Statistics
        print(f"\n📊 Extraction Summary:")
        print(f"   - Total pages: {total_pages}")
        print(f"   - Direct extraction: {pages_with_direct} pages")
        print(f"   - OCR used: {pages_with_ocr} pages")
        print(f"   - Total characters: {len(final_text)}")
        
        if final_text and len(final_text) > 100:
            print(f"📊 Preview: {final_text[:300]}...")
            return final_text
        elif final_text and len(final_text) > 0:
            print(f"⚠️ Very short text extracted ({len(final_text)} chars)")
            return final_text
        else:
            return "❌ No text could be extracted from the PDF. The file might be empty, corrupted, or contain only images without text."
            
    except Exception as e:
        print(f"❌ PDF extraction error: {e}")
        traceback.print_exc()
        return f"❌ Error extracting PDF: {str(e)}"

def extract_text_from_pdf_fast(pdf_path: str) -> str:
    """
    Fast extraction - direct text only, no OCR fallback
    Use this for text-based PDFs to save time
    """
    if not os.path.exists(pdf_path):
        return f"❌ PDF file not found at path: {pdf_path}"
    
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        return f"❌ Error: {str(e)}"
    
    return text.strip() or "No text found in PDF (might be scanned image)"

def extract_text_from_pdf_with_hindi(pdf_path: str) -> str:
    """
    Extract text with Hindi language support (slower but better for Hindi docs)
    """
    return extract_text_from_pdf_ocr(pdf_path, use_ocr_fallback=True, lang="hin+eng")

# For testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        test_path = sys.argv[1]
        print(f"\n{'='*60}")
        print("TESTING PDF EXTRACTION")
        print(f"{'='*60}")
        
        # Test 1: Normal extraction
        print("\n🔵 TEST 1: Normal extraction (direct + OCR)")
        text1 = extract_text_from_pdf_ocr(test_path)
        print(f"\nLength: {len(text1)} chars")
        
        # Test 2: Fast extraction only
        print("\n🔵 TEST 2: Fast extraction (direct only)")
        text2 = extract_text_from_pdf_fast(test_path)
        print(f"Length: {len(text2)} chars")
        
        print(f"\n{'='*60}")
        print("FIRST 500 CHARS OF EXTRACTED TEXT:")
        print(f"{'='*60}")
        print(text1[:500] if text1 else "No text extracted")
    else:
        print("Usage: python ocr_utils.py <pdf_path>")