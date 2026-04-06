# handlers/research_handler.py - PURE AI DETECTION (No manual anything)

import requests
from urllib.parse import quote
import time
import re

class ResearchHandler:
    def __init__(self, os_api_url="http://127.0.0.1:8000"):
        self.OS_API = os_api_url.rstrip('/')

    def handle(self, q: str):
        original_query = q
        
        # 🔥 PURE AI DETECTION - NO MANUAL MAPPINGS
        
        # Step 1: Remove command words only (no topic mapping)
        command_words = [
            'research', 'do research', 'research about', 'research on',
            'deep research', 'internet research', 'find information on',
            'search for', 'look up', 'study', 'learn about',
            'tell me about', 'explain', 'what is', 'who is', 'where is',
            'when is', 'why is', 'how does', 'define', 'describe',
            'and trained', 'trained on', 'train on', 'train yourself',
            'and train', 'please', 'jarvis', 'can you', 'could you'
        ]
        
        topic = q.lower().strip()
        for cmd in command_words:
            if topic.startswith(cmd):
                topic = topic[len(cmd):].strip()
                break
        
        # Step 2: Remove common stop words from beginning only
        stop_words = ['and', 'the', 'a', 'an', 'of', 'for', 'to', 'in', 'on', 'at', 'with', 'by']
        words = topic.split()
        while words and words[0].lower() in stop_words:
            words = words[1:]
        topic = ' '.join(words)
        
        # Step 3: Clean up
        topic = re.sub(r'\s+', ' ', topic).strip()
        topic = topic.rstrip('?').strip()
        
        # Step 4: If topic is empty, use original query without command words
        if not topic or len(topic) < 2:
            words = original_query.split()
            skip_words = {'research', 'and', 'trained', 'train', 'on', 'about', 'do', 'deep', 
                         'internet', 'find', 'information', 'search', 'look', 'up', 'study', 
                         'learn', 'tell', 'me', 'explain', 'what', 'is', 'who', 'where', 
                         'when', 'why', 'how', 'does', 'define', 'describe', 'please'}
            filtered = [w for w in words if w.lower() not in skip_words and len(w) > 2]
            if filtered:
                topic = ' '.join(filtered)
            else:
                topic = original_query
        
        # Step 5: Final cleanup
        topic = re.sub(r'\s+', ' ', topic).strip()
        
        # Step 6: Capitalize properly
        if topic and len(topic) > 2:
            topic = topic[0].upper() + topic[1:]
        
        print(f"📝 Original: '{original_query}'")
        print(f"🎯 Auto-detected topic: '{topic}'")

        try:
            safe_topic = quote(topic)
            url = f"{self.OS_API}/research/train?topic={safe_topic}"

            headers = {"Authorization": "Bearer jarvis123"}
            
            print(f"\n🔬 RESEARCH REQUEST: '{topic}'")
            print(f"📡 API URL: {url}")
            
            start_time = time.time()
            r = requests.post(url, headers=headers, timeout=180)
            elapsed = time.time() - start_time

            r.raise_for_status()
            data = r.json()

            print(f"⏱️ Research completed in {elapsed:.1f} seconds")
            print(f"📦 Response status: {data.get('status')}")

            if data.get("status") == "completed" and data.get("result"):
                result = data.get("result")
                word_count = len(result.split())
                
                formatted_result = f"""🔬 **RESEARCH COMPLETE: {topic.upper()}**
⏱️ Time: {elapsed:.1f} seconds | 📊 Words: {word_count}

{result[:8000]}{'...[truncated]' if len(result) > 8000 else ''}

---
📝 *This research has been saved to memory for future reference.*"""
                
                return {
                    "content": formatted_result,
                    "full_result": result,
                    "word_count": word_count,
                    "topic": topic
                }
            
            elif data.get("status") == "processing":
                return {"content": f"⏳ Research on '{topic}' is still processing. Please check back in a moment."}
            
            else:
                if data.get("result"):
                    result = data.get("result")
                    word_count = len(result.split())
                    formatted_result = f"""🔬 **RESEARCH RESULT: {topic.upper()}**
⏱️ Time: {elapsed:.1f} seconds | 📊 Words: {word_count}

{result[:8000]}

---
📝 *Retrieved from system.*"""
                    return {"content": formatted_result}
                
                return {"content": f"⚠️ Research completed but no detailed result received for '{topic}'."}

        except requests.exceptions.Timeout:
            return {"content": f"⏰ Research timeout (3 minutes) for '{topic}'. Topic might be too broad."}
        
        except requests.exceptions.ConnectionError:
            return {"content": "❌ Cannot connect to Research Server. Make sure OS API server is running on port 8000."}
        
        except requests.exceptions.RequestException as e:
            return {"content": f"❌ Research server error: {str(e)}"}
        
        except Exception as e:
            return {"content": f"❌ Research error: {type(e).__name__} → {str(e)}"}