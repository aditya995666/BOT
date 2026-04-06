from datetime import datetime
from memory.database import get_connection
from memory.vector_store import add_memory, search_similar
from sentence_transformers import SentenceTransformer, util
import re

from memory.vector_store import load_existing_memory
import threading

# ✅ Global flag to prevent multiple loads
_VECTOR_STORE_LOADED = False

def _safe_load_vector_store():
    """Load vector store only once"""
    global _VECTOR_STORE_LOADED
    if not _VECTOR_STORE_LOADED:
        load_existing_memory()
        _VECTOR_STORE_LOADED = True


class MemoryManager:
    def __init__(self):
        self.conn = get_connection()
        self._model = None
        _safe_load_vector_store()

    def _get_model(self):
        """Lazy load model to save memory"""
        if self._model is None:
            self._model = SentenceTransformer('all-MiniLM-L6-v2')
        return self._model

    # 🔥 UNIVERSAL STORE (COMPATIBLE WITH ALL AGENTS)
    def store(self, *args, **kwargs):
        """
        Universal memory store.

        Supports ALL formats:
        store(content)
        store(question, answer)
        store(content=..., source_agent=...)
        store(question=..., answer=...)
        """

        # --- Detect format ---
        if "content" in kwargs:
            text = kwargs["content"]

        elif "answer" in kwargs:
            text = kwargs["answer"]

        elif len(args) == 1:
            text = args[0]

        elif len(args) >= 2:
            # router format: store(question, answer)
            text = f"Q: {args[0]}\nA: {args[1]}"

        else:
            return

        source_agent = kwargs.get("source_agent", "unknown")
        content_type = kwargs.get("content_type", "text")
        confidence = kwargs.get("confidence", 0.8)

        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT INTO memory
            (content, source_agent, content_type, confidence_score, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            text,
            source_agent,
            content_type,
            confidence,
            datetime.now().isoformat()
        ))

        memory_id = cursor.lastrowid
        self.conn.commit()
        
        # 🔥 FAISS me store
        add_memory(text, memory_id)

    # 🔎 UNIVERSAL QUERY
    def query(self, text, top_k=5):
        """
        Universal query wrapper for Router + Agents.
        """
        try:
            results = search_similar(text, top_k)

            if not results:
                return None

            texts = []
            for r in results:
                if isinstance(r, dict):
                    texts.append(r.get("text") or r.get("content"))
                else:
                    texts.append(str(r))

            return "\n\n".join(texts)

        except Exception as e:
            print("Memory query error:", e)
            return None

    # 🔥 NEW METHOD: QUERY KNOWLEDGE
    def query_knowledge(self, question, top_k=5):
        """Specifically query stored knowledge chunks"""
        try:
            cursor = self.conn.cursor()
            
            results = search_similar(question, top_k)
            
            if not results:
                cursor.execute("""
                    SELECT content FROM memory 
                    WHERE content_type = 'knowledge' 
                    ORDER BY created_at DESC LIMIT 10
                """)
                rows = cursor.fetchall()
                if rows:
                    results = [{"text": row["content"], "similarity": 0.5} for row in rows]
            
            if not results:
                return None
            
            combined_text = " ".join([r["text"] for r in results[:3]])
            
            question_words = set(question.lower().split())
            sentences = re.split(r'[.!?]+', combined_text)
            
            best_sentence = ""
            best_score = 0
            
            for s in sentences:
                s = s.strip()
                if len(s) < 20:
                    continue
                s_words = set(s.lower().split())
                score = len(question_words & s_words)
                if score > best_score:
                    best_score = score
                    best_sentence = s
            
            if best_sentence:
                return best_sentence
            else:
                return results[0]["text"][:500] + "..."
                
        except Exception as e:
            print(f"❌ KNOWLEDGE QUERY ERROR: {e}")
            return None

    # 🔥 STORE KNOWLEDGE
    def store_knowledge(self, knowledge_text, source_agent="knowledge"):
        if not knowledge_text or len(knowledge_text.strip()) < 20:
            return False

        chunks = self.chunk_text(knowledge_text)
        cursor = self.conn.cursor()

        stored_ids = []
        for chunk in chunks:
            cursor.execute("""
                INSERT INTO memory
                (content, source_agent, content_type, confidence_score, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                chunk,
                source_agent,
                "knowledge",
                0.9,
                datetime.now().isoformat()
            ))

            memory_id = cursor.lastrowid
            stored_ids.append(memory_id)
            add_memory(chunk, memory_id)

        self.conn.commit()
        return True

    def chunk_text(self, text, chunk_size=300, overlap=50):
        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk.strip())
            start += chunk_size - overlap

        return chunks

    # 🔥 OLD NAME SUPPORT (Backward compatibility)
    def semantic_fetch(self, question, top_k=5):
        return self.query(question, top_k)