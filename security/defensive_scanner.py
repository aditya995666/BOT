# import os
# import ast
# import re

# MALWARE_KEYWORDS = {
#     "rm -rf",
#     "curl ",
#     "wget ",
#     "powershell",
#     "base64.b64decode",
#     "socket",
#     "reverse_shell",
#     "nc ",
#     "/bin/sh",
#     "chmod +x"
# }


# DANGEROUS_FUNCTIONS = {
#     "eval",
#     "exec",
#     "compile",
#     "execfile",
#     "subprocess",
#     "system",
#     "popen"
# }


# SAFE_CONTEXTS = {
#     "coding_agent",
#     "code_analyzer",
#     "reflection_agent"
# }


# API_KEY_PATTERNS = [
#     re.compile(r"sk-[A-Za-z0-9]{32,}"),           # OpenAI
#     re.compile(r"AIza[0-9A-Za-z_-]{35}"),         # Google
#     re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}")   # Slack
# ]


# def is_safe_context(fpath: str) -> bool:
#     fpath = fpath.replace("\\", "/")
#     return any(ctx in fpath for ctx in SAFE_CONTEXTS)


# def scan_path(path: str, mode: str = "analysis"):
#     """
#     mode:
#       - analysis  → user pasted code / review / explanation (SAFE)
#       - execution → tool / agent / runtime execution (STRICT)
#     """

#     if not os.path.exists(path):
#         return {"status": "SAFE", "details": "Path does not exist"}

#     for root, _, files in os.walk(path):
#         for file in files:
#             if not file.endswith(".py"):
#                 continue

#             fpath = os.path.join(root, file)

#             try:
#                 with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
#                     source = f.read()
#                     tree = ast.parse(source, filename=fpath)

#                 for node in ast.walk(tree):
#                     if isinstance(node, ast.Call):
#                         func_name = ""

#                         if isinstance(node.func, ast.Name):
#                             func_name = node.func.id
#                         elif isinstance(node.func, ast.Attribute):
#                             func_name = node.func.attr

#                         if func_name in DANGEROUS_FUNCTIONS:
#                             if mode == "analysis":
#                                 continue

#                             if is_safe_context(fpath):
#                                 continue

#                             return {
#                                 "status": "CRITICAL",
#                                 "details": f"Unsafe runtime call '{func_name}' in {fpath}"
#                             }

#                 if mode == "analysis":
#                     lowered = source.lower()
#                     for kw in MALWARE_KEYWORDS:
#                         if kw in lowered:
#                             return {
#                                 "status": "WARNING",
#                                 "details": f"Potential malware intent detected: '{kw}' in {fpath}"
#                             }

#                 # -------------------------------
#                 # API key scan (execution only)
#                 # -------------------------------
#                 if mode == "execution":
#                     for pattern in API_KEY_PATTERNS:
#                         if pattern.search(source):
#                             return {
#                                 "status": "CRITICAL",
#                                 "details": f"Hardcoded API key detected in {fpath}"
#                             }

#             except SyntaxError:
#                 continue

#             except Exception as e:
#                 return {
#                     "status": "WARNING",
#                     "details": f"Scanner error in {fpath}: {e}"
#                 }

#     return {
#         "status": "SAFE",
#         "details": "No unsafe runtime code found"
#     }
