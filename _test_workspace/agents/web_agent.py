import requests
import os
import re
import tempfile
from git import Repo
from pypdf import PdfReader
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from youtube_transcript_api import YouTubeTranscriptApi
from memory.global_memory import global_memory as memory

MAX_PAGES = 15

# 🌐 WEBSITE LEARNING

class WebAgent:
    def __init__(self):
        self.visited = set()

    def fetch_page(self, url):
        try:
           headers = {"User-Agent": "Mozilla/5.0"}
           r = requests.get(url, headers=headers, timeout=10)
           return r.text
        except Exception as e:
            print(f"[WebAgent] Failed to fetch {url}: {e}")  # ⭐ LOG ERROR
            return ""


    def extract_text(self, html):
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script","style","nav","footer","header"]):
            tag.decompose()

        return " ".join(soup.get_text(separator=" ").split())

    from urllib.parse import urlparse, urljoin

    def get_links(self, html, base_url):
        soup = BeautifulSoup(html, "html.parser")
        links = set()
        base_domain = urlparse(base_url).netloc

        for a in soup.find_all("a", href=True):
            link = urljoin(base_url, a["href"])
        # Allow same domain + subdomains
            if urlparse(link).netloc.endswith(base_domain):
                links.add(link)

        return links


    def crawl(self, start_url):
        self.visited = set()   # ⭐ FIX: reset crawler each training
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

# 🌐 TRAIN WEBSITE

def train_website(url):
    website_text = web_agent.crawl(url)

    if not website_text:
        return {"success": False, "content": "Could not read website"}

    words = website_text.split()
    chunks = [" ".join(words[i:i+500]) for i in range(0, len(words), 500)]

    for chunk in chunks:
        enriched_chunk = f"""
This content is extracted from a company's official WEBSITE.
It may contain company introduction, services, products, pricing,
clients, about us, contact info and business details.

Website data:
{chunk}
"""

        memory.store(
        question="website_data",
        answer=enriched_chunk,
        source_agent="web_knowledge",
        confidence=0.95
    )


    return {"success": True, "content": f"Website learned. {len(chunks)} chunks stored."}

# 📺 YOUTUBE LEARNING

def extract_video_id(url):
    regex = r"(?:v=|youtu\.be/)([A-Za-z0-9_-]+)"
    match = re.search(regex, url)
    return match.group(1) if match else None


def train_youtube(url):
    video_id = extract_video_id(url)
    if not video_id:
        return {"success": False, "content": "Invalid YouTube URL"}

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join([x["text"] for x in transcript])

        words = text.split()
        chunks = [" ".join(words[i:i+400]) for i in range(0, len(words), 400)]

        for chunk in chunks:
            enriched_chunk = f"""
This content is from a YouTube video transcript.
It may contain tutorial, explanation, education or discussion.

Video transcript:
{chunk}
"""

            memory.store(
    question="youtube_data",
    answer=enriched_chunk,

                source_agent="youtube_knowledge",
                confidence=0.95
            )

        return {"success": True, "content": f"YouTube learned. {len(chunks)} chunks stored."}

    except Exception as e:
        return {"success": False, "content": str(e)}

# 💻 GITHUB LEARNING

import shutil

def train_github(repo_url):
    try:
        temp_dir = tempfile.mkdtemp()
        Repo.clone_from(repo_url, temp_dir)
        stored = 0
        for root, _, files in os.walk(temp_dir):
            for file in files:
                if file.endswith((".py",".md",".txt",".json",".js")):
                    path = os.path.join(root, file)
                    with open(path, "r", errors="ignore") as f:
                        text = f.read()
                    text = text[:2000]
                    enriched_text = f"""
This content is from a GitHub repository.
Repository content:
{text}
"""
                    memory.store(
                        question="github_data",
                        answer=enriched_text,
                        source_agent="github_knowledge",
                        confidence=0.95
                    )
                    stored += 1

        return {"success": True, "content": f"GitHub learned. {stored} files stored."}

    except Exception as e:
        return {"success": False, "content": str(e)}

    finally:
        shutil.rmtree(temp_dir)  # ⭐ CLEANUP

# 📄 PDF LEARNING

def train_pdf(path):
    try:
        reader = PdfReader(path)
        full_text = ""

        for page in reader.pages:
            txt = page.extract_text()
            if txt:
                full_text += txt + "\n"

        words = full_text.split()
        chunks = [" ".join(words[i:i+400]) for i in range(0, len(words), 400)]

        for chunk in chunks:
            enriched_chunk = f"""
This content is from a PDF document.
It may contain study material, report or documentation.

PDF content:
{chunk}
"""

            memory.store(
    question="pdf_data",
    answer=enriched_chunk,

                source_agent="pdf_knowledge",
                confidence=0.95
            )

        return {"success": True, "content": f"PDF learned. {len(chunks)} chunks stored."}

    except Exception as e:
        return {"success": False, "content": str(e)}

# 🔎 ASK FROM LEARNED DATA

def ask_knowledge(question):
    results = memory.semantic_fetch(question)

    if not results:
        return "No relevant knowledge found."

    # 🔥 Join top results into readable answer
    if isinstance(results, list):
        texts = []
        for r in results[:5]:
            if isinstance(r, dict):
                texts.append(str(r.get("answer", "")))
            else:
                texts.append(str(r))
        return "\n\n".join(texts)

    return str(results)

