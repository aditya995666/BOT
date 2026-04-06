"""
Reflection Agent - Compatible with both old and new systems
"""
from brain.gemini_llm import GeminiBrain
from utils.prompt_templates import REFLECTION_PROMPT

# Initialize brain with error handling
try:
    brain = GeminiBrain()
    BRAIN_AVAILABLE = True
except Exception as e:
    print(f"⚠️ Brain initialization error: {e}")
    BRAIN_AVAILABLE = False
    brain = None

# Original function (backward compatibility)
def self_reflect(answer):
    if not BRAIN_AVAILABLE or brain is None:
        return "Reflection not available"
    return brain.think(REFLECTION_PROMPT.format(answer=answer))

# Router-compatible function
def reflect(agent_name, query, result, context=None):
    """Main reflection function for router"""
    
    if not BRAIN_AVAILABLE or brain is None:
        return {
            "insights": ["System in fallback mode"],
            "self_suggestions": "Brain module not available"
        }
    
    try:
        # Prepare analysis
        analysis_prompt = f"""
        Analyze this agent interaction:
        
        AGENT: {agent_name}
        QUERY: {query}
        RESULT TYPE: {type(result).__name__}
        RESULT SAMPLE: {str(result)[:200]}
        CONTEXT: {str(context)[:100] if context else 'None'}
        
        Provide:
        1. Brief insights about the interaction
        2. Suggestions for improvement
        """
        
        reflection_text = brain.think(analysis_prompt)
        
        # Format response for router
        insights = [
            f"✅ {agent_name.capitalize()} agent executed",
            f"📊 Result type: {type(result).__name__}",
            "🔍 Reflection analysis completed"
        ]
        
        return {
            "insights": insights,
            "self_suggestions": reflection_text[:300],  # Limit length
            "agent": agent_name,
            "reflection_id": f"ref_{id(result)}"
        }
        
    except Exception as e:
        return {
            "insights": ["❌ Reflection error"],
            "self_suggestions": f"Error: {str(e)[:100]}",
            "agent": agent_name
        }

# Router-compatible class
class ReflectionAgent:
    def __init__(self):
        self.reflection_count = 0
    
    def reflect(self, agent_name, query, result, context=None):
        self.reflection_count += 1
        return reflect(agent_name, query, result, context)
    
    def get_stats(self):
        return {"total_reflections": self.reflection_count}

# Singleton instance for router
reflection_agent = ReflectionAgent()