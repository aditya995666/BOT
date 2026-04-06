"""
Episodic Memory - Remembers past interactions and problems
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import deque

class EpisodicMemory:
    def __init__(self, memory_file="memory/episodic_memory.json", max_memories=1000):
        print("💾 Initializing Episodic Memory...")
        
        self.memory_file = memory_file
        self.max_memories = max_memories
        self.memories = deque(maxlen=max_memories)
        
        self._load_memories()
        
        print(f"✅ Episodic Memory loaded: {len(self.memories)} memories")
    
    def _load_memories(self):
        """Load memories from file"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r') as f:
                    data = json.load(f)
                    self.memories = deque(data.get("memories", []), maxlen=self.max_memories)
        except Exception as e:
            print(f"⚠️ Could not load memories: {e}")
    
    def _save_memories(self):
        """Save memories to file"""
        try:
            os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
            with open(self.memory_file, 'w') as f:
                json.dump({"memories": list(self.memories)}, f, indent=2)
        except Exception as e:
            print(f"⚠️ Could not save memories: {e}")
    
    def remember(self, interaction: Dict[str, Any]):
        memory_entry = {
        "id": len(self.memories) + 1,
        "timestamp": datetime.now().isoformat(),
        "query": interaction.get("query", "")[:200],
        "response": {
            "success": interaction.get("response", {}).get("success", False),
            "agent_used": interaction.get("response", {}).get("agent_used", "unknown"),
            "response_time": interaction.get("response", {}).get("response_time", 0)
        },
        "user_id": interaction.get("user_id", "anonymous"),
        "tags": self._extract_tags(interaction.get("query", ""))
    }

        self.memories.append(memory_entry)

    # 🔄 SAVE IMMEDIATELY
        self._save_memories()

        print(f"💾 Remembered interaction: {memory_entry['query'][:50]}...")

    
    def _extract_tags(self, query: str) -> List[str]:
        """Extract tags from query"""
        tags = []
        query_lower = query.lower()
        
        # Content tags
        content_tags = {
            "coding": ["code", "program", "python", "function", "algorithm"],
            "document": ["document", "file", "pdf", "upload", "read"],
            "knowledge": ["what", "how", "why", "explain", "tell me"],
            "math": ["formula", "equation", "calculate", "compute", "solve"],
            "error": ["error", "fix", "debug", "problem", "issue"]
        }
        
        for tag, keywords in content_tags.items():
            if any(keyword in query_lower for keyword in keywords):
                tags.append(tag)
        
        return tags[:3]
    
    def recall(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Recall similar past interactions"""
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        scored_memories = []
        
        for memory in self.memories:
            score = 0
            memory_query = memory.get("query", "").lower()
            memory_tags = memory.get("tags", [])
            
            # Word overlap score
            memory_words = set(memory_query.split())
            overlap = query_words.intersection(memory_words)
            score += len(overlap) * 2
            
            # Tag match score
            query_tags = self._extract_tags(query)
            tag_overlap = set(query_tags).intersection(set(memory_tags))
            score += len(tag_overlap) * 3
            
            # Success bonus
            if memory.get("response", {}).get("success", False):
                score += 2
            
            if score > 0:
                scored_memories.append((score, memory))
        
        # Sort by score and return top results
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        return [memory for score, memory in scored_memories[:limit]]
    
    def recall_problem(self, problem_type: str) -> List[Dict[str, Any]]:
        """Recall specific type of problems"""
        problems = []
        
        for memory in self.memories:
            tags = memory.get("tags", [])
            response = memory.get("response", {})
            
            if problem_type in tags and not response.get("success", False):
                problems.append(memory)
        
        return problems[-10:]  # Return last 10 problems
    def fetch_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch most recent episodic memories (newest first)"""
        if not self.memories:
            return []
        return list(self.memories)[-limit:][::-1]

    
    def get_statistics(self) -> Dict[str, Any]:
        """Get memory statistics"""
        total = len(self.memories)
        successful = sum(1 for m in self.memories if m.get("response", {}).get("success", False))
        failed = total - successful
        
        # Count by agent
        agent_counts = {}
        for memory in self.memories:
            agent = memory.get("response", {}).get("agent_used", "unknown")
            agent_counts[agent] = agent_counts.get(agent, 0) + 1
        
        # Count by tag
        tag_counts = {}
        for memory in self.memories:
            for tag in memory.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        return {
            "total_memories": total,
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / max(total, 1)) * 100,
            "agent_distribution": agent_counts,
            "tag_distribution": dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]),
            "memory_usage": f"{total}/{self.max_memories}"
        }
    
    def clear_old_memories(self, days_old: int = 30):
        """Clear memories older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        initial_count = len(self.memories)
        
        self.memories = deque(
            [m for m in self.memories 
             if datetime.fromisoformat(m.get("timestamp", "2000-01-01")) > cutoff_date],
            maxlen=self.max_memories
        )
        
        cleared = initial_count - len(self.memories)
        if cleared > 0:
            print(f"🗑️ Cleared {cleared} old memories")
            self._save_memories()
        
        return cleared


# Create global instance
episodic_memory = EpisodicMemory()