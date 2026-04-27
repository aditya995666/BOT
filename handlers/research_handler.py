# handlers/research_handler.py - DIRECT RESEARCH AGENT (No OS API)

import time
import re

class ResearchHandler:
    def __init__(self, os_api_url="http://127.0.0.1:8000"):
        self.OS_API = os_api_url.rstrip('/')  # Not used, kept for compatibility

    def handle(self, q: str):
        original_query = q
        
        # Step 1: Remove command words
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
        
        # Step 2: Remove stop words from beginning
        stop_words = ['and', 'the', 'a', 'an', 'of', 'for', 'to', 'in', 'on', 'at', 'with', 'by']
        words = topic.split()
        while words and words[0].lower() in stop_words:
            words = words[1:]
        topic = ' '.join(words)
        
        # Step 3: Clean up
        topic = re.sub(r'\s+', ' ', topic).strip()
        topic = topic.rstrip('?').strip()
        
        # Step 4: Fallback if empty
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
        
        # Step 6: Capitalize
        if topic and len(topic) > 2:
            topic = topic[0].upper() + topic[1:]
        
        print(f"📝 Original: '{original_query}'")
        print(f"🎯 Auto-detected topic: '{topic}'")

        try:
            # 🔥 DIRECT RESEARCH AGENT CALL - NO OS API, NO GEMINI
            from agents.research_agent import research_agent
            
            print(f"\n🔬 RESEARCH STARTED: '{topic}'")
            start_time = time.time()
            
            result = research_agent.research_topic(topic)
            
            elapsed = time.time() - start_time
            word_count = len(result.split())
            
            print(f"⏱️ Research completed in {elapsed:.1f} seconds")
            print(f"📊 Words: {word_count}")
            
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
            
        except Exception as e:
            return {"content": f"❌ Research error: {str(e)}"}