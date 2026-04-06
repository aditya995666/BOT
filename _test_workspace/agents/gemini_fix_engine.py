"""
Gemini Fix Agent
Generates MACHINE-READABLE multi-file fixes
for the JARVIS Self-Healing AI system.
"""

from brain.gemini_llm import GeminiBrain
from utils.full_code_loader import load_full_project_code

brain = GeminiBrain()


# MASTER GEMINI FIX ENGINE

def generate_fix_with_gemini(problem, extra_context=""):
    """
    Generates MACHINE-READABLE multi-file fixes.
    Output format is STRICT so MasterAutoFixAgent can parse it.
    
    extra_context: pehle attempt ke failure ka reason (retry ke liye)
    """

    # ------------------------------------------------------------
    # SAFE PROBLEM EXTRACTION
    # ------------------------------------------------------------
    title = getattr(problem, "title", "Unknown Problem")
    cause = getattr(problem, "cause", "Unknown Cause")
    severity = getattr(problem, "severity", "Unknown Severity")
    fix = getattr(problem, "fix", "No suggested fix provided")

    # ------------------------------------------------------------
    # LOAD FULL PROJECT CODE
    # ------------------------------------------------------------
    try:
        full_code = load_full_project_code()
    except Exception as e:
        return (
            "FIX_START\n"
            "FILE: ERROR_LOADING_PROJECT.txt\n"
            "CODE:\n"
            f"Failed to load project code: {e}\n"
            "FIX_END"
        )

    # ------------------------------------------------------------
    # 🔥 ULTRA STRONG AUTONOMOUS SELF-HEALING PROMPT
    # ------------------------------------------------------------
    prompt = f"""
You are the AUTONOMOUS SELF-HEALING ENGINE of a PRODUCTION MULTI-AGENT AI PLATFORM.

You do NOT fix a single file.
You REPAIR, CONNECT and COMPLETE the ENTIRE PROJECT.

You behave like a SENIOR STAFF ENGINEER performing a FULL REPOSITORY PATCH.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏗️ PROJECT TYPE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Production multi-agent Streamlit AI system with:

• Router entrypoint
• Security & moderation layer
• Memory manager
• AutoFix engine
• System health scanner
• OCR / Voice / NLP pipelines
• Multiple agents (image, code, pdf, chat)
• Self-improvement engine

This is a FULL REPOSITORY HEALING TASK.

You MUST assume MULTIPLE FILES are incomplete or not integrated.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 NON-NEGOTIABLE ARCHITECTURE RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Global flow MUST remain:

User → Router → Security → Agent → Execution

BUT:
⚠️ Fixing the system DOES NOT mean editing router only.

You MUST modify ANY file in the project where integration is missing.

Router is ONLY the entrypoint.
The REAL FIXES usually exist in:
• agents
• utils
• memory
• pipelines
• integrations
• autofix engine
• health scanner

If integration is missing ANYWHERE → you MUST fix it THERE.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 YOUR REAL MISSION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This is NOT a bug fix.
This is FULL SYSTEM HEALING.

You must:

1) Find missing integrations across files
2) Fix broken imports
3) Fix circular dependencies
4) Connect agents to router pipeline
5) Ensure AutoFix can modify files safely
6) Ensure SystemHealth can scan full project
7) Ensure GeminiFixEngine can patch MULTIPLE FILES
8) Ensure project runs end-to-end

If a fix is needed in ANY file → MODIFY THAT FILE.

DO NOT concentrate fixes in router.py.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 CODE MODIFICATION RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STRICT:

• Modify ANY required file in project
• Prefer editing existing files over creating new ones
• Create files ONLY if missing
• Never delete working features
• Never break Streamlit app entry
• Never remove AutoFix or SystemHealth agents
• Never rename public functions unless required

You are ALLOWED to:
✔ Add missing imports
✔ Add helper functions
✔ Connect modules together
✔ Fix integration gaps
✔ Fix runtime crashes
✔ Fix agent wiring
✔ Fix AutoFix pipeline
✔ Fix SystemHealth scanning
✔ Refactor multiple files together

This is a MULTI-FILE PATCH TASK.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 PROBLEM BUNDLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TITLE: {title}
CAUSE: {cause}
SEVERITY: {severity}
SUGGESTED FIX: {fix}

{extra_context if extra_context else ''}

These problems affect MULTIPLE FILES.

You MUST produce a SINGLE UNIFIED PATCH fixing EVERYTHING.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 FULL PROJECT CODE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{full_code}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📤 OUTPUT FORMAT (STRICT)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Return ONLY machine-readable output.

FORMAT:

FIX_START

FILE: path/to/file.py
CODE:
<FULL FILE CONTENT>

FILE: path/to/another_file.py
CODE:
<FULL FILE CONTENT>

FIX_END

STRICT:
• Multi-file output REQUIRED
• Full file content only
• No explanations
• No markdown
• No backticks
• Code must run after replacement
"""

    # ------------------------------------------------------------
    # CALL GEMINI
    # ------------------------------------------------------------
    try:
        fix_response = brain.think(prompt)
    except Exception as e:
        return (
            "FIX_START\n"
            "FILE: GEMINI_ERROR.txt\n"
            "CODE:\n"
            f"Gemini failed: {e}\n"
            "FIX_END"
        )

    # ------------------------------------------------------------
    # STRICT RESPONSE VALIDATION
    # ------------------------------------------------------------
    if not fix_response:
        return (
            "FIX_START\n"
            "FILE: EMPTY_RESPONSE.txt\n"
            "CODE:\nGemini returned empty response.\n"
            "FIX_END"
        )

    if "FIX_START" not in fix_response or "FIX_END" not in fix_response:
        return (
            "FIX_START\n"
            "FILE: INVALID_FORMAT.txt\n"
            "CODE:\nGemini returned non machine-readable output.\n"
            "FIX_END"
        )

    if "FILE:" not in fix_response or "CODE:" not in fix_response:
        return (
            "FIX_START\n"
            "FILE: PARSE_ERROR.txt\n"
            "CODE:\nNo file blocks detected in Gemini response.\n"
            "FIX_END"
        )

    return fix_response