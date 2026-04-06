# agents/coding_utils.py

import ast
import re
from typing import Optional, List


# ───────────────────────────────────────────────
# Intent Detection (NO manual keywords)
# ───────────────────────────────────────────────

def has_code_in_query(query: str) -> bool:
    """
    Detects if the user pasted code in the query.
    """
    return bool(
        re.search(r"```|def\s+\w+\(|class\s+\w+|import\s+\w+", query)
    )


def has_error_trace(query: str) -> bool:
    """
    Detects stack traces or error-like patterns.
    """
    return bool(
        re.search(r"traceback|error|exception|syntaxerror|nameerror", query, re.I)
    )


def model_returned_code(output: str) -> bool:
    """
    Detects whether the LLM returned python code.
    """
    return bool(re.search(r"```python", output))


def is_improvement_request(query: str) -> bool:
    """
    Auto-detect improvement/debugging intent.
    """
    return has_code_in_query(query) or has_error_trace(query)


# ───────────────────────────────────────────────
# Code extraction & validation
# ───────────────────────────────────────────────

def extract_all_python_blocks(text: str) -> List[str]:
    """
    Extracts all python code blocks from model output.
    """
    return [
        block.strip()
        for block in re.findall(r"```python\s*(.*?)```", text, re.S)
    ]


def is_valid_python(code: str) -> bool:
    """
    Checks whether the given code is syntactically valid Python.
    """
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def select_best_code_block(blocks: List[str]) -> Optional[str]:
    """
    Returns the first syntactically valid python block.
    """
    for block in blocks:
        if is_valid_python(block):
            return block
    return None


# ───────────────────────────────────────────────
# Final smart validator
# ───────────────────────────────────────────────

def validate_and_fix_output(output: str, query: str) -> str:
    """
    SMART validation (production-grade).

    Behavior:
    - Conceptual answer → return as-is
    - Code expected → validate python
    - Improvement/debugging → strict validation
    """

    improvement_intent = is_improvement_request(query)
    code_intent = model_returned_code(output)

    # 🧠 CONCEPTUAL RESPONSE
    if not improvement_intent and not code_intent:
        return output.strip()

    # 🧠 CODE EXPECTED
    python_blocks = extract_all_python_blocks(output)

    if not python_blocks:
        return (
            "❌ ERROR: Expected production-ready Python code, but none was returned.\n\n"
            "Please generate FULL runnable Python code inside:\n"
            "```python\n<code>\n```"
        )

    best_code = select_best_code_block(python_blocks)

    if not best_code:
        return (
            "❌ ERROR: Generated Python code has syntax errors.\n\n"
            "```python\n" + python_blocks[0] + "\n```"
        )

    return f"```python\n{best_code}\n```"
