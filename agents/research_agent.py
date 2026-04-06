# agents/research_agent.py - AI Topic Understanding + Multiple Sources

import time
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import quote
from utils.learning_orchestrator import learning_orchestrator
from memory.global_memory import global_memory
from brain.gemini_llm import GeminiBrain

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

class ResearchAgent:
    
    def __init__(self):
        self.brain = GeminiBrain()
    
    # 🔥 AI Topic Understanding - Khud samjhega
    def understand_topic(self, raw_topic):
        """AI se topic ko samjho - what user actually wants to research"""
        
        prompt = f"""
You are an AI research assistant. Understand what the user wants to research.

User said: "{raw_topic}"

Your task:
1. Understand the MAIN topic they want to research
2. Remove all command/instruction words
3. Extract the core subject

Examples:
- "research and trained python" → "Python programming"
- "tell me about machine learning" → "Machine learning"
- "what is artificial intelligence" → "Artificial intelligence"
- "research cyber security" → "Cyber security"
- "and train yourself on java" → "Java programming"

Return ONLY the topic name (1-5 words), nothing else.
"""
        
        try:
            response = self.brain.think(prompt)
            topic = response.strip()
            topic = re.sub(r'["\']', '', topic)
            topic = topic.split('\n')[0].strip()
            
            if len(topic) > 2 and len(topic) < 100:
                print(f"🧠 AI understood: '{raw_topic}' → '{topic}'")
                return topic
            else:
                return raw_topic
        except Exception as e:
            print(f"AI understanding failed: {e}, using raw topic")
            return raw_topic
    
    # 1️⃣ WIKIPEDIA SEARCH
    def get_wikipedia_url(self, topic):
        """Find best Wikipedia page for topic"""
        search_api = "https://en.wikipedia.org/w/api.php"
        topic = topic.strip().lower()
        
        params = {
            "action": "query",
            "list": "search",
            "srsearch": topic,
            "format": "json",
            "srlimit": 5
        }

        try:
            r = requests.get(search_api, params=params, headers=HEADERS, timeout=15)
            data = r.json()

            if data["query"]["search"]:
                for result in data["query"]["search"]:
                    if result["title"].lower() == topic:
                        title = result["title"]
                        return f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"
                
                first_result = data["query"]["search"][0]["title"]
                return f"https://en.wikipedia.org/wiki/{quote(first_result.replace(' ', '_'))}"
        except Exception as e:
            print(f"Wikipedia search error: {e}")
            return None
        return None

    # 2️⃣ WIKIPEDIA SCRAPER
    def scrape_wikipedia(self, url):
        """Extract content from Wikipedia"""
        try:
            print(f"📥 Fetching Wikipedia: {url}")
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code != 200:
                return ""

            soup = BeautifulSoup(r.text, "html.parser")
            content_div = soup.find("div", {"id": "mw-content-text"})
            if not content_div:
                content_div = soup.find("div", {"class": "mw-parser-output"})
                if not content_div:
                    return ""

            for tag in content_div.find_all(["script", "style", "table", "sup", "span.mw-editsection", "div.reflist", "div.navbox"]):
                tag.decompose()

            title = soup.find("h1", {"id": "firstHeading"})
            title_text = title.get_text().strip() if title else ""

            content_parts = [f"# {title_text}\n"]
            current_section = "INTRODUCTION"
            section_content = []
            
            for element in content_div.find_all(["h2", "h3", "h4", "p", "ul", "ol"]):
                tag_name = element.name
                
                if tag_name in ["h2", "h3", "h4"]:
                    if section_content:
                        content_parts.append(f"\n## {current_section}\n")
                        content_parts.append("\n".join(section_content))
                        section_content = []
                    
                    heading = element.get_text().strip()
                    heading = re.sub(r'\[.*?\]', '', heading)
                    if heading and not any(x in heading.lower() for x in ['see also', 'references', 'external links', 'navigation']):
                        current_section = heading
                
                elif tag_name == "p":
                    para = element.get_text().strip()
                    para = re.sub(r'\[\d+\]', '', para)
                    para = re.sub(r'\s+', ' ', para)
                    if len(para) > 50:
                        section_content.append(para)
                
                elif tag_name in ["ul", "ol"]:
                    list_items = []
                    for li in element.find_all("li", recursive=False):
                        item = li.get_text().strip()
                        if len(item) > 20:
                            list_items.append(f"  • {item}")
                    if list_items:
                        section_content.extend(list_items)

            if section_content:
                content_parts.append(f"\n## {current_section}\n")
                content_parts.append("\n".join(section_content))

            return "\n".join(content_parts)
        except Exception as e:
            print(f"Wikipedia scrape error: {e}")
            return ""

    # 3️⃣ DUCKDUCKGO SEARCH
    def search_duckduckgo(self, topic):
        """Search DuckDuckGo for additional information"""
        try:
            print(f"🦆 Searching DuckDuckGo for '{topic}'...")
            search_url = f"https://html.duckduckgo.com/html/?q={quote(topic)}"
            r = requests.get(search_url, headers=HEADERS, timeout=15)
            
            if r.status_code != 200:
                return ""
            
            soup = BeautifulSoup(r.text, 'html.parser')
            results = soup.find_all('a', class_='result__a')
            
            content_parts = []
            content_parts.append("\n## 🔍 Additional Search Results\n")
            
            for i, result in enumerate(results[:5]):
                title = result.get_text().strip()
                link = result.get('href', '')
                content_parts.append(f"**{i+1}. {title}**")
                content_parts.append(f"   🔗 {link}\n")
            
            snippets = soup.find_all('a', class_='result__snippet')
            for i, snippet in enumerate(snippets[:5]):
                text = snippet.get_text().strip()
                if text:
                    content_parts.append(f"   📝 {text[:300]}\n")
            
            return "\n".join(content_parts)
        except Exception as e:
            print(f"DuckDuckGo search error: {e}")
            return ""

    # 4️⃣ GOOGLE SEARCH
    def search_google(self, topic):
        """Search Google for information"""
        try:
            print(f"🔍 Searching Google for '{topic}'...")
            search_url = f"https://www.google.com/search?q={quote(topic)}"
            r = requests.get(search_url, headers=HEADERS, timeout=15)
            
            if r.status_code != 200:
                return ""
            
            soup = BeautifulSoup(r.text, 'html.parser')
            results = []
            
            for g in soup.find_all('div', class_='g'):
                title_elem = g.find('h3')
                snippet_elem = g.find('div', class_='VwiC3b')
                
                if title_elem:
                    title = title_elem.get_text().strip()
                    snippet = snippet_elem.get_text().strip() if snippet_elem else ""
                    if title and len(title) > 5:
                        results.append(f"**{title}**\n   {snippet[:300]}\n")
            
            if results:
                return "\n## 🌐 Google Search Results\n\n" + "\n".join(results[:5])
            return ""
        except Exception as e:
            print(f"Google search error: {e}")
            return ""

    # 5️⃣ TEXT CLEANING
    def clean_text(self, text):
        """Clean but preserve meaningful content"""
        if not text:
            return ""
        
        paragraphs = text.split('\n')
        cleaned = []
        
        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
            
            if any(x in p.lower() for x in [
                'see also', 'references', 'external links', 
                'navigation menu', 'privacy policy', 'terms of use'
            ]):
                continue
            
            if p.startswith('#') or p.startswith('##'):
                cleaned.append(p)
            elif len(p) > 30:
                cleaned.append(p)
            elif p.startswith('  •'):
                cleaned.append(p)
        
        return '\n'.join(cleaned)

    # 6️⃣ STRUCTURE NOTES
    def structure_notes(self, topic, content):
        """Create well-structured study notes"""
        
        sections = re.split(r'\n##\s+', content)
        
        structured = f"""# 📚 COMPLETE STUDY NOTES: {topic.upper()}

"""
        for i, section in enumerate(sections):
            if i == 0:
                structured += f"\n{section}\n"
            else:
                lines = section.split('\n', 1)
                if len(lines) == 2:
                    heading, body = lines
                    structured += f"\n## 📖 {heading}\n"
                    structured += f"{body}\n"
                else:
                    structured += f"\n## 📌 Section {i}\n"
                    structured += f"{section}\n"
            
            structured += "\n" + "-" * 80 + "\n"
        
        word_count = len(content.split())
        para_count = len([p for p in content.split('\n') if p and not p.startswith('#')])
        
        structured += f"""
📊 **Summary**: {word_count} words, {para_count} paragraphs
📅 Research completed: {time.strftime('%Y-%m-%d %H:%M:%S')}
"""
        return structured

    # 7️⃣ MAIN RESEARCH - AI Understand + Multiple Sources
    def research_topic(self, raw_topic):
        """Main research function - AI understands topic, then searches ALL sources"""
        
        print(f"\n🔎 DEEP RESEARCH STARTED: '{raw_topic}'")
        print("=" * 60)
        
        # 🔥 STEP 1: AI se topic samjho
        print("🧠 AI Understanding topic...")
        understood_topic = self.understand_topic(raw_topic)
        print(f"✅ AI understood: '{raw_topic}' → '{understood_topic}'")

        all_content = []
        
        # SOURCE 1: WIKIPEDIA
        print(f"\n🌐 Searching Wikipedia for '{understood_topic}'...")
        wiki_url = self.get_wikipedia_url(understood_topic)
        
        if wiki_url:
            print(f"📥 Scraping Wikipedia: {wiki_url}")
            wiki_text = self.scrape_wikipedia(wiki_url)
            if wiki_text and len(wiki_text) > 500:
                all_content.append(f"\n{'='*60}\n📚 SOURCE: WIKIPEDIA\n{'='*60}\n")
                all_content.append(self.clean_text(wiki_text))
                print(f"✅ Wikipedia: {len(wiki_text)} chars")
            else:
                print("⚠️ Wikipedia content insufficient")
        else:
            print("❌ No Wikipedia page found")
        
        # SOURCE 2: DUCKDUCKGO
        print(f"\n🦆 Searching DuckDuckGo for '{understood_topic}'...")
        ddg_content = self.search_duckduckgo(understood_topic)
        if ddg_content and len(ddg_content) > 100:
            all_content.append(f"\n{'='*60}\n🦆 SOURCE: DUCKDUCKGO\n{'='*60}\n")
            all_content.append(ddg_content)
            print(f"✅ DuckDuckGo: {len(ddg_content)} chars")
        
        # SOURCE 3: GOOGLE (If Wikipedia didn't have good content)
        if len(all_content) < 2:
            print(f"\n🔍 Searching Google for '{understood_topic}'...")
            google_content = self.search_google(understood_topic)
            if google_content and len(google_content) > 100:
                all_content.append(f"\n{'='*60}\n🌐 SOURCE: GOOGLE\n{'='*60}\n")
                all_content.append(google_content)
                print(f"✅ Google: {len(google_content)} chars")
        
        # Check if any content found
        if not all_content or len(''.join(all_content)) < 200:
            print("❌ No content found from any source")
            return self._fallback_search(understood_topic)
        
        # Combine all content
        combined_content = "\n".join(all_content)
        print(f"\n✅ Total content: {len(combined_content)} chars")
        
        # Clean and structure
        final_knowledge = self.structure_notes(understood_topic, combined_content)
        
        # Store in memory
        try:
            global_memory.store(
                question=understood_topic,
                answer=final_knowledge,
                source_agent="deep_research_agent",
                content_type="research",
                confidence=0.95
            )
            print("🧠 Stored in memory successfully")
        except Exception as e:
            print(f"Memory store failed: {e}")
        
        # Auto learning
        try:
            learning_orchestrator.process_interaction({
                "query": f"Auto research: {understood_topic}",
                "intent": "research_training",
                "response": {
                    "success": True,
                    "agent_used": "deep_research_agent",
                    "content": final_knowledge[:500] + "..."
                }
            })
        except Exception as e:
            print(f"Training failed: {e}")
        
        print(f"\n✅ RESEARCH COMPLETE! Generated {len(final_knowledge)} chars")
        return final_knowledge

    # 8️⃣ FALLBACK SEARCH
    def _fallback_search(self, topic):
        """Fallback when all sources fail"""
        return f"""# {topic.upper()} - Research Failed

❌ Could not find detailed information about "{topic}".

Suggestions:
• Try a more specific topic
• Check spelling
• Use simpler terms

Example: Instead of "AI", try "artificial intelligence overview"
"""