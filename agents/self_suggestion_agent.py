# agents/self_suggestion_agent.py

from brain.gemini_llm import GeminiBrain

brain = GeminiBrain()

SELF_SUGGESTION_PROMPT_TEMPLATE = """
You are a senior AI system architect reviewing yourself.

User just asked: {user_query}
Your last response / action chain produced: {last_output_or_error}

Now provide **4 concrete improvement suggestions** in Hindi + English mix. 
Only give 4 points, no PROBLEM/ROOT_CAUSE format, no explanations. 
Number them 1 to 4.

Format:
1. ...
2. ...
3. ...
4. ...
"""

def self_suggest(system_output, user_query="", history=None):
    """
    Generate exactly 4 actionable suggestions from last system output.
    """
    history = history or []

    output_str = str(system_output).strip()
    if not output_str:
        output_str = "[Empty response]"

    prompt = SELF_SUGGESTION_PROMPT_TEMPLATE.format(
        user_query=user_query.strip() or "[User query not provided]",
        last_output_or_error=output_str
    )

    try:
        response = brain.think(prompt, history)
        cleaned = response.strip()

        # Ensure only 4 lines returned
        lines = [line.strip() for line in cleaned.split("\n") if line.strip()]
        return "\n".join(lines[:4])

    except Exception as e:
        return "\n".join([
            "1. Exception handling improve karo",
            "2. Logging add karo",
            "3. Prompt ko strict karo",
            "4. brain.think() ke errors handle karo"
        ])


class SelfSuggestionAgent:
    """
    Generate solutions for detected problems.
    Each solution includes a code snippet for auto-fix.
    """

    def generate_solutions(self, problems):
        """
        problems: List of problem objects
        Returns list of dicts:
            - title: problem title
            - code: python code string to fix it
            - fix: textual suggestion
        """
        solutions = []
        for p in problems:
            # 4-line code snippet example per problem
            code_snippet = f"""
# Auto-fix for problem: {p.title}
# Cause: {p.cause}
print('Fixing {p.title} automatically...')
# Add your fix logic here
"""
            solutions.append({
                "title": p.title,
                "code": code_snippet,
                "fix": f"Suggested fix: {p.fix}"
            })
        return solutions

