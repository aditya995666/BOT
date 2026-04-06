class ConversationBuffer:
    def __init__(self, max_turns=6):
        self.history = []
        self.max_turns = max_turns

    def add(self, role, text):
        self.history.append(f"{role}: {text}")
        self.history = self.history[-self.max_turns:]

    def get(self):
        return "\n".join(self.history)

