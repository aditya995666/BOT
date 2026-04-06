"""
Gemini Fix Agent
Generates MACHINE-READABLE multi-file fixes
for the JARVIS Self-Healing AI system.
"""

from brain.gemini_llm import GeminiBrain
import os
import re

brain = GeminiBrain()

# ========== FALLBACK: Load project code if function missing ==========
def load_full_project_code():
    """Load all Python files from project"""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    code_map = {}
    
    for root, dirs, files in os.walk(project_root):
        # Skip unnecessary folders
        dirs[:] = [d for d in dirs if d not in ['__pycache__', 'venv', 'env', '.git', 'node_modules']]
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, project_root)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        code_map[rel_path] = f.read()
                except Exception:
                    code_map[rel_path] = f"# Error reading file"
    
    # Format output
    output = []
    for path, code in code_map.items():
        output.append(f"\n{'='*60}\nFILE: {path}\n{'='*60}\n{code}\n")
    
    return "\n".join(output)

# MASTER GEMINI FIX ENGINE

def generate_fix_with_gemini(problem, extra_context=""):
    """
    Generates MACHINE-READABLE multi-file fixes.
    Output format is STRICT so MasterAutoFixAgent can parse it.
    """
    
    # ------------------------------------------------------------
    # SAFE PROBLEM EXTRACTION
    # ------------------------------------------------------------
    title = getattr(problem, "title", "Unknown Problem")
    cause = getattr(problem, "cause", "Unknown Cause")
    severity = getattr(problem, "severity", "Unknown Severity")
    fix = getattr(problem, "fix", "No suggested fix provided")
    
    # Handle different problem formats
    if hasattr(problem, '__dict__'):
        problem_dict = problem.__dict__
    else:
        problem_dict = {"title": title, "cause": cause, "severity": severity}
    
    # ------------------------------------------------------------
    # LOAD FULL PROJECT CODE
    # ------------------------------------------------------------
    try:
        full_code = load_full_project_code()
    except Exception as e:
        full_code = f"# Error loading project code: {e}"
    
    # ------------------------------------------------------------
    # SIMPLIFIED BUT EFFECTIVE PROMPT
    # ------------------------------------------------------------
    prompt = f"""
You are fixing a production multi-agent AI system.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROBLEM:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Title: {title}
Cause: {cause}
Severity: {severity}
Suggested Fix: {fix}
{extra_context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FULL PROJECT CODE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{full_code[:30000]}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INSTRUCTIONS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Identify which files need changes
2. Generate COMPLETE file content (not just changes)
3. Output in this EXACT format:

FIX_START
FILE: path/to/file.py
CODE:
<full file content>
FILE: path/to/another.py
CODE:
<full file content>
FIX_END

Rules:
- Include ALL files that need changes
- Provide COMPLETE file content
- No explanations outside FIX_START/FIX_END
- No markdown backticks
- Keep existing working code intact
"""

    # ------------------------------------------------------------
    # CALL GEMINI
    # ------------------------------------------------------------
    try:
        fix_response = brain.think(prompt)
    except Exception as e:
        return _generate_fallback_fix(problem_dict, str(e))
    
    # ------------------------------------------------------------
    # VALIDATE AND CLEAN RESPONSE
    # ------------------------------------------------------------
    if not fix_response:
        return _generate_fallback_fix(problem_dict, "Empty response")
    
    # 🔥 FIX: Extract valid fix blocks even if format is slightly off
    cleaned_response = _extract_fix_blocks(fix_response)
    
    if not cleaned_response or "FILE:" not in cleaned_response:
        return _generate_fallback_fix(problem_dict, "No valid fix blocks found")
    
    return cleaned_response

# ========== HELPER FUNCTIONS ==========

def _extract_fix_blocks(response):
    """Extract valid FIX_START...FIX_END blocks from response"""
    
    # Try to find FIX_START...FIX_END pattern
    match = re.search(r'FIX_START(.*?)FIX_END', response, re.DOTALL)
    if match:
        content = match.group(1)
        # Ensure it has FILE: and CODE: blocks
        if 'FILE:' in content and 'CODE:' in content:
            return f"FIX_START{content}FIX_END"
    
    # If no valid blocks, try to extract file blocks manually
    files = []
    file_pattern = r'FILE:\s*([^\n]+)\s*CODE:\s*(.*?)(?=FILE:|$)'
    matches = re.findall(file_pattern, response, re.DOTALL)
    
    if matches:
        blocks = []
        for file_path, code in matches:
            code = code.strip()
            if code and len(code) > 10:
                blocks.append(f"FILE: {file_path.strip()}\nCODE:\n{code}")
        
        if blocks:
            return "FIX_START\n" + "\n".join(blocks) + "\nFIX_END"
    
    return None

def _generate_fallback_fix(problem_dict, error_reason):
    """Generate a fallback fix when Gemini fails"""
    
    title = problem_dict.get('title', 'Unknown')
    
    return f"""FIX_START
FILE: FIX_NOT_GENERATED.txt
CODE:
# Gemini Fix Engine failed to generate fix
# Error: {error_reason}
# Problem: {title}

# Manual intervention required
FIX_END"""