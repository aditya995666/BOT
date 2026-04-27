import requests
import os
import re
import tempfile
import threading
import queue
import time
from git import Repo
from pypdf import PdfReader
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from youtube_transcript_api import YouTubeTranscriptApi
from datetime import datetime

MAX_PAGES = 15


class URLProcessor:
    def __init__(self):
        self.url_queue = queue.Queue()
        self.processed_urls = set()
        self.processing = True
        self.worker_thread = None
        self.start_worker()

    def start_worker(self):
        self.worker_thread = threading.Thread(target=self._process_loop, daemon=True)
        self.worker_thread.start()
        print("🔄 Auto-URL Processor started")

    def add_url(self, url, user_query=""):
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        if url in self.processed_urls:
            print(f"⏭️ URL already processed: {url}")
            return False
        self.url_queue.put({
            'url': url,
            'query': user_query,
            'timestamp': datetime.now()
        })
        print(f"📥 URL added to queue: {url}")
        return True

    def _process_loop(self):
        print("🔄 URL Processor worker thread started")
        while self.processing:
            try:
                item = self.url_queue.get(timeout=2)
                url = item['url']
                print(f"\n{'='*50}\n🔄 [BACKGROUND] Processing: {url}\n{'='*50}")
                start_time = time.time()
                result = train_website_background(url)
                elapsed = time.time() - start_time
                if result.get('success'):
                    self.processed_urls.add(url)
                    print(f"✅ [BACKGROUND] Done {url} in {elapsed:.2f}s — {result.get('chunks', 0)} chunks")
                else:
                    print(f"❌ [BACKGROUND] Failed {url}: {result.get('content', 'Unknown')}")
                self.url_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ URL Processor error: {e}")

    def is_processed(self, url):
    # www.difmo.com aur difmo.com ko same maano
        def normalize(u):
            return urlparse(u).netloc.replace("www.", "").rstrip("/")
        
        input_domain = normalize(url)
        for processed_url in self.processed_urls:
            if normalize(processed_url) == input_domain:
                return True
        return False
    def get_status(self):
        return {
            "processed_count": len(self.processed_urls),
            "queue_size": self.url_queue.qsize()
        }

url_processor = URLProcessor()

_last_processed_url = None
_active_url = None
# ─────────────────────────────────────────────
# 🌐 WEB AGENT
# ─────────────────────────────────────────────
class WebAgent:
    def __init__(self):
        self.visited = set()
        print("✅ WebAgent initialized")

    def fetch_page(self, url):
        print(f"   🌐 Fetching: {url[:80]}...")
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(url, headers=headers, timeout=15)
            print(f"      ✅ Status: {r.status_code}")
            return r.text
        except Exception as e:
            print(f"      ❌ Failed: {e}")
            return ""

    def extract_text(self, html):
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = " ".join(soup.get_text(separator=" ").split())
        print(f"      ✅ Extracted {len(text)} chars")
        return text

    def get_links(self, html, base_url):
        soup = BeautifulSoup(html, "html.parser")
        links = set()
        base_domain = urlparse(base_url).netloc
        for a in soup.find_all("a", href=True):
            link = urljoin(base_url, a["href"])
            if urlparse(link).netloc.endswith(base_domain):
                links.add(link)
        return links

    def crawl(self, start_url):
        print(f"\n{'='*50}\n🕷️ CRAWLING: {start_url}\n{'='*50}")
        start_time = time.time()
        self.visited = set()
        to_visit = [start_url]
        collected_text = ""
        pages_crawled = 0

        while to_visit and len(self.visited) < MAX_PAGES:
            url = to_visit.pop(0)
            if url in self.visited:
                continue
            pages_crawled += 1
            print(f"\n📄 [{pages_crawled}/{MAX_PAGES}] {url[:80]}...")
            self.visited.add(url)
            html = self.fetch_page(url)
            if not html:
                continue
            text = self.extract_text(html)
            collected_text += "\n\n" + text[:3000]
            to_visit.extend(list(self.get_links(html, url)))

        elapsed = time.time() - start_time
        print(f"✅ Crawl complete: {pages_crawled} pages, {len(collected_text)} chars in {elapsed:.2f}s")
        return collected_text

web_agent = WebAgent()


# ─────────────────────────────────────────────
# 📦 FAISS STORAGE
# ─────────────────────────────────────────────
def store_website_in_faiss(url: str, content: str):
    try:
        from memory.vector_store import add_memory
        import hashlib

        words = content.split()
        chunks = [" ".join(words[i:i+300]) for i in range(0, len(words), 200)]
        print(f"📦 Storing {len(chunks)} chunks in FAISS...")

        stored = 0
        for i, chunk in enumerate(chunks):
            clean_chunk = chunk.strip()
            chunk_hash = hashlib.md5(f"{url}_{i}_{chunk[:100]}".encode()).hexdigest()
            memory_id = int(chunk_hash[:8], 16) % 1000000
            add_memory(
                text=clean_chunk,
                memory_id=memory_id,
                metadata={
                    "source": "web",
                    "url": url,
                    "chunk_index": i,
                    "type": "website_content",
                    "timestamp": datetime.now().isoformat()
                }
            )
            stored += 1
            if (i + 1) % 20 == 0:
                print(f"   Stored {stored}/{len(chunks)} chunks in FAISS...")

        print(f"✅ FAISS: Stored {stored} chunks for {url}")
        return stored
    except Exception as e:
        print(f"❌ FAISS store error: {e}")
        return 0


# ─────────────────────────────────────────────
# 🔧 BACKGROUND TRAINING
# ─────────────────────────────────────────────
def train_website_background(url):
    print(f"\n🔧 [BACKGROUND] Training on: {url}")
    try:
        website_text = web_agent.crawl(url)
        if not website_text or len(website_text.strip()) < 100:
            return {"success": False, "content": "Insufficient content"}

        faiss_stored = store_website_in_faiss(url, website_text)
        print(f"✅ [BACKGROUND] FAISS: {faiss_stored} chunks stored for {url}")
        return {"success": True, "content": f"Stored {faiss_stored} chunks", "chunks": faiss_stored}
    except Exception as e:
        print(f"❌ [BACKGROUND] Error: {e}")
        return {"success": False, "content": str(e)}

# ========== PUBLIC API FOR ROUTER ==========
def train_website(url):
    """Train website - Main entry point for router"""
    return train_website_background(url)
# ─────────────────────────────────────────────
# 🌐 URL DETECTION HELPER
# ─────────────────────────────────────────────
def process_url_if_present(text):
    global _last_processed_url, _active_url  # 🔥 _active_url add karo
    url_pattern = r'https?://[^\s]+|www\.[^\s]+'
    urls = re.findall(url_pattern, text)
    if urls:
        for url in urls:
            print(f"🔍 Auto-detected URL: {url}")
            url_processor.add_url(url, text)
        _last_processed_url = urls[0]
        _active_url = urls[0]  # 🔥 Yeh add karo
        print(f"🎯 Active URL set: {_active_url}")
        return True, urls[0]
    return False, None
def get_active_url():
    return _active_url  # 🔥 Router yeh use karega

def is_url_processed(url):
    return url_processor.is_processed(url)

def get_auto_processor_status():
    return url_processor.get_status()


# ─────────────────────────────────────────────
# 🔎 ASK FROM LEARNED DATA  ← MAIN FIX HERE
# ─────────────────────────────────────────────
# ─────────────────────────────────────────────
# 🔎 ASK FROM LEARNED DATA WITH AI SUMMARIZATION
# ─────────────────────────────────────────────
# ─────────────────────────────────────────────
# 🔎 ASK FROM LEARNED DATA WITH AI SUMMARIZATION
# ─────────────────────────────────────────────
def ask_knowledge(question):
    global _last_processed_url, _active_url
    start_time = time.time()

    target_url = _active_url
    if not target_url:
        return "⚠️ Pehle koi URL share karo!"

    print(f"🔗 Active URL: {target_url}")

    if not url_processor.is_processed(target_url):
        return f"⏳ Abhi **{target_url}** seekh raha hoon... 15-20 second baad poocho!"

    try:
        from memory.vector_store import search_similar
        from brain.gemini_llm import GeminiBrain
        
        brain = GeminiBrain()
        
        # 🔥 FIX: Remove source_filter to get ALL results
        faiss_results = search_similar(question, top_k=10)  # ← No source_filter
        
        if faiss_results:
            # Try to find chunks related to active URL
            target_domain = urlparse(target_url).netloc.replace("www.", "")
            
            # First try: URL-specific chunks
            url_results = [
                r for r in faiss_results
                if target_domain in str(r.get("metadata", {}).get("url", ""))
            ]
            
            # Second try: Any chunks that are not garbage
            if not url_results:
                url_results = [
                    r for r in faiss_results
                    if r.get("text") and len(r.get("text", "")) > 100
                    and not any(g in r.get("text", "") for g in ["Please install", "still learning", "abhi load"])
                ]
            
            print(f"✅ Found {len(url_results)} usable chunks")
            
            if url_results:
                # Extract text from chunks
                texts = []
                for r in url_results[:5]:
                    raw = r.get("text", "") or r.get("content", "")
                    if raw and len(raw) > 100:
                        cleaned = _clean_content(raw)
                        if cleaned and len(cleaned) > 50:
                            texts.append(cleaned)
                
                if texts:
                    combined_text = "\n\n".join(texts)
                    
                    # Use AI to answer
                    prompt = f"""Based ONLY on the following website content, answer the user's question.

USER QUESTION: {question}

WEBSITE CONTENT:
{combined_text[:3000]}

INSTRUCTIONS:
1. Answer based ONLY on the content above
2. If specific dates/numbers are mentioned, use them
3. If information not found, say "Information not available"
4. Keep answer concise (7,8 sentences)

ANSWER:"""
                    
                    answer = brain.think(prompt)
                    return f"📚 **Answer:**\n\n{answer}"
        
        return f"⚠️ No information found for: {question}"
        
    except Exception as e:
        print(f"⚠️ ask_knowledge error: {e}")
        return f"❌ Error: {str(e)}"
def _extract_texts(results):
    """Helper: extract and clean text from FAISS results"""
    texts = []
    for r in results:
        raw = r.get("text", "") or r.get("content", "")
        if raw:
            cleaned = _clean_content(raw)
            if cleaned and len(cleaned) > 30:
                texts.append(cleaned)
    return texts


# ─────────────────────────────────────────────
# 🧹 CONTENT CLEANER
# ─────────────────────────────────────────────
def _clean_content(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'^Source:\s*https?://\S+\s*\n+', '', text, flags=re.MULTILINE)
    text = re.sub(r'Website:\s*\S+\s*\n+Content:\s*', '', text, flags=re.DOTALL)
    text = re.sub(r'^PDF\s+\S+\s+content:\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^YouTube video\s+\S+\s+transcript:\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^GitHub\s+\S+\s+file\s+\S+:\s*', '', text, flags=re.IGNORECASE)
    text = text.strip()
    if len(text) > 1500:
        text = text[:1500] + "..."
    return text


def get_website_summary(url):
    return ask_knowledge(f"What is {url} about? Give me a summary.")


# ─────────────────────────────────────────────
# 📺 YOUTUBE LEARNING
# ─────────────────────────────────────────────
def extract_video_id(url):
    regex = r"(?:v=|youtu\.be/)([A-Za-z0-9_-]+)"
    match = re.search(regex, url)
    return match.group(1) if match else None

def train_youtube(url):
    print(f"\n{'='*60}\n📺 TRAIN YOUTUBE: {url}\n{'='*60}")
    start_time = time.time()
    video_id = extract_video_id(url)
    if not video_id:
        return {"success": False, "content": "❌ Invalid YouTube URL"}
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join([x["text"] for x in transcript])
        print(f"✅ Transcript: {len(text)} chars")

        words = text.split()
        chunks = [" ".join(words[i:i+300]) for i in range(0, len(words), 270)]
        stored = store_chunks_in_faiss(url, chunks, source_type="youtube")

        elapsed = time.time() - start_time
        print(f"✅ YOUTUBE DONE: {stored} chunks in {elapsed:.2f}s")
        return {"success": True, "content": f"✅ YouTube learned. {stored} chunks stored."}
    except Exception as e:
        print(f"❌ YouTube error: {e}")
        return {"success": False, "content": f"❌ YouTube error: {str(e)}"}


# ─────────────────────────────────────────────
# 💻 GITHUB LEARNING
# ─────────────────────────────────────────────
import shutil

def train_github(repo_url):
    print(f"\n{'='*60}\n💻 TRAIN GITHUB: {repo_url}\n{'='*60}")
    start_time = time.time()
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp()
        print(f"📥 Cloning to {temp_dir}")
        Repo.clone_from(repo_url, temp_dir)

        chunks = []
        for root, _, files in os.walk(temp_dir):
            for file in files:
                if file.endswith((".py", ".md", ".txt", ".json", ".js", ".html", ".css")):
                    path = os.path.join(root, file)
                    try:
                        with open(path, "r", errors="ignore") as f:
                            text = f.read()[:2000]
                        chunks.append(f"File: {file}\n\n{text}")
                    except Exception as e:
                        print(f"   ⚠️ {file}: {e}")

        stored = store_chunks_in_faiss(repo_url, chunks, source_type="github")
        elapsed = time.time() - start_time
        print(f"✅ GITHUB DONE: {stored} files in {elapsed:.2f}s")
        return {"success": True, "content": f"✅ GitHub learned. {stored} files stored."}
    except Exception as e:
        print(f"❌ GitHub error: {e}")
        return {"success": False, "content": f"❌ GitHub error: {str(e)}"}
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


# ─────────────────────────────────────────────
# 📄 PDF LEARNING
# ─────────────────────────────────────────────
def train_pdf(path):
    print(f"\n{'='*60}\n📄 TRAIN PDF: {path}\n{'='*60}")
    start_time = time.time()
    try:
        reader = PdfReader(path)
        full_text = ""
        pages = len(reader.pages)
        print(f"   Pages: {pages}")
        for i, page in enumerate(reader.pages, 1):
            txt = page.extract_text()
            if txt:
                full_text += txt + "\n"
            if i % 10 == 0:
                print(f"   {i}/{pages} pages...")

        if not full_text.strip():
            return {"success": False, "content": "❌ No text extracted from PDF"}

        print(f"✅ Extracted {len(full_text)} chars")
        words = full_text.split()
        chunks = [" ".join(words[i:i+300]) for i in range(0, len(words), 270)]
        stored = store_chunks_in_faiss(os.path.basename(path), chunks, source_type="pdf")

        elapsed = time.time() - start_time
        print(f"✅ PDF DONE: {stored} chunks in {elapsed:.2f}s")
        return {"success": True, "content": f"✅ PDF learned. {stored} chunks stored."}
    except Exception as e:
        print(f"❌ PDF error: {e}")
        return {"success": False, "content": f"❌ PDF error: {str(e)}"}


# ─────────────────────────────────────────────
# 🔧 SHARED FAISS CHUNK STORE HELPER
# ─────────────────────────────────────────────
def store_chunks_in_faiss(source_id: str, chunks: list, source_type: str = "web") -> int:
    """
    Unified helper — YouTube, GitHub, PDF sab isko use karein.
    FIX: Pehle train_youtube/github/pdf mein memory.store() call hoti thi
    jo undefined thi. Ab sab FAISS mein jaata hai.
    """
    try:
        from memory.vector_store import add_memory
        import hashlib

        stored = 0
        for i, chunk in enumerate(chunks):
            clean_chunk = chunk.strip()
            if not clean_chunk:
                continue
            chunk_hash = hashlib.md5(f"{source_id}_{i}_{chunk[:100]}".encode()).hexdigest()
            memory_id = int(chunk_hash[:8], 16) % 1000000
            add_memory(
                text=clean_chunk,
                memory_id=memory_id,
                metadata={
                    "source": source_type,
                    "url": source_id,
                    "chunk_index": i,
                    "type": f"{source_type}_content",
                    "timestamp": datetime.now().isoformat()
                }
            )
            stored += 1
            if stored % 20 == 0:
                print(f"   Stored {stored}/{len(chunks)} chunks...")

        print(f"✅ FAISS [{source_type}]: {stored} chunks stored for {source_id}")
        return stored
    except Exception as e:
        print(f"❌ FAISS store error [{source_type}]: {e}")
        return 0