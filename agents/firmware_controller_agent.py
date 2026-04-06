import re
from datetime import datetime
from collections import Counter


class FirmwareControllerAgent:
    """
    Central authority layer (Firmware + Boot + OS-awareness logic)
    Runs BEFORE routing and agents
    """

    def __init__(self):
        self.blocked_patterns = {
            "high": [
                r"rm\s+-rf",
                r"format\s+c:",
                r"del\s+/f",
                r"shutdown\s+-s",
                r":\(\)\s*\{\s*:\|\:&\s*\};:",
            ],
            "medium": [
                r"delete\s+system",
                r"hack",
                r"bypass\s+security",
                r"disable\s+firewall",
            ],
        }

        self.sanitize_map = {
            r"hack": "[REDACTED]",
            r"rm\s+-rf": "[BLOCKED_CMD]",
        }

        self.os_keywords = [
            "kernel", "process", "thread", "memory", "heap", "stack",
            "scheduler", "deadlock", "race condition", "interrupt",
            "io", "filesystem", "boot", "firmware", "privilege"
        ]

        self.loop_threshold = 3

    # --------------------------------------------------

    def inspect(self, query: str, history=None, context=None) -> dict:
        history = history or []

        decision = {
            "allowed": True,
            "modified_query": query,
            "reason": None,
            "severity": "low",
            "timestamp": datetime.utcnow().isoformat(),
            "os_intent": False,
            "loop_detected": False,
            "confidence_score": 1.0
        }

        q = query.lower()

        os_hits = [k for k in self.os_keywords if k in q]
        if os_hits:
            decision["os_intent"] = True
            decision["confidence_score"] -= 0.05 * len(os_hits)

        recent_queries = [
            self._extract_text(h).lower()
            for h in history[-5:]
        ]

        freq = Counter(recent_queries)

        if freq[q] >= self.loop_threshold:
            decision["loop_detected"] = True
            decision["confidence_score"] -= 0.3
            decision["reason"] = "Potential repetitive loop detected"

        for severity, patterns in self.blocked_patterns.items():
            for pattern in patterns:
                if re.search(pattern, q):
                    decision["severity"] = severity
                    decision["confidence_score"] = 0.0

                    if severity == "high":
                        decision["allowed"] = False
                        decision["reason"] = f"Blocked by firmware ({severity})"
                        self._audit(decision, query)
                        return decision

                    decision["modified_query"] = self._sanitize(query)
                    decision["reason"] = f"Sanitized by firmware ({severity})"
                    self._audit(decision, query)
                    return decision

        if context and "document" in context and "code" in q:
            decision["modified_query"] = (
                "Answer strictly using provided document context.\n\n" + query
            )
            decision["reason"] = "Boot-layer grounding enforced"
            decision["confidence_score"] -= 0.1

        decision["confidence_score"] = max(
            0.0, min(1.0, round(decision["confidence_score"], 2))
        )

        self._audit(decision, query)
        return decision

    # --------------------------------------------------

    def _extract_text(self, history_item) -> str:
        """
        Normalize history content safely
        """
        if not isinstance(history_item, dict):
            return ""

        content = history_item.get("content", "")

        if isinstance(content, str):
            return content

        if isinstance(content, dict):
            return (
                content.get("query")
                or content.get("text")
                or str(content)
            )

        return str(content)

    # --------------------------------------------------

    def _sanitize(self, text: str) -> str:
        clean = text
        for pattern, replacement in self.sanitize_map.items():
            clean = re.sub(pattern, replacement, clean, flags=re.IGNORECASE)
        return clean

    # --------------------------------------------------

    def _audit(self, decision: dict, original_query: str):
        pass


# 🔌 Singleton
firmware_controller = FirmwareControllerAgent()
