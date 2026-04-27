# memory/memory_manager.py
from datetime import datetime
from memory.database import get_connection, init_db
from memory.vector_store import add_memory, search_similar
from sentence_transformers import SentenceTransformer
import re
import threading
import time

from memory.vector_store import load_existing_memory

_VECTOR_STORE_LOADED = False


class MemoryManager:
    """SINGLETON CLASS - Only one instance exists"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        print(f"\n{'='*50}")
        print(f"🧠 MEMORY MANAGER INITIALIZING")
        print(f"{'='*50}")
        start_time = time.time()
        
        self._model = None
        self._init_db_once()
        self._safe_load_vector_store()
        
        elapsed = time.time() - start_time
        print(f"✅ MemoryManager initialized in {elapsed:.2f}s")
        print(f"{'='*50}\n")
        self._initialized = True
    
    def _init_db_once(self):
        print(f"📂 Initializing database...")
        init_db()
        print(f"✅ Database ready")
    
    def _safe_load_vector_store(self):
        global _VECTOR_STORE_LOADED
        if not _VECTOR_STORE_LOADED:
            print(f"📚 Loading vector store...")
            start_time = time.time()
            load_existing_memory()
            elapsed = time.time() - start_time
            print(f"✅ Vector store loaded in {elapsed:.2f}s")
            _VECTOR_STORE_LOADED = True

    def _get_model(self):
        if self._model is None:
            self._model = SentenceTransformer('all-MiniLM-L6-v2')
        return self._model

    # ─────────────────────────────────────────────
    # 🔥 UNIVERSAL STORE — FIXED: metadata pass karo
    # ─────────────────────────────────────────────
    def store(self, *args, **kwargs):
        """Universal memory store"""
        store_start = time.time()
        try:
            source_agent = kwargs.get("source_agent", "unknown")
            content_type = kwargs.get("content_type", "text")
            
            # Document/PDF answers store nahi karo
            if source_agent in ["document", "pdf", "knowledge_memory"]:
                print(f"⏭️ [STORE] Skipping - document/pdf answers not stored in memory")
                return

            # Format detect karo
            if "content" in kwargs:
                text = kwargs["content"]
            elif "answer" in kwargs:
                text = kwargs["answer"]
            elif len(args) == 1:
                text = args[0]
            elif len(args) >= 2:
                text = f"Q: {args[0]}\nA: {args[1]}"
            else:
                print(f"⚠️ Store: No valid format")
                return

            confidence = kwargs.get("confidence", 0.8)
            
            text_preview = text[:100].replace('\n', ' ')
            print(f"📝 [STORE] Agent: {source_agent}, Type: {content_type}")
            print(f"   Preview: {text_preview}...")

            conn = get_connection()
            cursor = conn.cursor()
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
            conn.commit()

            # ✅ FIX: source map karo aur metadata pass karo
            source_map = {
                "website": "web",
                "web":     "web",
                "youtube": "youtube",
                "github":  "github",
                "pdf":     "pdf",
            }
            source = source_map.get(content_type, "unknown")

            metadata = {
                "source":       source,
                "source_agent": source_agent,
                "content_type": content_type,
                "db_id":        memory_id,
            }

            add_memory(text, memory_id, metadata=metadata)  # ✅ metadata pass karo
            
            elapsed = time.time() - store_start
            print(f"✅ [STORE] ID {memory_id} | source={source} stored in {elapsed:.3f}s")
            
        except Exception as e:
            print(f"❌ [STORE] Error: {e}")

    # ─────────────────────────────────────────────
    # 🔎 QUERY KNOWLEDGE — FIXED: web priority add
    # ─────────────────────────────────────────────
    def query_knowledge(self, question, top_k=5):
        """Query stored knowledge — web > pdf > others > unknown"""
        query_start = time.time()
        print(f"📚 [KNOWLEDGE_QUERY] Question: '{question[:80]}'")
        
        if len(question.strip()) < 5:
            return None
            
        greetings = ['hi', 'hello', 'hey', 'namaste', 'good morning', 'good evening', 
                     'hello bro', 'hi bro', 'hey bro', 'kaise ho', 'kya haal']
        if question.lower().strip() in greetings:
            return None
        
        try:
            results = search_similar(question, top_k * 2)
            
            if not results:
                print(f"⚠️ No FAISS results, SQL fallback...")
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT content, content_type FROM memory 
                    WHERE source_agent NOT IN ('document', 'pdf')
                    ORDER BY created_at DESC LIMIT 5
                """)
                rows = cursor.fetchall()
                if rows:
                    results = [{
                        "text": row["content"],
                        "similarity": 0.5,
                        "metadata": {"source": row["content_type"] or "unknown"},
                        "source": row["content_type"] or "unknown"
                    } for row in rows]
                else:
                    return None
            
            # ✅ FIX: web + pdf + other + unknown — priority order
            bucket_web     = []
            bucket_pdf     = []
            bucket_other   = []
            bucket_unknown = []

            for r in results:
                metadata = r.get("metadata", {})
                # search_similar returns "source" key directly now
                source = r.get("source") or metadata.get("source", "unknown")
                
                if source == "web":
                    bucket_web.append(r)
                elif source == "pdf":
                    bucket_pdf.append(r)
                elif source in ("youtube", "github", "knowledge"):
                    bucket_other.append(r)
                else:
                    bucket_unknown.append(r)

            # Priority: web > pdf > other > unknown
            sorted_results = bucket_web + bucket_pdf + bucket_other + bucket_unknown
            
            print(f"   Priority → web:{len(bucket_web)} pdf:{len(bucket_pdf)} "
                  f"other:{len(bucket_other)} unknown:{len(bucket_unknown)}")

            if not sorted_results:
                return None
            
            # ✅ Unknown-only results hain toh return mat karo
            # (yeh purani AI responses hain, not actual knowledge)
            if not bucket_web and not bucket_pdf and not bucket_other:
                print(f"⚠️ Only unknown/garbage results found — skipping")
                return None

            top_results = sorted_results[:top_k]
            
            combined_chunks = []
            for r in top_results:
                chunk_text = r.get("text", "")
                if chunk_text and len(chunk_text.strip()) > 20:
                    combined_chunks.append(chunk_text.strip())
            
            if not combined_chunks:
                return None
            
            combined_answer = "\n\n".join(combined_chunks)
            
            elapsed = time.time() - query_start
            print(f"✅ [KNOWLEDGE_QUERY] Returning {len(combined_chunks)} chunks "
                  f"({len(combined_answer)} chars) in {elapsed:.3f}s")
            
            return combined_answer
                
        except Exception as e:
            elapsed = time.time() - query_start
            error_str = str(e).lower()
            if "closed" in error_str:
                print(f"🔄 Retrying after closed DB...")
                return self.query_knowledge(question, top_k)
            print(f"❌ [KNOWLEDGE_QUERY] Error: {e}")
            return None

    # ─────────────────────────────────────────────
    # 🔥 UNIVERSAL QUERY
    # ─────────────────────────────────────────────
    def query(self, text, top_k=5):
        query_start = time.time()
        try:
            results = search_similar(text, top_k)
            if not results:
                return None
            texts = []
            for r in results:
                if isinstance(r, dict):
                    texts.append(r.get("text") or r.get("content", ""))
                else:
                    texts.append(str(r))
            print(f"✅ [QUERY] Found {len(results)} results in {time.time()-query_start:.3f}s")
            return "\n\n".join(texts)
        except Exception as e:
            print(f"❌ [QUERY] Error: {e}")
            return None

    # ─────────────────────────────────────────────
    # 🔥 STORE KNOWLEDGE
    # ─────────────────────────────────────────────
    def store_knowledge(self, knowledge_text, source_agent="knowledge"):
        store_start = time.time()
        if not knowledge_text or len(knowledge_text.strip()) < 20:
            print(f"⚠️ [STORE_KNOWLEDGE] Too short, skipping")
            return False

        chunks = self.chunk_text_by_words(knowledge_text)
        print(f"📝 [STORE_KNOWLEDGE] Source: {source_agent}, Chunks: {len(chunks)}")
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            stored_ids = []
            
            for idx, chunk in enumerate(chunks):
                if not chunk.strip():
                    continue
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

                # ✅ FIX: metadata pass karo
                add_memory(chunk, memory_id, metadata={
                    "source": "knowledge",
                    "source_agent": source_agent,
                    "content_type": "knowledge",
                    "db_id": memory_id,
                })
                
                if (idx + 1) % 10 == 0:
                    print(f"   Stored {idx + 1}/{len(chunks)} chunks...")

            conn.commit()
            elapsed = time.time() - store_start
            print(f"✅ [STORE_KNOWLEDGE] {len(stored_ids)} chunks in {elapsed:.2f}s")
            return True
            
        except Exception as e:
            print(f"❌ [STORE_KNOWLEDGE] Error: {e}")
            return False

    def chunk_text_by_words(self, text, chunk_size=150, overlap=30):
        words = text.split()
        chunks = []
        i = 0
        while i < len(words):
            chunk = " ".join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)
            i += (chunk_size - overlap)
        print(f"✅ Word-chunked: {len(words)} words → {len(chunks)} chunks")
        return chunks

    def chunk_text(self, text, chunk_size=300, overlap=50):
        return self.chunk_text_by_words(text, chunk_size=150, overlap=30)

    def semantic_fetch(self, question, top_k=5):
        return self.query(question, top_k)

    def store_conversation_context(self, session_id: str, key: str, value: str):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_context (
                    session_id TEXT,
                    context_key TEXT,
                    context_value TEXT,
                    updated_at TEXT,
                    PRIMARY KEY (session_id, context_key)
                )
            """)
            cursor.execute("""
                INSERT OR REPLACE INTO conversation_context
                (session_id, context_key, context_value, updated_at)
                VALUES (?, ?, ?, ?)
            """, (session_id, key, value, datetime.now().isoformat()))
            conn.commit()
            print(f"📝 [CONTEXT] Stored '{key}' for session {session_id}")
            return True
        except Exception as e:
            print(f"❌ [CONTEXT] Error: {e}")
            return False

    def get_conversation_context(self, session_id: str, key: str):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT context_value FROM conversation_context
                WHERE session_id = ? AND context_key = ?
            """, (session_id, key))
            row = cursor.fetchone()
            return row["context_value"] if row else None
        except Exception as e:
            print(f"❌ [CONTEXT] Error: {e}")
            return None

    def get_last_shared_code(self, session_id: str):
        return self.get_conversation_context(session_id, "last_code")

    def update_last_shared_code(self, session_id: str, code: str):
        return self.store_conversation_context(session_id, "last_code", code)

    def is_healthy(self):
        try:
            get_connection().cursor().execute("SELECT 1")
            return True
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False


print(f"\n🚀 Creating MemoryManager global instance...")
memory_manager = MemoryManager()