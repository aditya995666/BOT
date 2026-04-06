import requests
import os
import re
import tempfile
import threading
import queue
from git import Repo
from pypdf import PdfReader
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from youtube_transcript_api import YouTubeTranscriptApi
from memory.global_memory import global_memory as memory
from datetime import datetime

MAX_PAGES = 15

# 🔥 AUTO-URL PROCESSOR (Background scraping)
class URLProcessor:
    """Background URL processor - automatically scrapes URLs when detected"""
    
    def __init__(self):
        self.url_queue = queue.Queue()
        self.processed_urls = set()
        self.processing = True
        self.worker_thread = None
        self.start_worker()
    
    def start_worker(self):
        """Start background worker thread"""
        self.worker_thread = threading.Thread(target=self._process_loop, daemon=True)
        self.worker_thread.start()
        print("🔄 Auto-URL Processor started - Will auto-scrape any URL you share")
    
    def add_url(self, url, user_query=""):
        """Add URL to processing queue"""
        if url in self.processed_urls:
            return False
        
        # Clean URL
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        self.url_queue.put({
            'url': url,
            'query': user_query,
            'timestamp': datetime.now()
        })
        return True
    
    def _process_loop(self):
        """Background worker that processes URLs"""
        while self.processing:
            try:
                item = self.url_queue.get(timeout=2)
                url = item['url']
                
                print(f"🔄 Auto-scraping in background: {url}")
                result = train_website_background(url)
                
                if result.get('success'):
                    self.processed_urls.add(url)
                    print(f"✅ Auto-scraped & stored: {url}")
                else:
                    print(f"❌ Auto-scrape failed: {url}")
                
                self.url_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"URL Processor error: {e}")
    
    def is_processed(self, url):
        """Check if URL already processed"""
        return url in self.processed_urls
    
    def get_status(self):
        """Get processor status"""
        return {
            "processed_count": len(self.processed_urls),
            "queue_size": self.url_queue.qsize()
        }

# Global processor instance
url_processor = URLProcessor()

# 🌐 WEBSITE LEARNING

class WebAgent:
    def __init__(self):
        self.visited = set()

    def fetch_page(self, url):
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(url, headers=headers, timeout=15)
            return r.text
        except Exception as e:
            print(f"[WebAgent] Failed to fetch {url}: {e}")
            return ""

    def extract_text(self, html):
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script","style","nav","footer","header"]):
            tag.decompose()
        return " ".join(soup.get_text(separator=" ").split())

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
        self.visited = set()
        to_visit = [start_url]
        collected_text = ""

        while to_visit and len(self.visited) < MAX_PAGES:
            url = to_visit.pop(0)
            if url in self.visited:
                continue
            self.visited.add(url)
            html = self.fetch_page(url)
            if not html:
                continue
            text = self.extract_text(html)
            collected_text += "\n\n" + text[:3000]
            to_visit.extend(list(self.get_links(html, url)))

        return collected_text

web_agent = WebAgent()

# 🔥 Background training 
def train_website_background(url):
    """Background training - stores in FAISS and SQLite"""
    try:
        website_text = web_agent.crawl(url)
        
        if not website_text or len(website_text.strip()) < 100:
            return {"success": False, "content": "Insufficient content"}
        
        words = website_text.split()
        chunks = [" ".join(words[i:i+500]) for i in range(0, len(words), 500)]
        
        stored_count = 0
        for chunk in chunks:
            enriched_chunk = f"""
Website: {url}
Content: {chunk}
"""
            try:
                memory.store(
                    question=f"website_{url[:50]}",
                    answer=enriched_chunk,
                    source_agent="web_knowledge",
                    confidence=0.95,
                    content_type="website"
                )
                stored_count += 1
            except Exception as e:
                print(f"Store error in background: {e}")
        
        # 🔥 Auto-generate summary after learning
        if stored_count > 0:
            print(f"📝 Auto-summary ready for {url}")
        
        return {"success": True, "content": f"Stored {stored_count} chunks", "chunks": stored_count}
    except Exception as e:
        return {"success": False, "content": str(e)}

# 🌐 TRAIN WEBSITE (Public - with output)
def train_website(url):
    print(f"[WebAgent] Training on website: {url}")
    website_text = web_agent.crawl(url)

    if not website_text or len(website_text.strip()) < 100:
        return {"success": False, "content": "Could not read website or insufficient content"}

    words = website_text.split()
    chunks = [" ".join(words[i:i+500]) for i in range(0, len(words), 500)]
    
    stored_count = 0
    for chunk in chunks:
        enriched_chunk = f"""
Website: {url}
Content: {chunk}
"""
        try:
            memory.store(
                question=f"website_{url[:50]}",
                answer=enriched_chunk,
                source_agent="web_knowledge",
                confidence=0.95,
                content_type="website"
            )
            stored_count += 1
        except Exception as e:
            print(f"Store error: {e}")

    return {"success": True, "content": f"✅ Website learned. {stored_count} chunks stored from {url}"}

# 🔥 Auto-detect and process URL from text
def process_url_if_present(text):
    """Extract URL from text and trigger background processing"""
    url_pattern = r'https?://[^\s]+|www\.[^\s]+'
    urls = re.findall(url_pattern, text)
    
    if urls:
        for url in urls:
            url_processor.add_url(url, text)
        return True, urls[0]
    return False, None

def is_url_processed(url):
    """Check if URL has been processed"""
    return url_processor.is_processed(url)

def get_auto_processor_status():
    """Get status of auto processor"""
    return url_processor.get_status()

# 🔥 GET SUMMARY FROM LEARNED DATA
def get_website_summary(url):
    """Get summary of a learned website"""
    question = f"What is {url} about? Give me a summary of the company and their services."
    return ask_knowledge(question)

# 🔎 ASK FROM LEARNED DATA - COMPLETE FIX
def ask_knowledge(question):
    print(f"[WebAgent] Asking: {question}")
    
    try:
        # 🔥 FIX 1: Try semantic_fetch first (FAISS)
        if hasattr(memory, 'semantic_fetch'):
            results = memory.semantic_fetch(question, top_k=5)
            if results:
                return _format_results(results)
        
        # 🔥 FIX 2: Try query_knowledge
        if hasattr(memory, 'query_knowledge'):
            results = memory.query_knowledge(question, top_k=5)
            if results:
                return _format_results(results)
        
        # 🔥 FIX 3: Try search_memory
        if hasattr(memory, 'search_memory'):
            results = memory.search_memory(question, limit=5)
            if results:
                return _format_results(results)
        
        # 🔥 FIX 4: Direct database query with correct schema
        try:
            import sqlite3
            from pathlib import Path
            
            db_path = Path(__file__).parent.parent / "memory" / "memory.db"
            if db_path.exists():
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                
                # 🔥 Check if 'question' column exists, if not use 'query'
                cursor.execute("PRAGMA table_info(memory)")
                columns = [c[1] for c in cursor.fetchall()]
                
                question_col = "question" if "question" in columns else "query" if "query" in columns else "id"
                answer_col = "answer" if "answer" in columns else "response" if "response" in columns else "content"
                
                keywords = question.lower().split()[:5]
                keyword_conditions = " OR ".join([f"{question_col} LIKE '%{kw}%' OR {answer_col} LIKE '%{kw}%'" for kw in keywords])
                
                cursor.execute(f"""
                    SELECT {question_col}, {answer_col} FROM memory 
                    WHERE source_agent IN ('web_knowledge', 'youtube_knowledge', 'github_knowledge', 'pdf_knowledge')
                    AND ({keyword_conditions})
                    LIMIT 5
                """)
                
                rows = cursor.fetchall()
                conn.close()
                
                if rows:
                    results = [{"question": r[0], "answer": r[1]} for r in rows]
                    return _format_results(results)
        except Exception as e:
            print(f"Direct DB query error: {e}")
        
        return "❌ No relevant knowledge found. Share a URL first - I'll learn about it automatically!"

    except Exception as e:
        print(f"Ask knowledge error: {e}")
        return f"❌ Knowledge retrieval failed: {str(e)}"

def _format_results(results):
    """Format results into readable answer"""
    if not results:
        return "No relevant knowledge found."
    
    if isinstance(results, str):
        return results
    
    if isinstance(results, list):
        texts = []
        for i, r in enumerate(results[:3], 1):
            if isinstance(r, dict):
                answer = r.get("answer", "")
                if answer:
                    # Clean up the answer
                    answer = re.sub(r'^Website:.*?\nContent:\s*', '', answer, flags=re.DOTALL)
                    answer = answer.strip()
                    if len(answer) > 1500:
                        answer = answer[:1500] + "..."
                    texts.append(f"📚 **Info {i}**\n{answer}\n")
            elif isinstance(r, str):
                texts.append(f"📚 **Info {i}**\n{r[:1500]}\n")
        
        if texts:
            return "\n---\n".join(texts)
    
    return str(results)[:2000]

# 📺 YOUTUBE LEARNING
def extract_video_id(url):
    regex = r"(?:v=|youtu\.be/)([A-Za-z0-9_-]+)"
    match = re.search(regex, url)
    return match.group(1) if match else None

def train_youtube(url):
    print(f"[WebAgent] Training on YouTube: {url}")
    video_id = extract_video_id(url)
    if not video_id:
        return {"success": False, "content": "❌ Invalid YouTube URL"}

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join([x["text"] for x in transcript])

        words = text.split()
        chunks = [" ".join(words[i:i+400]) for i in range(0, len(words), 400)]

        stored_count = 0
        for chunk in chunks:
            enriched_chunk = f"YouTube video {url} transcript: {chunk}"
            try:
                memory.store(
                    question=f"youtube_{video_id}",
                    answer=enriched_chunk,
                    source_agent="youtube_knowledge",
                    confidence=0.95,
                    content_type="youtube"
                )
                stored_count += 1
            except Exception as e:
                print(f"Store error: {e}")

        return {"success": True, "content": f"✅ YouTube learned. {stored_count} chunks stored."}
    except Exception as e:
        return {"success": False, "content": f"❌ YouTube error: {str(e)}"}

# 💻 GITHUB LEARNING
import shutil

def train_github(repo_url):
    print(f"[WebAgent] Training on GitHub: {repo_url}")
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp()
        Repo.clone_from(repo_url, temp_dir)
        stored = 0
        for root, _, files in os.walk(temp_dir):
            for file in files:
                if file.endswith((".py",".md",".txt",".json",".js",".html",".css")):
                    path = os.path.join(root, file)
                    try:
                        with open(path, "r", errors="ignore") as f:
                            text = f.read()
                        text = text[:2000]
                        enriched_text = f"GitHub {repo_url} file {file}: {text}"
                        memory.store(
                            question=f"github_{repo_url.replace('/', '_')[:50]}",
                            answer=enriched_text,
                            source_agent="github_knowledge",
                            confidence=0.95,
                            content_type="github"
                        )
                        stored += 1
                    except Exception as e:
                        print(f"File read error: {e}")
                        continue
        return {"success": True, "content": f"✅ GitHub learned. {stored} files stored."}
    except Exception as e:
        return {"success": False, "content": f"❌ GitHub error: {str(e)}"}
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

# 📄 PDF LEARNING
def train_pdf(path):
    print(f"[WebAgent] Training on PDF: {path}")
    try:
        reader = PdfReader(path)
        full_text = ""
        for page in reader.pages:
            txt = page.extract_text()
            if txt:
                full_text += txt + "\n"
        if not full_text.strip():
            return {"success": False, "content": "❌ No text extracted from PDF"}
        words = full_text.split()
        chunks = [" ".join(words[i:i+400]) for i in range(0, len(words), 400)]
        stored_count = 0
        for chunk in chunks:
            enriched_chunk = f"PDF {os.path.basename(path)} content: {chunk}"
            try:
                memory.store(
                    question=f"pdf_{os.path.basename(path)}",
                    answer=enriched_chunk,
                    source_agent="pdf_knowledge",
                    confidence=0.95,
                    content_type="pdf"
                )
                stored_count += 1
            except Exception as e:
                print(f"Store error: {e}")
        return {"success": True, "content": f"✅ PDF learned. {stored_count} chunks stored."}
    except Exception as e:
        return {"success": False, "content": f"❌ PDF error: {str(e)}"}