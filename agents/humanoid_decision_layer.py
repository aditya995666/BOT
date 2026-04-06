# agents/humanoid_decision_layer.py

from agents.emotion_agent import detect_emotion
from memory.episodic_memory import episodic_memory

class HumanoidDecisionLayer:
    """
    Decides the best agent for a query based on:
    - User emotion
    - Context
    - Past performance
    """

    def __init__(self, improvement_engine):
        self.engine = improvement_engine

    def decide_agent(self, query, context=None, history=None):
        context = context or {}
        mood = detect_emotion(query)

        # Fetch past interactions
        recent_interactions = episodic_memory.fetch_recent(limit=20)
        performance = self.engine.performance_metrics.get("agent_performance", {})

        if "code" in query.lower():
            return "coding"
        if "pdf" in query.lower() or "document" in query.lower():
            return "document"
        if mood in ["angry", "frustrated"] and performance.get("support", {}).get("success_rate", 100) < 70:
            return "emotion"  # route to emotion agent for calming/feedback
        return "general"
