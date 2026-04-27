# memory/vector_store.py
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import threading
import time

class VectorStore:
    """SINGLETON CLASS - Only one instance of FAISS index and model"""
    
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
        print(f"🗄️ VECTOR STORE INITIALIZING")
        print(f"{'='*50}")
        start_time = time.time()
        
        print(f"🤖 Loading SentenceTransformer model 'all-MiniLM-L6-v2'...")
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        
        self.DIM = 384
        self.index = faiss.IndexFlatIP(self.DIM)
        self.memory_texts = []
        self.memory_ids = []
        self.memory_metadata = []
        self.memory_loaded = False
        
        self.pdf_chunks = {}
        self.pdf_chunk_indices = {}
        self.pdf_content_hashes = {}

        self._initialized = True
        elapsed = time.time() - start_time
        print(f"✅ VectorStore initialized in {elapsed:.2f}s")
        print(f"{'='*50}\n")
    
    def chunk_text(self, text, chunk_size=150):
        words = text.split()
        total_words = len(words)
        chunks = []
        overlap = 30
        print(f"📦 Chunking: {total_words} words → chunk_size={chunk_size}, overlap={overlap}")
        i = 0
        while i < total_words:
            chunk = " ".join(words[i:i + chunk_size])
            chunks.append(chunk)
            i += (chunk_size - overlap)
        print(f"✅ Created {len(chunks)} overlapping chunks")
        return chunks
    
    def add_memory(self, text: str, memory_id: int, metadata: dict = None):
        """Add a single memory to FAISS index"""
        if not isinstance(text, str):
            text = str(text)
        if not text.strip():
            return
            
        text_preview = text[:80].replace('\n', ' ')
        print(f"📝 [ADD] ID {memory_id}: '{text_preview}...'")
        
        emb = self.model.encode([text], normalize_embeddings=True)
        self.index.add(np.array(emb).astype("float32"))
        self.memory_texts.append(text)
        self.memory_ids.append(memory_id)
        self.memory_metadata.append(metadata or {})
        
        print(f"✅ [ADD] ID {memory_id} added. Total vectors: {self.index.ntotal}")
    
    def add_pdf_to_index(self, pdf_text: str, pdf_path: str = "uploaded_pdf") -> int:
        import hashlib
        
        if not pdf_text or len(pdf_text.strip()) < 50:
            print("⚠️ [PDF] Empty or too short text, skipping FAISS store")
            return 0
        
        print(f"\n{'='*50}")
        print(f"📄 STORING PDF IN FAISS: {pdf_path}")
        print(f"{'='*50}")
        
        content_hash = hashlib.md5(pdf_text[:5000].encode()).hexdigest()
        pdf_id = f"pdf_{content_hash[:16]}"
        
        if pdf_id in self.pdf_chunks:
            print(f"⏭️ PDF already in FAISS by content (ID: {pdf_id})")
            return len(self.pdf_chunks[pdf_id])
        
        if pdf_path in self.pdf_chunks:
            print(f"⏭️ PDF already in FAISS by path: {pdf_path}")
            return len(self.pdf_chunks[pdf_path])
        
        chunks = self.chunk_text(pdf_text, chunk_size=150)
        if not chunks:
            print("⚠️ No chunks created from PDF text")
            return 0
        
        print(f"🔢 Generating embeddings for {len(chunks)} chunks...")
        emb_start = time.time()
        try:
            embeddings = self.model.encode(chunks, normalize_embeddings=True, batch_size=32)
            print(f"✅ Embeddings generated in {time.time() - emb_start:.2f}s")
        except Exception as e:
            print(f"❌ Embedding failed: {e}")
            return 0
        
        start_idx = self.index.ntotal
        self.index.add(np.array(embeddings).astype("float32"))
        chunk_indices = list(range(start_idx, self.index.ntotal))
        
        self.pdf_chunks[pdf_id] = chunks
        self.pdf_chunk_indices[pdf_id] = chunk_indices
        self.pdf_content_hashes[content_hash] = pdf_path
        
        for i, chunk in enumerate(chunks):
            self.memory_texts.append(chunk)
            self.memory_ids.append(-(i + 1))
            self.memory_metadata.append({
                "source": "pdf",
                "pdf_path": pdf_path,
                "pdf_id": pdf_id,
                "content_hash": content_hash,
                "chunk_index": i,
                "total_chunks": len(chunks)
            })
        
        print(f"✅ PDF stored: {len(chunks)} chunks | Total vectors: {self.index.ntotal}")
        return len(chunks)
    
    def search_similar(self, query: str, top_k: int = 10, source_filter: str = None):
        """
        Search with SOURCE PRIORITY:
          1. web     ← website crawl (HIGHEST)
          2. pdf     ← uploaded docs
          3. youtube / github
          4. unknown ← old DB records / AI responses (LOWEST)
        """
        print(f"🔎 [SEARCH] Query: '{query[:80]}' (top_k={top_k})")
        
        if self.index.ntotal == 0:
            print(f"⚠️ [SEARCH] Index is empty")
            return []
        
        q_emb = self.model.encode([query], normalize_embeddings=True)
        fetch_k = min(top_k * 5, self.index.ntotal)
        D, I = self.index.search(np.array(q_emb).astype("float32"), fetch_k)
        
        SIM_THRESHOLD = 0.20
        
        # ── Bucket by source ──────────────────────────
        buckets = {"web": [], "pdf": [], "other": [], "unknown": []}
        
        for score, idx in zip(D[0], I[0]):
            if idx == -1 or idx >= len(self.memory_texts):
                continue
            if score < SIM_THRESHOLD:
                continue
            
            metadata = self.memory_metadata[idx] if idx < len(self.memory_metadata) else {}
            source = metadata.get("source", "unknown")
            
            result = {
                "memory_id": self.memory_ids[idx],
                "text": self.memory_texts[idx],
                "similarity": float(score),
                "metadata": metadata,
                "source": source,
                "is_pdf": source == "pdf"
            }
            
            if source == "web":
                buckets["web"].append(result)
            elif source == "pdf":
                buckets["pdf"].append(result)
            elif source in ("youtube", "github"):
                buckets["other"].append(result)
            else:
                # Old AI responses / unknown — lowest priority
                buckets["unknown"].append(result)
        
        # ── Apply source_filter or priority-merge ────
        if source_filter == "web":
            results = buckets["web"]
        elif source_filter == "pdf":
            results = buckets["pdf"]
        elif source_filter == "youtube":
            results = [r for r in buckets["other"] if r["source"] == "youtube"]
        elif source_filter == "github":
            results = [r for r in buckets["other"] if r["source"] == "github"]
        else:
            # 🔥 Priority order: web → pdf → other → unknown (last resort)
            results = buckets["web"] + buckets["pdf"] + buckets["other"] + buckets["unknown"]
        
        # Sort within priority groups by similarity
        results = results[:top_k]
        
        print(f"✅ [SEARCH] Found {len(results)} results (threshold={SIM_THRESHOLD})")
        print(f"   Buckets → web:{len(buckets['web'])} pdf:{len(buckets['pdf'])} "
              f"other:{len(buckets['other'])} unknown:{len(buckets['unknown'])}")
        for i, r in enumerate(results[:3]):
            print(f"   Result {i+1}: similarity={r['similarity']:.4f}, source={r['source']}")
        
        return results
    
    def search_pdf(self, query: str, pdf_path: str = None, top_k: int = 10):
        print(f"🔎 [PDF SEARCH] Query: '{query[:80]}'")
        if self.index.ntotal == 0:
            return []
        
        q_emb = self.model.encode([query], normalize_embeddings=True)
        fetch_k = min(top_k * 5, self.index.ntotal)
        D, I = self.index.search(np.array(q_emb).astype("float32"), fetch_k)
        
        results = []
        SIM_THRESHOLD = 0.25
        seen_hashes = set()
        
        for score, idx in zip(D[0], I[0]):
            if idx == -1 or idx >= len(self.memory_texts):
                continue
            if score < SIM_THRESHOLD:
                continue
            
            metadata = self.memory_metadata[idx] if idx < len(self.memory_metadata) else {}
            if metadata.get("source") != "pdf":
                continue
            
            if pdf_path:
                stored_path = metadata.get("pdf_path", "")
                stored_id = metadata.get("pdf_id", "")
                if pdf_path != stored_path and pdf_path != stored_id:
                    continue
            
            content_hash = metadata.get("content_hash", "")
            if content_hash and content_hash in seen_hashes:
                continue
            if content_hash:
                seen_hashes.add(content_hash)
            
            results.append({
                "text": self.memory_texts[idx],
                "similarity": float(score),
                "chunk_index": metadata.get("chunk_index", 0),
                "pdf_path": metadata.get("pdf_path", "unknown"),
                "pdf_id": metadata.get("pdf_id", ""),
            })
            
            if len(results) >= top_k:
                break
        
        results.sort(key=lambda x: x["similarity"], reverse=True)
        print(f"✅ [PDF SEARCH] Found {len(results)} unique PDF chunks")
        return results

    def load_existing_memory(self):
        if self.memory_loaded:
            print(f"ℹ️ Vector store already loaded ({len(self.memory_texts)} vectors)")
            return
        
        print(f"\n{'='*50}")
        print(f"📚 LOADING EXISTING MEMORY")
        print(f"{'='*50}")
        load_start = time.time()
        
        from memory.database import get_connection
        
        try:
            conn = get_connection()
            cursor = conn.cursor()

            # ✅ FIX 1: content_type aur source_agent bhi fetch karo
            cursor.execute("""
                SELECT id, content, source_agent, content_type
                FROM memory
                ORDER BY id DESC
            """)
            rows = cursor.fetchall()
            print(f"✅ Fetched {len(rows)} records from DB")
            
            skipped = 0
            loaded = 0
            for idx, r in enumerate(rows):
                content      = r["content"]
                source_agent = r["source_agent"] or "unknown"
                content_type = r["content_type"] or "text"

                # ✅ FIX 2: Purani AI responses / garbage skip karo
                #    Jo records "ai response" ya "bot answer" type ke hain unhe
                #    load mat karo — warna search mein garbage aata hai
                SKIP_AGENTS = {"document", "pdf", "knowledge_memory"}
                SKIP_TYPES  = {"ai_response", "bot_response", "assistant_response"}

                if source_agent in SKIP_AGENTS or content_type in SKIP_TYPES:
                    skipped += 1
                    continue

                # ✅ FIX 3: source map karo properly
                # content_type se source derive karo
                source_map = {
                    "website":  "web",
                    "web":      "web",
                    "youtube":  "youtube",
                    "github":   "github",
                    "pdf":      "pdf",
                    "knowledge":"knowledge",
                }
                source = source_map.get(content_type, "unknown")

                # ✅ FIX 4: Metadata ke saath load karo
                metadata = {
                    "source":       source,
                    "source_agent": source_agent,
                    "content_type": content_type,
                    "db_id":        r["id"],
                }

                self.add_memory(content, r["id"], metadata=metadata)
                loaded += 1

                if (idx + 1) % 100 == 0:
                    print(f"   Progress: {idx + 1}/{len(rows)}")
            
            self.memory_loaded = True
            elapsed = time.time() - load_start
            print(f"✅ LOAD COMPLETE: {loaded} loaded, {skipped} skipped in {elapsed:.2f}s")
            print(f"{'='*50}\n")
            
        except Exception as e:
            print(f"❌ Failed to load existing memory: {e}")
            self.memory_loaded = True


# ── Global instance ───────────────────────────────────────────
_vector_store = None

def get_vector_store():
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store

# Backward compatibility exports
def chunk_text(text, chunk_size=150):
    return get_vector_store().chunk_text(text, chunk_size)

def add_memory(text: str, memory_id: int, metadata: dict = None):
    return get_vector_store().add_memory(text, memory_id, metadata)

def search_similar(query: str, top_k: int = 10, source_filter: str = None):
    return get_vector_store().search_similar(query, top_k, source_filter)

def load_existing_memory():
    return get_vector_store().load_existing_memory()

def add_pdf_to_index(pdf_text: str, pdf_path: str = "uploaded_pdf") -> int:
    return get_vector_store().add_pdf_to_index(pdf_text, pdf_path)

def search_pdf(query: str, pdf_path: str = None, top_k: int = 10):
    return get_vector_store().search_pdf(query, pdf_path, top_k)