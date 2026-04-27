import json
from brain.gemini_llm import GeminiBrain
import traceback
from collections import deque

class ClarificationEngine:
    """
    AI-powered ambiguity detector using central GeminiBrain.
    """

    def __init__(self):
        self.brain = GeminiBrain()
        self.question_history = {}  # Track questions per user
        self.max_questions = 1  # Max 2 questions per topic

    def analyze_query(self, query: str, intent: str, history: list, user_id="default"):
        """
        Returns:
        {
            "unclear": bool,
            "question": str | None
        }
        """
        # Initialize user history if not exists
        if user_id not in self.question_history:
            self.question_history[user_id] = deque(maxlen=5)
        
        # SPECIAL CASE: Direct greeting detection
        if query and isinstance(query, str):
            query_lower = query.lower().strip()
            greetings = ["hello", "hi", "hey", "namaste", "khaa ho", "kaise ho", "hy", "hlo", "hola"]
            if any(greet == query_lower or query_lower.startswith(greet + " ") for greet in greetings):
                print(f"✅ Direct greeting detected: '{query}'")
                return {"unclear": False, "question": None}

        # Check if we've asked too many questions already
        recent_questions = list(self.question_history[user_id])
        if len(recent_questions) >= self.max_questions:
            print(f"✅ Max questions ({self.max_questions}) reached - assuming clear")
            return {"unclear": False, "question": None}
        
        # Check if last response was "yes" or "no" - then assume clear
        if history and len(history) > 1:
            last_user_msg = None
            for msg in reversed(history):
                if isinstance(msg, dict) and msg.get("role") == "user":
                    last_user_msg = msg.get("content", "").lower()
                    break
            
            if last_user_msg and last_user_msg.strip() in ["yes", "no", "haan", "nahi", "yep", "nope"]:
                print(f"✅ Short answer detected - assuming clear")
                return {"unclear": False, "question": None}

        # Convert history to safe format for prompt
        safe_history = []
        if history:
            for msg in history:
                if isinstance(msg, dict):
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    safe_history.append(f"{role}: {content}")
                else:
                    safe_history.append(f"user: {str(msg)}")
        
        history_str = "\n".join(safe_history) if safe_history else "No history"

        prompt = f"""
You are an AI query clarity evaluator. You ask ONLY when TRULY necessary.

User query: "{query}"
Detected intent: {intent}
Conversation history: {history_str if history_str else 'None'}

🔴 CRITICAL RULES - NO MANUAL KEYWORDS:
1. Ask for clarification ONLY if query is COMPLETELY ambiguous (like "something", "tell me", "that thing")
2. If user has provided ANY meaningful information → NOT unclear (even if not perfect)
3. For coding requests: Assume user wants code in Python unless specified otherwise
4. For document requests: If user said "from pdf" or "from document" → already clear
5. For knowledge requests: If user asked "what is", "how to", "explain" → already clear
6. NEVER ask clarification just because you want more details
7. If in doubt, assume CLEAR (default to False)

Ask clarification ONLY when:
- Query is extremely short with zero context (1-2 vague words)
- Truly no way to determine what user wants

Return ONLY JSON:
{{"unclear": true/false, "question": "clarification question or null"}}
"""
        try:
            response_text = self.brain.think(prompt)
            
            if response_text is None:
                print("⚠️ Gemini returned None")
                return {"unclear": False, "question": None}
            
            cleaned = str(response_text).strip()
            
            if not cleaned:
                print("⚠️ Gemini returned empty string")
                return {"unclear": False, "question": None}
            
            # Clean JSON if needed
            if "```json" in cleaned:
                parts = cleaned.split("```json", 1)
                if len(parts) > 1:
                    cleaned = parts[1].split("```", 1)[0].strip()
            elif "```" in cleaned:
                parts = cleaned.split("```", 2)
                if len(parts) > 1:
                    cleaned = parts[1].strip()
            
            # Parse JSON
            try:
                parsed = json.loads(cleaned)
                if isinstance(parsed, dict):
                    unclear = bool(parsed.get("unclear", False))
                    question = parsed.get("question")
                    
                    if unclear and question:
                        # Check if question already asked
                        if question in recent_questions:
                            print(f"⚠️ Question already asked: {question}")
                            return {"unclear": False, "question": None}
                        
                        # Store question
                        self.question_history[user_id].append(question)
                    
                    if question and isinstance(question, str):
                        question = question.strip()
                    else:
                        question = None
                    
                    return {"unclear": unclear, "question": question}
            except json.JSONDecodeError:
                print(f"⚠️ Could not parse as JSON: {cleaned[:100]}...")
                return {"unclear": False, "question": None}
            
        except Exception as e:
            print(f"❌ Clarification Engine crashed: {type(e).__name__}: {str(e)}")
            return {"unclear": False, "question": None}


clarification_engine = ClarificationEngine()