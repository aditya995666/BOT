# memory/vector_store.py
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

memory_loaded = False
model = SentenceTransformer("all-MiniLM-L6-v2")

DIM = 384
index = faiss.IndexFlatIP(DIM)

# memory store
memory_texts = []
memory_ids = []

def chunk_text(text, chunk_size=300):
    words = text.split()
    chunks = []

    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)

    return chunks

def add_memory(text: str, memory_id: int):
    if not isinstance(text, str):
        text = str(text)
    emb = model.encode([text], normalize_embeddings=True)
    index.add(np.array(emb).astype("float32"))
    memory_texts.append(text)
    memory_ids.append(memory_id)

def search_similar(query: str, top_k: int = 10):
    if index.ntotal == 0:
        return []
    
    q_emb = model.encode([query], normalize_embeddings=True)
    D, I = index.search(np.array(q_emb).astype("float32"), top_k)
    results = []
    SIM_THRESHOLD = 0.70
    
    for score, idx in zip(D[0], I[0]):
        if score >= SIM_THRESHOLD and idx != -1 and idx < len(memory_texts):
            results.append({
                "memory_id": memory_ids[idx],
                "text": memory_texts[idx],
                "similarity": float(score)
            })
    
    return results

def load_existing_memory():
    global memory_loaded
    if memory_loaded:
        return
    
    from memory.database import get_connection
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, content FROM memory ORDER BY id DESC")
        rows = cursor.fetchall()
        
        for r in rows:
            add_memory(r["content"], r["id"])
        
        memory_loaded = True
        conn.close()
    except Exception as e:
        pass