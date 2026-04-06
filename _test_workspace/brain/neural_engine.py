"""
Neural Engine - Core learning and improvement engine
Mistakes are remembered internally to improve future responses
NEVER shown to user
"""

import json
import os
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import pickle
from collections import defaultdict


class NeuralEngine:
    def __init__(self, memory_file="memory/problem_database.json"):
        print("🧠 Initializing Neural Engine...")

        self.memory_file = memory_file

        self.knowledge_base = {
            "patterns": defaultdict(list),
            "mistakes": defaultdict(list),
            "solutions": defaultdict(list),
            "improvements": [],
            "statistics": {
                "total_interactions": 0,
                "successful_responses": 0,
                "failed_responses": 0,
                "learning_cycles": 0
            }
        }

        self._load_knowledge()

        self.learning_rate = 0.1
        self.experience_buffer = []
        self.max_experience_size = 1000

        print(f"✅ Neural Engine loaded: {self.knowledge_base['statistics']['total_interactions']} interactions")

    # ---------------- LOAD ----------------
    def _load_knowledge(self):
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r') as f:
                    data = json.load(f)

                # restore defaultdict
                self.knowledge_base["patterns"] = defaultdict(list, data.get("patterns", {}))
                self.knowledge_base["mistakes"] = defaultdict(list, data.get("mistakes", {}))
                self.knowledge_base["solutions"] = defaultdict(list, data.get("solutions", {}))
                self.knowledge_base["improvements"] = data.get("improvements", [])
                self.knowledge_base["statistics"] = data.get("statistics", self.knowledge_base["statistics"])

                print(f"📚 Loaded {len(self.knowledge_base['patterns'])} patterns from memory")
                print(f"📚 Loaded {len(self.knowledge_base['mistakes'])} mistake patterns from memory")
        except Exception as e:
            print(f"⚠️ Could not load knowledge: {e}")

    # ---------------- SAVE ----------------
    def _save_knowledge(self):
        try:
            os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)

            # convert defaultdict → dict for JSON
            safe_knowledge = {
                "patterns": dict(self.knowledge_base["patterns"]),
                "mistakes": dict(self.knowledge_base["mistakes"]),
                "solutions": dict(self.knowledge_base["solutions"]),
                "improvements": self.knowledge_base["improvements"],
                "statistics": self.knowledge_base["statistics"]
            }

            with open(self.memory_file, 'w') as f:
                json.dump(safe_knowledge, f, indent=2, default=str)

            print(f"💾 Knowledge saved to {self.memory_file}")
        except Exception as e:
            print(f"⚠️ Could not save knowledge: {e}")

    # ---------------- LEARN ----------------
    def learn_from_interaction(self, interaction: Dict[str, Any]):
        try:
            query = interaction.get("query", "")
            response = interaction.get("response", {})
            success = response.get("success", False)
            agent_used = response.get("agent_used", "unknown")

            self.knowledge_base["statistics"]["total_interactions"] += 1
            if success:
                self.knowledge_base["statistics"]["successful_responses"] += 1
            else:
                self.knowledge_base["statistics"]["failed_responses"] += 1

            patterns = self._extract_patterns(query)

            if success:
                for pattern in patterns:
                    self.knowledge_base["patterns"][pattern].append({
                        "query": query,
                        "response": response,
                        "agent": agent_used,
                        "timestamp": datetime.now().isoformat(),
                        "success": True
                    })
                    print(f"🧠 Learned successful pattern: '{pattern}'")
            else:
                for pattern in patterns:
                    error_msg = response.get("error", "unknown")
                    if isinstance(error_msg, dict):
                        error_msg = str(error_msg)
                    
                    self.knowledge_base["mistakes"][pattern].append({
                        "query": query,
                        "error": error_msg,
                        "agent": agent_used,
                        "timestamp": datetime.now().isoformat(),
                        "success": False
                    })
                    print(f"🧠 Learned mistake pattern: '{pattern}' - will avoid next time")

            self.experience_buffer.append(interaction)
            if len(self.experience_buffer) > self.max_experience_size:
                self.experience_buffer.pop(0)

            # Save every time
            self._save_knowledge()

            print(f"🧠 Learned from interaction: {query[:50]}...")

        except Exception as e:
            print(f"⚠️ Learning error: {e}")

    # ---------------- PATTERN ----------------
    def _extract_patterns(self, query: str) -> List[str]:
        patterns = []
        query_lower = query.lower()
        words = query_lower.split()

        if len(words) >= 3:
            for i in range(len(words) - 1):
                pattern = f"{words[i]} {words[i+1]}"
                if len(pattern) > 3:
                    patterns.append(pattern)

        intent_keywords = {
            "code": ["code", "program", "python", "function", "algorithm"],
            "document": ["document", "file", "pdf", "upload", "read"],
            "knowledge": ["what", "how", "why", "explain", "tell me about"],
            "formula": ["formula", "equation", "calculate", "compute"]
        }

        for intent, keywords in intent_keywords.items():
            if any(k in query_lower for k in keywords):
                patterns.append(f"intent:{intent}")

        return list(set(patterns))[:5]

    # ---------------- SUGGESTION ----------------
    def get_suggestion(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Get suggestion for INTERNAL USE ONLY
        Mistakes are remembered to improve future responses
        NEVER shown to user - returns only internal data
        """
        patterns = self._extract_patterns(query)
        internal_hint = None
        highest_confidence = 0

        for pattern in patterns:
            # First check mistakes - higher priority
            if pattern in self.knowledge_base["mistakes"]:
                past_mistakes = self.knowledge_base["mistakes"][pattern]
                if past_mistakes:
                    last_mistake = past_mistakes[-1]
                    confidence = 0.9
                    
                    if confidence > highest_confidence:
                        highest_confidence = confidence
                        internal_hint = {
                            "type": "mistake_warning",
                            "pattern": pattern,
                            "confidence": confidence,
                            "error_to_avoid": last_mistake.get("error", "unknown")[:100],
                            "internal_only": True,
                            "action": "be_careful",
                            "timestamp": datetime.now().isoformat()
                        }
                        print(f"🧠 Internal: Found mistake pattern '{pattern}' - will avoid")

            # Then check successful patterns
            if pattern in self.knowledge_base["patterns"]:
                past = self.knowledge_base["patterns"][pattern]
                if past:
                    last = past[-1]
                    confidence = 0.8
                    
                    if confidence > highest_confidence:
                        highest_confidence = confidence
                        internal_hint = {
                            "type": "success_pattern",
                            "pattern": pattern,
                            "confidence": confidence,
                            "approach": last.get("agent", "general"),
                            "internal_only": True,
                            "action": "use_similar_approach",
                            "timestamp": datetime.now().isoformat()
                        }
                        print(f"🧠 Internal: Found successful pattern '{pattern}' - will reuse")

        return internal_hint

    # ---------------- CYCLE ----------------
    def run_learning_cycle(self):
        print("🔄 Running learning cycle...")

        self.knowledge_base["statistics"]["learning_cycles"] += 1
        recent = self.experience_buffer[-50:] if self.experience_buffer else []

        improvements = []
        mistake_insights = []
        
        for exp in recent:
            if exp.get("response", {}).get("success"):
                imp = self._analyze_success(exp)
                if imp:
                    improvements.append(imp)
            else:
                imp = self._analyze_failure(exp)
                if imp:
                    improvements.append(imp)
                    mistake_insights.append(imp)

        improvements = [i for i in improvements if i]

        if improvements:
            self.knowledge_base["improvements"].extend(improvements)

        self._save_knowledge()

        if mistake_insights:
            print(f"🧠 Learning cycle found {len(mistake_insights)} mistake patterns to avoid")

        return {
            "improvements_found": len(improvements),
            "mistake_patterns": len(mistake_insights),
            "total_experiences": len(recent),
            "cycle_number": self.knowledge_base["statistics"]["learning_cycles"]
        }

    def _analyze_success(self, experience: Dict) -> Optional[Dict]:
        query = experience.get("query", "")
        response = experience.get("response", {})

        patterns = self._extract_patterns(query)
        if not patterns:
            return None

        return {
            "type": "success_pattern",
            "query_pattern": patterns[0],
            "agent": response.get("agent_used", "unknown"),
            "response_time": response.get("response_time", 0),
            "timestamp": datetime.now().isoformat(),
            "internal": True,
            "insight": f"Successful response for query type: {query[:30]}..."
        }

    def _analyze_failure(self, experience: Dict) -> Optional[Dict]:
        query = experience.get("query", "")
        response = experience.get("response", {})
        error = response.get("error", "unknown error")
        
        patterns = self._extract_patterns(query)
        if not patterns:
            return None

        return {
            "type": "failure_analysis",
            "query_pattern": patterns[0],
            "error": str(error)[:100],
            "timestamp": datetime.now().isoformat(),
            "internal": True,
            "lesson": f"Avoid: {error[:50]} for queries like: {query[:30]}..."
        }

    def get_knowledge_summary(self) -> Dict[str, Any]:
        return {
            "total_patterns": len(self.knowledge_base["patterns"]),
            "total_mistakes": len(self.knowledge_base["mistakes"]),
            "total_improvements": len(self.knowledge_base["improvements"]),
            "statistics": self.knowledge_base["statistics"],
            "recent_patterns": list(self.knowledge_base["patterns"].keys())[:10],
            "common_mistakes": list(self.knowledge_base["mistakes"].keys())[:5]
        }


# Global instance
neural_engine = NeuralEngine()