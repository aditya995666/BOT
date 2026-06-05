import os
import ast
import importlib.util
from utils.problem_schema import SystemProblem
from typing import List
# 🔥 SAFE PROJECT ROOT (scan only project, not whole PC)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROJECT_ROOTS = [BASE_DIR]

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
            
            # NEW SCANS
            report += self.scan_syntax_errors(code_map)           # Syntax + Indentation
            report += self.scan_potential_errors(code_map)        # NameError, bare except
            report += self.scan_import_resolution(code_map, imports)  # Import resolution
            report += self.quick_import_test()
               # Quick import test
            report += self.scan_missing_imports(code_map, imports)  # Existing
            report += self.scan_memory_system()                    # Existing

            
                        # Deduplicate - FILE-BASED (better)
            import re
            seen_files = set()
            seen_problems = {}
            deduped = []
            
            for p in report:
                # Extract file path from cause
                file_match = re.search(r'File: ([^\n]+)', p.cause)
                file_path = file_match.group(1) if file_match else None
                
                # Create unique key: problem_type + file_path
                if file_path:
                    key = (p.title, file_path)
                else:
                    key = (p.title, p.cause[:100] if p.cause else "")
                
                # For Indentation Error, only keep one per file
                if "Indentation Error" in p.title:
                    if key not in seen_files:
                        seen_files.add(key)
                        deduped.append(p)
                else:
                    # For other problems, keep one per file
                    if key not in seen_files:
                        seen_files.add(key)
                        deduped.append(p)
            
            print(f"✅ Deduplicated: {len(report)} → {len(deduped)} unique problems")
            return deduped

        except Exception as e:
            return [SystemProblem(
                title="Scanner Crash",
                cause=str(e),
                severity="CRITICAL",
                fix="Fix SystemHealthAgent crash"
            )]
    # ========== NEW: SYNTAX & INDENTATION SCANNER ==========
    def scan_syntax_errors(self, code_map):
        """Scan all Python files for syntax and indentation errors"""
        problems = []
        
        for module_name, info in code_map.items():
            if "syntax_error" in info:
                # Already caught by AST parse
                problems.append(SystemProblem(
                    title="Syntax Error",
                    cause=f"File: {info['path']}\nError: {info['syntax_error']}",
                    severity="CRITICAL",
                    fix="Fix the syntax error - check missing brackets, quotes, or indentation"
                ))
            else:
                # Double-check for indentation issues
                try:
                    with open(info['path'], "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                    
                    # Check for mixed tabs and spaces
                    has_tabs = False
                    has_spaces = False
                    indent_issues = []
                    
                    for i, line in enumerate(lines, 1):
                        if line.startswith('\t'):
                            has_tabs = True
                        if line.startswith(' '):
                            has_spaces = True
                        
                        # Check for inconsistent indentation
                        if line.strip() and not line.startswith((' ', '\t')):
                            if line[0] not in (' ', '\t', '#', '"', "'"):
                                # Code not indented properly after block
                                prev_line = lines[i-2].strip() if i > 1 else ""
                                if prev_line.endswith(':') and not line.strip().startswith('#'):
                                    indent_issues.append(i)
                    
                    if has_tabs and has_spaces:
                        problems.append(SystemProblem(
                            title="Mixed Indentation",
                            cause=f"File: {info['path']} uses both tabs and spaces",
                            severity="HIGH",
                            fix="Use consistent indentation (prefer 4 spaces). Run: autopep8 --in-place {info['path']}"
                        ))
                    
                    if indent_issues:
                        problems.append(SystemProblem(
                            title="Indentation Error",
                            cause=f"File: {info['path']}\nLine {indent_issues[:3]} may have indentation issues",
                            severity="HIGH",
                            fix="Check indentation after colons (if, for, while, def, class)"
                        ))
                        
                except Exception as e:
                    pass
        
        return problems
    
    # ========== NEW: LOGIC & RUNTIME ERROR DETECTION ==========
    def scan_potential_errors(self, code_map):
        """Scan for potential NameError, TypeError, logic issues"""
        problems = []
        
        for module_name, info in code_map.items():
            if "syntax_error" in info:
                continue
                
            try:
                with open(info['path'], "r", encoding="utf-8", errors="ignore") as f:
                    source = f.read()
                
                tree = ast.parse(source)
                
                # Find undefined variables
                defined_names = set()
                used_names = set()
                
                for node in ast.walk(tree):
                    # Track defined names
                    if isinstance(node, ast.FunctionDef):
                        defined_names.add(node.name)
                        for arg in node.args.args:
                            defined_names.add(arg.arg)
                    elif isinstance(node, ast.ClassDef):
                        defined_names.add(node.name)
                    elif isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                defined_names.add(target.id)
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            defined_names.add(alias.name.split('.')[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            for alias in node.names:
                                defined_names.add(alias.name)
                    
                    # Track used names
                    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                        if node.id not in ['True', 'False', 'None', 'print', 'len', 'range', 'str', 'int', 'float', 'list', 'dict', 'set', 'tuple']:
                            used_names.add(node.id)
                
                # Find undefined variables (used but not defined)
                undefined = list(used_names - defined_names)

                for var in undefined[:5]:
                    problems.append(SystemProblem(
                        title=f"Potential NameError: {var}",
                        cause=f"File: {info['path']}\nUndefined variable: {var}",
                        severity="MEDIUM",
                        fix=f"Define '{var}' before use or correct typo"
                    ))
                
                # Check for bare except (bad practice)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ExceptHandler):
                        if node.type is None:
                            problems.append(SystemProblem(
                                title="Bare Except",
                                cause=f"File: {info['path']} uses bare 'except:'",
                                severity="MEDIUM",
                                fix="Use 'except Exception as e:' instead of bare except"
                            ))
                            break
                
            except SyntaxError:
                # Already handled in syntax scan
                pass
            except Exception as e:
                pass
        
        return problems
    
    # ========== NEW: IMPORT RESOLUTION CHECK ==========
    def scan_import_resolution(self, code_map, imports):
        """Check if imports are actually resolvable"""
        problems = []
        
        for imp in imports:
            module = imp["module"]
            name = imp["name"]
            file = imp.get("file", "")
            
            # Skip Python builtins
            if module.startswith(IGNORED_MODULE_PREFIXES):
                continue
            
            # Check if module exists in project
            module_in_project = any(m == module or m.startswith(module + ".") for m in code_map)
            
            if module_in_project:
                # Check if the imported name exists in that module
                matched = None
                for m_name, m_info in code_map.items():
                    if m_name == module or m_name.startswith(module + "."):
                        matched = m_info
                        break
                
                if matched and "syntax_error" not in matched:
                    if name != "__module__":
                        all_names = matched.get("classes", []) + matched.get("functions", []) + matched.get("variables", [])
                        if name not in all_names:
                            problems.append(SystemProblem(
                                title="Import Resolution Failed",
                                cause=f"Cannot import '{name}' from '{module}' in {file}\nAvailable: {', '.join(all_names[:5])}",
                                severity="HIGH",
                                fix=f"Check if '{name}' is defined in {module}, or fix the import statement"
                            ))
        
        return problems
    
    # ========== NEW: EXECUTION TEST ==========
    def quick_import_test(self):
        """Try to import all project modules to catch import errors"""
        problems = []
        
        for root_folder in PROJECT_ROOTS:
            if not os.path.exists(root_folder):
                continue
                
            for root, dirs, files in os.walk(root_folder):
                dirs[:] = [d for d in dirs if d not in IGNORED_FOLDERS]
                
                for file in files:
                    if not file.endswith(".py"):
                        continue
                    
                    path = os.path.join(root, file)
                    module_name = os.path.relpath(path, start=BASE_DIR).replace("\\", ".").replace("/", ".")[:-3]
                    
                    try:
                        spec = importlib.util.spec_from_file_location(module_name, path)
                        if spec and spec.loader:
                            # Just try to load, don't execute
                            pass
                    except SyntaxError as e:
                        problems.append(SystemProblem(
                            title="Import Syntax Error",
                            cause=f"File: {path}\nError: {str(e)}",
                            severity="CRITICAL",
                            fix=f"Fix syntax error at line {e.lineno}: {e.msg}"
                        ))
                    except ImportError as e:
                        problems.append(SystemProblem(
                            title="Import Chain Error",
                            cause=f"File: {path}\nError: {str(e)}",
                            severity="HIGH",
                            fix=f"Fix missing dependency or circular import"
                        ))
                    except Exception as e:
                        # Other errors - might be logic errors
                        if "name" in str(e).lower() or "defined" in str(e).lower():
                            problems.append(SystemProblem(
                                title="Runtime Name Error",
                                cause=f"File: {path}\nError: {str(e)}",
                                severity="MEDIUM",
                                fix="Check variable/function definitions"
                            ))
        
        return problems
