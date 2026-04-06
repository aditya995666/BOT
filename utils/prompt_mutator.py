# utils/prompt_mutator.py

import random
from utils.prompt_templates import CODING_PROMPT, GENERAL_PROMPT

class PromptMutator:
    """
    Dynamically mutate prompts to improve AI response quality
    """

    @staticmethod
    def mutate(prompt_type, query):
        mutations = [
            "Add more detailed explanation.",
            "Focus on performance optimization.",
            "Add error handling examples.",
            "Make the answer concise and clear.",
            "Include step-by-step reasoning."
        ]
        mutation = random.choice(mutations)

        if prompt_type == "coding":
            return CODING_PROMPT.format(query=query) + f"\n# NOTE: {mutation}"
        elif prompt_type == "general":
            return GENERAL_PROMPT.format(query=query) + f"\n# NOTE: {mutation}"
        else:
            return f"{query}\n# NOTE: {mutation}"
