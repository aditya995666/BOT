import re

def extract_pure_python_code(text: str) -> str:
    """Extract pure Python code from LLM response."""
    if not text:
        return ""

    # Try to extract from markdown code block
    match = re.search(r"```python\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Try to extract from generic code block
    match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # If no code block, assume entire response is code if it looks like code
    lines = text.strip().split('\n')
    if any(line.strip().startswith(('def ', 'class ', 'import ', 'from ')) for line in lines):
        return text.strip()

    return ""