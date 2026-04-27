# agents/document_agent.py - IMPROVED VERSION

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
        print(f"📄 Context provided: {bool(context) and len(str(context)) > 10}")
        print(f"📄 Single PDF: {pdf_path if pdf_path else 'None'}")
        print(f"📄 Multiple PDFs: {len(pdf_paths) if pdf_paths else 0}")
        
        # ========== SECTION 1: EXTRACT TEXT FROM PDFS ==========
        extracted_context = ""
        
        # Priority 1: Multiple PDFs
        if pdf_paths and len(pdf_paths) > 0:
            print(f"📚 Processing {len(pdf_paths)} PDF files...")
            all_texts = []
            failed_pdfs = []
            
            for i, path in enumerate(pdf_paths):
                if path and os.path.exists(path):
                    print(f"📄 [{i+1}] Extracting: {os.path.basename(path)}")
                    text = extract_text_from_pdf_ocr(path)
                    
                    if text and len(text) > 50 and "❌" not in text and "No text" not in text:
                        file_header = f"""
┌{'─'*70}┐
│ 📁 FILE: {os.path.basename(path)}
│ 📅 Extracted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
│ 📊 Length: {len(text)} characters
└{'─'*70}┘
"""
                        all_texts.append(f"{file_header}\n{text}")
                        print(f"   ✅ Extracted {len(text)} chars")
                    else:
                        failed_pdfs.append(os.path.basename(path))
                        print(f"   ⚠️ Failed to extract from {os.path.basename(path)}")
            
            if all_texts:
                extracted_context = "\n\n".join(all_texts)
                print(f"✅ Successfully extracted {len(all_texts)}/{len(pdf_paths)} PDFs")
                if failed_pdfs:
                    print(f"⚠️ Failed PDFs: {failed_pdfs}")
            else:
                extracted_context = "❌ No readable content found in any uploaded PDF file."
        
        # Priority 2: Single PDF
        elif pdf_path and pdf_path.strip() and os.path.exists(pdf_path):
            print(f"🔄 Extracting from single PDF: {pdf_path}")
            extracted_context = extract_text_from_pdf_ocr(pdf_path)
            print(f"📊 Extracted text length: {len(extracted_context)} chars")
        
        # Priority 3: Use provided context
        elif context and len(str(context).strip()) > 10:
            extracted_context = str(context)
            print(f"📊 Using provided context: {len(extracted_context)} chars")
        
        # Priority 4: No content
        else:
            extracted_context = "No document content available. Please upload a PDF file."
        
        # ========== SECTION 2: VALIDATE CONTENT ==========
        if not extracted_context or len(extracted_context.strip()) < 50:
            return {
                "success": False,
                "agent_used": "document",
                "result": {
                    "content": "❌ Could not extract text from document. Please ensure:\n1. PDF is not corrupted\n2. PDF contains readable text (not just scanned images without OCR)\n3. File size is reasonable"
                },
                "query": query,
                "document_length": len(extracted_context) if extracted_context else 0
            }
        
        error_indicators = ["❌", "No text could be extracted", "Error extracting", "not found"]
        if any(indicator in extracted_context for indicator in error_indicators):
            return {
                "success": False,
                "agent_used": "document",
                "result": {
                    "content": extracted_context[:500]
                },
                "query": query,
                "document_length": len(extracted_context)
            }
        
        # ========== SECTION 2.5: STORE PDF IN FAISS ==========
        # 🔥 PDF extract hone ke baad FAISS mein store karo
        # Yeh ensure karta hai ki agli queries mein PDF ka data available rahe
                # ========== SECTION 2.5: STORE PDF IN FAISS (FIXED) ==========
        # 🔥 FIX: Pehle check karo already store hai ya nahi
        try:
            from memory.vector_store import add_pdf_to_index, is_pdf_in_index
            
            # 🔥 Create consistent ID based on content, not path
            import hashlib
            content_hash = hashlib.md5(extracted_context[:5000].encode()).hexdigest()
            pdf_id = f"pdf_{content_hash[:16]}"  # Consistent ID
            
            # 🔥 CRITICAL FIX: Check if already stored
            if not is_pdf_in_index(pdf_id):
                chunks_added = add_pdf_to_index(extracted_context, pdf_id)
                print(f"✅ New PDF stored in FAISS: {chunks_added} chunks (ID: {pdf_id})")
            else:
                print(f"⏭️ PDF already in FAISS, skipping storage (ID: {pdf_id})")
            
        except ImportError:
            print(f"⚠️ add_pdf_to_index not available")
        except Exception as e:
            print(f"⚠️ FAISS store failed: {e}")
        
        # ========== SECTION 3: ANALYZE QUERY TYPE ==========
        query_lower = query.lower()
        
        is_summary_request = any(word in query_lower for word in [
            "summarize", "summary", "summarise", "brief", "overview", 
            "extract key points", "gist", "tl;dr"
        ])
        
        is_question_request = any(word in query_lower for word in [
            "what", "why", "when", "where", "who", "how", "which",
            "tell me about", "explain", "describe"
        ])
        
        is_search_request = any(word in query_lower for word in [
            "find", "search", "look for", "where is", "contains"
        ])
        
        # Count files in context
        file_count = extracted_context.count("📁 FILE:")
        if file_count == 0 and extracted_context.count(".pdf") > 0:
            file_count = 1
        
        # ========== SECTION 4: FIND RELEVANT CHUNK ==========
        # 🔥 FAISS se relevant chunks try karo pehle
        faiss_chunk = ""
        try:
            from memory.vector_store import search_pdf
            
            if pdf_paths and len(pdf_paths) > 0:
                faiss_results = search_pdf(query, pdf_path=pdf_paths[0], top_k=8)
            elif pdf_path:
                faiss_results = search_pdf(query, pdf_path=pdf_path, top_k=8)
            else:
                faiss_results = search_pdf(query, top_k=8)
            
            if faiss_results and len(faiss_results) > 0:
                faiss_chunks = [r["text"] for r in faiss_results if r.get("text")]
                faiss_chunk = "\n\n".join(faiss_chunks)
                print(f"✅ FAISS returned {len(faiss_results)} relevant chunks ({len(faiss_chunk)} chars)")
            else:
                print(f"⚠️ FAISS returned no results, using keyword search")
                
        except ImportError:
            print(f"⚠️ search_pdf not available - using keyword search")
        except Exception as e:
            print(f"⚠️ FAISS search failed: {e} - falling back to keyword search")
        
        # Summary mode ya FAISS nahi mila toh keyword search
        if is_summary_request:
            relevant_chunk = extracted_context[:3500]
            print(f"📊 Summary mode - using first 3500 chars")
        elif faiss_chunk and len(faiss_chunk) > 100:
    # 🔥 Limit FAISS chunk to 3000 chars
            relevant_chunk = faiss_chunk[:3000]
            print(f"📊 Using FAISS chunk: {len(relevant_chunk)} chars (limited to 3000)")
        else:
            # Fallback: keyword-based search
            relevant_chunk = find_relevant_chunk(extracted_context, query, file_count)
            print(f"📊 Keyword search chunk: {len(relevant_chunk)} chars")
            
            if not relevant_chunk or len(relevant_chunk) < 50:
                relevant_chunk = extracted_context[:3000]
                print(f"⚠️ No relevant chunk, using first 3000 chars")
        
        # ========== SECTION 5: BUILD PROMPT ==========
        if is_summary_request:
            enhanced_prompt = f"""You are a document analysis expert. Based ONLY on the document(s) below, provide a comprehensive answer to the user's request.

{'='*60}
DOCUMENT CONTENT:
{'='*60}

{relevant_chunk}

{'='*60}
USER REQUEST: {query}
{'='*60}

INSTRUCTIONS:
1. Use ONLY information from the documents above
2. {'Mention which file each piece of information comes from' if file_count > 1 else ''}
3. Organize information clearly with bullet points if multiple items
4. If information is not in the documents, say "This information was not found in the document"
5. Be specific and quote relevant sections when possible

RESPONSE:"""
        
        elif is_question_request:
            enhanced_prompt = f"""You are a document Q&A expert. Answer the user's question using ONLY the document content provided.

{'='*60}
RELEVANT DOCUMENT SECTIONS:
{'='*60}

{relevant_chunk}

{'='*60}
USER QUESTION: {query}
{'='*60}

INSTRUCTIONS:
1. Answer ONLY based on the document content above
2. If the answer is not in the document, say "The document does not contain information about [topic]"
3. Quote specific parts of the document to support your answer
4. {'Specify which file contains the information' if file_count > 1 else ''}
5. Be concise but complete

ANSWER:"""
        
        else:
            enhanced_prompt = f"""You are a document analysis assistant. Respond to the user based ONLY on the document content.

{'='*60}
DOCUMENT CONTENT:
{'='*60}

{relevant_chunk}

{'='*60}
USER REQUEST: {query}
{'='*60}

INSTRUCTIONS:
1. Use ONLY information from the document above
2. If you cannot find the information, clearly state that
3. {'Reference file names when possible' if file_count > 1 else ''}
4. Do not add external knowledge or assumptions

RESPONSE:"""
        
        print(f"📊 Prompt length: {len(enhanced_prompt)} chars")
        print(f"📊 Files in context: {file_count}")
        print(f"📊 Query type: {'Summary' if is_summary_request else 'Question' if is_question_request else 'General'}")
        
        # ========== SECTION 6: GET RESPONSE FROM GEMINI ==========
                # ========== SECTION 6: GET RESPONSE FROM GEMINI ==========
        formatted_history = None
        if history:
            if isinstance(history, list):
                # Sirf last 2 messages lo
                limited_history = history[-2:] if len(history) > 2 else history  # ✅ Indent sahi karo
                formatted_history = []
                for item in limited_history:
                    if isinstance(item, dict):
                        role = item.get("role", "user")
                        content = item.get("content", "")[:500]
                        formatted_history.append(f"{role}: {content}")
                    else:
                        formatted_history.append(str(item)[:500])
            else:
                formatted_history = str(history)[:1000]  # ✅ Yeh sahi hai
        
        response = brain.think(enhanced_prompt, formatted_history)
        
        # ========== SECTION 7: VALIDATE RESPONSE ==========
        if not response or len(response.strip()) < 10:
            response = "I couldn't generate a proper response from the document. Please try rephrasing your question."
        
        no_info_indicators = ["does not contain", "not found", "no information", "cannot find", "not in the document"]
        if any(indicator in response.lower() for indicator in no_info_indicators):
            print("⚠️ Response indicates information not found in document")
        
        return {
            "success": True,
            "agent_used": "document",
            "result": {
                "content": response
            },
            "query": query,
            "document_length": len(extracted_context),
            "file_count": file_count if file_count > 0 else 1,
            "summary_mode": is_summary_request,
            "relevant_chunk_length": len(relevant_chunk)
        }
        
    except Exception as e:
        print(f"❌ Document agent error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "agent_used": "document",
            "result": {
                "content": f"Document processing error: {str(e)}. Please try again or upload a different PDF."
            },
            "error": str(e)
        }


def find_relevant_chunk(text: str, query: str, file_count: int = 0) -> str:
    if not text or len(text) < 10:
        return ""
    
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    if len(sentences) < 2:
        sentences = text.split('\n')
    
    results = []
    query_lower = query.lower()
    query_words = set(query_lower.split())
    
    stopwords = {'what', 'why', 'when', 'where', 'who', 'how', 'which', 'is', 'are', 'was', 'were', 
                 'can', 'could', 'will', 'would', 'should', 'do', 'does', 'did', 'the', 'a', 'an',
                 'and', 'or', 'but', 'for', 'nor', 'so', 'yet', 'of', 'to', 'in', 'for', 'on', 'with'}
    query_words = query_words - stopwords
    
    if not query_words:
        query_words = set(query_lower.split())
    
    print(f"🔍 Searching for keywords: {query_words}")
    
    is_skill_query = any(word in query_lower for word in ['skill', 'technical', 'experience', 'qualification', 'resume', 'all'])
    is_number_query = any(char.isdigit() for char in query_lower)
    boost_multiplier = 2.0 if is_skill_query else 1.5 if is_number_query else 1.0
    
    for i, sent in enumerate(sentences):
        sent_lower = sent.lower().strip()
        if len(sent) < 15:
            continue
        
        sent_words = set(sent_lower.split())
        common_words = query_words.intersection(sent_words)
        
        if common_words:
            score = len(common_words) * boost_multiplier
            
            if query_lower in sent_lower:
                score *= 2
            
            if any(marker in sent for marker in ['•', '-', '*', '✅', '📁']):
                score *= 1.5
            
            position_boost = 1.0 - (i / len(sentences)) * 0.5
            score *= position_boost
            
            results.append((sent, score, i))
    
    results.sort(key=lambda x: x[1], reverse=True)
    
    # 🔥 "all" query ke liye zyada chunks lo
    num_chunks = 20 if is_skill_query else 15 if file_count > 1 else 7
    
    if results:
        final_chunks = []
        used_indices = set()
        
        for chunk_text, _, idx in results[:num_chunks]:
            if idx not in used_indices:
                final_chunks.append(chunk_text)
                used_indices.add(idx)
                if idx + 1 < len(sentences) and idx + 1 not in used_indices:
                    final_chunks.append(sentences[idx + 1])
                    used_indices.add(idx + 1)
        
        result = " ".join(final_chunks)
        print(f"✅ Found {len(results[:num_chunks])} relevant sentences")
        return result
    
    print("⚠️ No relevant sentences found, using document beginning")
    return text[:3000]


def _check_if_answer_found(response: str, query: str) -> bool:
    negative_indicators = [
        "not contain", "not found", "does not mention", "unable to find",
        "no information", "cannot find", "not in the document",
        "does not have", "no mention", "doesn't contain"
    ]
    response_lower = response.lower()
    for indicator in negative_indicators:
        if indicator in response_lower:
            return False
    if len(response.strip()) < 20:
        return False
    query_words = set(query.lower().split())
    response_words = set(response_lower.split())
    return len(query_words.intersection(response_words)) >= 1


def extract_specific_answer(document_text: str, query: str) -> str:
    query_lower = query.lower()
    
    if "formula" in query_lower or "equation" in query_lower:
        formula_patterns = [
            r'[=][^.\n]*',
            r'f\(x\)[^.\n]*',
            r'[+\-*/=][^.\n]*',
            r'\b\w+\s*=\s*[^.\n]+'
        ]
        for pattern in formula_patterns:
            matches = re.findall(pattern, document_text, re.IGNORECASE)
            if matches:
                return f"Found in document: {matches[0]}"
    
    if "what is" in query_lower or "define" in query_lower:
        main_term = re.sub(r'(what is|define|the term|meaning of)', '', query_lower).strip()
        sentences = re.split(r'[.!?]+', document_text)
        for sentence in sentences:
            if main_term in sentence.lower() and len(sentence) > 20:
                if any(word in sentence.lower() for word in ['is', 'are', 'refers to', 'means', 'defined as']):
                    return sentence.strip()
    
    return ""


def process(context: str, query: str, history: Optional[List] = None) -> Dict[str, Any]:
    return document_agent(context, query, history)