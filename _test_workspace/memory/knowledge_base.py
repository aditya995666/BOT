from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

model = SentenceTransformer("all-MiniLM-L6-v2")

knowledge_chunks = []
index = faiss.IndexFlatL2(384)


def chunk_text(text, chunk_size=200):
    words = text.split()
    chunks = []

    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i+chunk_size])
        chunks.append(chunk)

    return chunks


def add_knowledge(text):
    chunks = chunk_text(text)

    for chunk in chunks:
        emb = model.encode([chunk])
        index.add(np.array(emb).astype("float32"))
        knowledge_chunks.append(chunk)


def search_knowledge(query, top_k=3):
    emb = model.encode([query])
    D, I = index.search(np.array(emb).astype("float32"), top_k)

    results = []

    for idx in I[0]:
        if idx < len(knowledge_chunks):
            results.append(knowledge_chunks[idx])

    return "\n".join(results)