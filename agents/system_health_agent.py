import os
import ast
import importlib.util
from utils.problem_schema import SystemProblem

# 🔥 SAFE PROJECT ROOT (scan only project, not whole PC)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROJECT_ROOTS = [
    os.path.join(BASE_DIR, "agents"),
    os.path.join(BASE_DIR, "brain"),
    os.path.join(BASE_DIR, "memory"),
    os.path.join(BASE_DIR, "utils"),
    BASE_DIR
]

IGNORED_FOLDERS = ("__pycache__", ".venv", ".git", "venv", "site-packages")

IGNORED_MODULE_PREFIXES = (
    "os","sys","json","time","datetime","math","random","pickle",
    "typing","collections","pathlib","subprocess","threading",
    "streamlit","pandas","numpy","sklearn","torch","cv2",
    "openai","google","requests","bs4","selenium","matplotlib"
)


class SystemHealthAgent:

    # ---------------- CODE MAP ----------------
    def build_project_code_map(self):
        code_map = {}

        for root_folder in PROJECT_ROOTS:
            if not os.path.exists(root_folder):
                continue

            for root, dirs, files in os.walk(root_folder):
                dirs[:] = [d for d in dirs if d not in IGNORED_FOLDERS]

                for file in files:
                    if not file.endswith(".py"):
                        continue

                    path = os.path.join(root, file)

                    # 🔥 Skip huge files (prevents freeze)
                    try:
                        if os.path.getsize(path) > 300_000:
                            continue
                    except Exception:
                        continue

                    module_name = os.path.relpath(path, start=BASE_DIR)\
                                     .replace("\\", ".").replace("/", ".")[:-3]

                    classes, functions, variables = [], [], []

                    try:
                        with open(path, "r", encoding="utf-8", errors="ignore") as f:
                            source = f.read()

                        tree = ast.parse(source)

                        for node in ast.walk(tree):
                            if isinstance(node, ast.ClassDef):
                                classes.append(node.name)
                            elif isinstance(node, ast.FunctionDef):
                                functions.append(node.name)
                            elif isinstance(node, ast.Assign):
                                for t in node.targets:
                                    if isinstance(t, ast.Name):
                                        variables.append(t.id)

                        code_map[module_name] = {
                            "classes": classes,
                            "functions": functions,
                            "variables": variables,
                            "path": path
                        }

                    except SyntaxError as e:
                        code_map[module_name] = {"syntax_error": str(e), "path": path}

        return code_map

    # ---------------- IMPORTS ----------------
    def extract_all_imports(self):
        imports = []

        for root_folder in PROJECT_ROOTS:
            if not os.path.exists(root_folder):
                continue

            for root, dirs, files in os.walk(root_folder):
                dirs[:] = [d for d in dirs if d not in IGNORED_FOLDERS]

                for file in files:
                    if not file.endswith(".py"):
                        continue

                    path = os.path.join(root, file)

                    try:
                        if os.path.getsize(path) > 300_000:
                            continue
                    except Exception:
                        continue

                    try:
                        with open(path, "r", encoding="utf-8", errors="ignore") as f:
                            tree = ast.parse(f.read())

                        for node in ast.walk(tree):
                            if isinstance(node, ast.ImportFrom) and node.module:
                                for name in node.names:
                                    imports.append({"module": node.module, "name": name.name, "file": path})
                            elif isinstance(node, ast.Import):
                                for name in node.names:
                                    imports.append({"module": name.name, "name": "__module__", "file": path})

                    except Exception:
                        continue

        return imports

    # ---------------- MODULE CHECK ----------------
    def is_module_installed(self, module_name):
        try:
            return importlib.util.find_spec(module_name) is not None
        except Exception:
            return False

    # ---------------- MISSING IMPORTS ----------------
    def scan_missing_imports(self, code_map, imports):
        problems = []

        for imp in imports:
            module, name, file = imp["module"], imp["name"], imp.get("file", "")

            if module.startswith(IGNORED_MODULE_PREFIXES):
                continue

            module_in_project = any(m == module or m.startswith(module + ".") for m in code_map)
            module_installed = self.is_module_installed(module)

            if not module_in_project and not module_installed:
                problems.append(SystemProblem(
                    title="Missing Module",
                    cause=f"{module} not found (imported in {file})",
                    severity="CRITICAL",
                    fix=f"Install module: pip install {module}"
                ))
                continue

            if name == "__module__":
                continue

            if module_in_project:
                matched_module = next((code_map[m] for m in code_map if m.startswith(module)), None)
                if matched_module:
                    if name not in matched_module.get("classes", []) \
                       and name not in matched_module.get("functions", []) \
                       and name not in matched_module.get("variables", []):
                        problems.append(SystemProblem(
                            title="Missing Class/Function",
                            cause=f"{module}.{name} not found",
                            severity="HIGH",
                            fix=f"Implement {name} in {module}"
                        ))

        return problems

    # ---------------- MEMORY SYSTEM ----------------
    def scan_memory_system(self):
        problems = []

        if not os.path.exists("memory.db"):
            problems.append(SystemProblem(
                title="Database Missing",
                cause="memory.db not found",
                severity="HIGH",
                fix="Auto-create memory.db"
            ))

        if not os.path.exists("memory"):
            problems.append(SystemProblem(
                title="Memory Folder Missing",
                cause="memory folder not found",
                severity="CRITICAL",
                fix="Create memory folder"
            ))

        return problems

    # ---------------- FULL SYSTEM SCAN ----------------
    def full_system_scan(self):
        try:
            code_map = self.build_project_code_map()
            imports = self.extract_all_imports()

            report = []
            report += self.scan_missing_imports(code_map, imports)
            report += self.scan_memory_system()

            # Deduplicate
            seen = set()
            deduped = []
            for p in report:
                key = (p.title, p.cause)
                if key not in seen:
                    deduped.append(p)
                    seen.add(key)

            return deduped

        except Exception as e:
            return [SystemProblem(
                title="Scanner Crash",
                cause=str(e),
                severity="CRITICAL",
                fix="Fix SystemHealthAgent crash"
            )]
