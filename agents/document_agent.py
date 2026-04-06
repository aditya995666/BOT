# agents/document_agent.py - FIXED VERSION

from brain.gemini_llm import GeminiBrain
from utils.prompt_templates import DOCUMENT_PROMPT
import re
from typing import Dict, Any, Optional, List
from datetime import datetime
from utils.ocr_utils import extract_text_from_pdf_ocr
import os

brain = GeminiBrain()

def document_agent(context: str, query: str, history=None, pdf_path: Optional[str] = None, pdf_paths: Optional[List[str]] = None) -> Dict[str, Any]:
    try:
        print(f"📄 Document agent processing query: '{query}'")
        print(f"📄 Context provided: {bool(context)}")
        print(f"📄 PDF path provided: {pdf_path}")
        print(f"📄 Multiple PDF paths: {pdf_paths if pdf_paths else 'None'}")
        
        # 🔥 FIX: Handle multiple PDFs
        if (not context or len(str(context).strip()) < 10) and pdf_paths and len(pdf_paths) > 0:
            print(f"📚 Processing {len(pdf_paths)} PDF files...")
            all_texts = []
            
            for i, path in enumerate(pdf_paths):
                if path and os.path.exists(path):
                    print(f"📄 [{i+1}] Extracting: {os.path.basename(path)}")
                    text = extract_text_from_pdf_ocr(path)
                    if text and len(text) > 50:
                        all_texts.append(f"\n{'='*60}\n📁 FILE: {os.path.basename(path)}\n{'='*60}\n{text}")
                    else:
                        print(f"⚠️ No text extracted from {path}")
            
            if all_texts:
                context = "\n\n".join(all_texts)
                print(f"✅ Combined {len(all_texts)} PDFs, total {len(context)} chars")
            else:
                context = "No readable content found in uploaded PDF files."
        
        # Single PDF fallback
        elif (not context or len(str(context).strip()) < 10) and pdf_path and pdf_path.strip():
            if os.path.exists(pdf_path):
                print(f"🔄 Auto-extracting from PDF: {pdf_path}")
                context = extract_text_from_pdf_ocr(pdf_path)
                print(f"📊 Extracted text length: {len(context)} chars")
            else:
                context = "No document content available. Please upload a PDF file first."
        
        # No context at all
        elif not context or len(str(context).strip()) < 10:
            context = "No document content available. Please upload a PDF file first."
        
        # Ensure context is string
        if isinstance(context, dict):
            context = str(context)
        elif isinstance(context, list):
            context = " ".join(str(item) for item in context)
        else:
            context = str(context)
        
        print(f"📊 Final context length: {len(context)} characters")
        
        if len(context.strip()) < 50:
            return {
                "success": False,
                "agent_used": "document",
                "result": {
                    "content": "❌ Document content is too short or empty. Please upload a valid PDF file with text content."
                },
                "query": query,
                "document_length": len(context)
            }
        
        # Check if multiple files are present
        file_count = context.count("📁 FILE:")
        
        relevant_chunk = find_relevant_chunk(context, query, file_count)
        print(f"📊 Relevant chunk length: {len(relevant_chunk)} chars")
        
        is_summary_request = any(word in query.lower() for word in ["summarize", "summary", "summarise", "brief", "overview", "extract key points"])
        is_skills_request = any(word in query.lower() for word in ["skill", "technical", "resume", "experience", "qualification"])
        
        if is_summary_request:
            enhanced_prompt = f"""
            I have this document content:
            
            {context[:4000]}
            
            User is asking to: {query}
            
            IMPORTANT: Create a comprehensive summary using ONLY information from the document above.
            {'Include file names if multiple documents are present.' if file_count > 0 else ''}
            
            Summary:
            """
        else:
            enhanced_prompt = f"""
            I have this document content:
            
            {relevant_chunk}
            
            User is asking: {query}
            
            IMPORTANT RULES:
            1. You MUST answer ONLY using information from the document above
            2. If the information is not in the document, say "The document does not contain this information"
            3. Be specific and quote relevant parts if possible
            4. {'Specify which file contains the information when possible.' if file_count > 0 else ''}
            5. Don't make up answers
            
            Answer:
            """
        
        print(f"📊 Sending prompt to Gemini (length: {len(enhanced_prompt)} chars)")

        # 🔥 FIX: Convert history to string format if it's a list of dicts
        formatted_history = None
        if history:
            if isinstance(history, list):
                formatted_history = []
                for item in history:
                    if isinstance(item, dict):
                        role = item.get("role", "user")
                        content = item.get("content", "")
                        formatted_history.append(f"{role}: {content}")
                    else:
                        formatted_history.append(str(item))
            else:
                formatted_history = history

        response = brain.think(enhanced_prompt, formatted_history)
        return {
            "success": True,
            "agent_used": "document",
            "result": {
                "content": response
            },
            "query": query,
            "document_length": len(context),
            "file_count": file_count if file_count > 0 else 1,
            "summary_mode": is_summary_request
        }
        
    except Exception as e:
        print(f"❌ Document agent error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "agent_used": "document",
            "result": {
                "content": f"Document processing error: {str(e)}"
            },
            "error": str(e)
        }

def find_relevant_chunk(text, query, file_count=0):
    if not text or len(text) < 10:
        return "No relevant content found in document."
    
    # Better sentence splitting
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', text)
    results = []
    query_words = set(query.lower().split())
    
    question_words = {'what', 'why', 'when', 'where', 'who', 'how', 'is', 'are', 'was', 'were', 
                      'can', 'could', 'will', 'would', 'should', 'do', 'does', 'did', 'the', 'a', 'an'}
    query_words = query_words - question_words
    
    if not query_words:
        query_words = set(query.lower().split())
    
    print(f"🔍 Searching for: {query_words}")
    
    # Special boost for skill-related queries
    skill_boost = 2.0 if any(word in query.lower() for word in ['skill', 'technical', 'resume', 'experience']) else 1.0
    
    for i, s in enumerate(sentences):
        s_lower = s.lower().strip()
        if s_lower and len(s) > 20:
            s_words = set(s_lower.split())
            common = len(query_words.intersection(s_words))
            if common >= 1:
                # Boost score
                boost = skill_boost
                # Boost for sentences with bullet points (often skills)
                if '•' in s or '-' in s or '*' in s:
                    boost *= 1.5
                results.append((s, common * boost, i))
    
    results.sort(key=lambda x: x[1], reverse=True)
    
    # Take more chunks for multi-file
    top_chunks = [chunk[0] for chunk in results[:10]] if file_count > 1 else [chunk[0] for chunk in results[:7]]
    
    if top_chunks:
        result = " ".join(top_chunks)
        print(f"✅ Found {len(top_chunks)} relevant sentences")
        return result
    
    print("⚠️ No relevant sentences found, using first part of document")
    return text[:2000] if len(text) > 2000 else text

def _check_if_answer_found(response: str, query: str) -> bool:
    """Check if response actually contains an answer"""
    negative_indicators = [
        "not contain", "not found", "does not mention", "unable to find",
        "no information", "cannot find", "not in the document"
    ]
    
    response_lower = response.lower()
    query_lower = query.lower()
    
    # Check for negative indicators
    for indicator in negative_indicators:
        if indicator in response_lower:
            return False
    
    # Check if response contains query keywords
    query_words = set(query_lower.split())
    response_words = set(response_lower.split())
    common_words = query_words.intersection(response_words)
    
    return len(common_words) >= 2  # At least 2 common words

def extract_specific_answer(document_text: str, query: str) -> str:
    """
    Extract specific answer from document using text search
    """
    query_lower = query.lower()
    doc_lower = document_text.lower()
    
    # Look for normal distribution formula
    if "normal distribution" in query_lower and ("formula" in query_lower or "pdf" in query_lower):
        # Search for formula patterns
        formula_patterns = [
            r"f\(x\)\s*=\s*[^\\n]+",
            r"σ\s*=\s*[^\\n]+",
            r"μ\s*=\s*[^\\n]+",
            r"z\s*=\s*[^\\n]+",
            r"PDF\s*[:=]\s*[^\\n]+",
            r"probability density function\s*[:=]\s*[^\\n]+"
        ]
        
        for pattern in formula_patterns:
            matches = re.findall(pattern, document_text, re.IGNORECASE)
            if matches:
                return f"Found formula in document: {matches[0]}"
    
    # Look for definitions
    if "what is" in query_lower or "define" in query_lower:
        # Extract sentences containing the main term
        main_term = query_lower.replace("what is", "").replace("define", "").strip()
        sentences = re.split(r'[.!?]+', document_text)
        
        for sentence in sentences:
            if main_term in sentence.lower() and len(sentence) > 20:
                return sentence.strip()
    
    return ""  # Return empty if nothing found

def process(context: str, query: str, history: Optional[List] = None) -> Dict[str, Any]:
    """
    Alternative method for compatibility with router
    """
    return document_agent(context, query, history)