"""
Coding Super Agent - Self-improving coding assistant
CLEAN & PRODUCTION READY VERSION
"""
import ast
import re
import sys
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from collections import Counter

from brain.gemini_llm import GeminiBrain
from agents.self_improvement_engine import self_improvement_engine
from utils.prompt_templates import CODING_PROMPT, CODING_IMPROVEMENT_PROMPT


def _safe_print(msg: str) -> None:
    try:
        sys.stdout.write(f"{msg}\n")
    except UnicodeEncodeError:
        enc = getattr(sys.stdout, "encoding", None) or "ascii"
        safe_msg = msg.encode(enc, errors="replace").decode(enc, errors="replace")
        sys.stdout.write(f"{safe_msg}\n")


class CodingSuperAgent:
    def __init__(self):
        self.brain = GeminiBrain()
        self.code_history = []
        self.improvement_attempts = 0
        self.successful_generations = 0

        self.current_code = None
        self.sandbox_passed = False
        self.integration_passed = False
        self.sandbox_result = None
        self.integration_result = None
        self.function_name = None
        self._last_generation_used_fallback = False
        self.common_issues = {
            "import_error": ["ModuleNotFoundError", "ImportError"],
            "syntax_error": ["SyntaxError", "IndentationError"],
            "runtime_error": ["NameError", "TypeError", "ValueError"],
            "logic_error": ["wrong output", "infinite loop", "incorrect calculation"]
        }
        self.solution_patterns = {
            "import_error": "Check module name and installation",
            "syntax_error": "Review Python syntax and indentation",
            "runtime_error": "Add error handling and validation",
            "logic_error": "Add debug prints and test cases"
        }

    def code(self, query: str, history: Optional[List] = None) -> Dict[str, Any]:
        """Generate initial code only - no tests run automatically"""
        start_time = time.time()
        _safe_print(f"\n{'='*60}")
        _safe_print("CODE GENERATION STARTED")
        _safe_print(f"Query: {query[:100]}...")
        _safe_print(f"{'='*60}")
        history = history or []
        self._last_generation_used_fallback = False
        try:
            initial_code = self._generate_initial_code(query, {})
            code_to_use = initial_code

            validation_result = self._self_validate(code_to_use, query)
            if not validation_result["is_valid"]:
                _safe_print(f"Validation failed: {validation_result['issues']}")

            self.current_code = self._apply_improvements(code_to_use, query)
            explanation = self._generate_explanation(self.current_code, query)
            self._learn_from_generation(query, self.current_code, validation_result)
            self.sandbox_passed = False
            self.integration_passed = False
            self.sandbox_result = None
            self.integration_result = None

            func_match = re.search(r'def\s+(\w+)\s*\(', self.current_code)
            self.function_name = func_match.group(1) if func_match else None

            response_time = time.time() - start_time

            return {
                "success": True,
                "code": self.current_code,
                "generated_code": self.current_code,
                "explanation": explanation,
                "validation": validation_result,
                "sandbox_passed": False,
                "integration_passed": False,
                "ready_for_permanent": False,
                "response_time": round(response_time, 2),
                "confidence": validation_result["confidence"],
                "needs_sandbox_test": True,
                "function_name": self.function_name
            }

        except Exception as e:
            response_time = time.time() - start_time
            return {
                "success": False,
                "error": str(e),
                "response_time": round(response_time, 2),
                "suggestion": "Try simplifying your request or provide more context",
                "partial_solution": self._suggest_partial_solution(query)
            }

    def _understand_request(self, query: str, history: List) -> Dict[str, Any]:
        prompt = f"""
        Analyze this coding request:
        Query: {query}
        History: {history[-3:] if history else "No history"}
        Determine:
        1. Programming language needed
        2. Complexity level (beginner/intermediate/advanced)
        3. Key requirements
        4. Potential edge cases
        5. Related patterns or libraries
        Return as structured analysis.
        """
        response = self.brain.think(prompt)
        return {
            "language": self._detect_language(response),
            "complexity": self._detect_complexity(response),
            "requirements": self._extract_requirements(response),
            "libraries": self._detect_libraries(query),
            "estimated_lines": self._estimate_code_size(query)
        }

    def _generate_initial_code(self, query: str, analysis: Dict) -> str:
        _safe_print(f"Generating initial code for: {query[:50]}...")
        api_start = time.time()

        language = analysis.get("language", "python")
        requirements = analysis.get("requirements", [])
        libraries = analysis.get("libraries", [])

        prompt = CODING_PROMPT.format(
            query=query,
            language=language,
            requirements=", ".join(requirements),
            libraries=", ".join(libraries)
        )

        if not getattr(self.brain, "gemini_available", True):
            self._last_generation_used_fallback = True
            return self._fallback_code_from_query(query)

        response = self.brain.think(prompt)
        api_time = time.time() - api_start
        _safe_print(f"Code generation call finished in {api_time:.2f}s")
        rl = (response or "").lower()
        if (
            not response
            or "api key" in rl
            or "gemini api error" in rl
            or "quota" in rl
            or "resource_exhausted" in rl
            or "429" in rl
        ):
            self._last_generation_used_fallback = True
            return self._fallback_code_from_query(query)

        code = self._extract_code_block(response)
        code = self._fix_streamlit_duplicate_keys(code)

        self.code_history.append({
            "query": query,
            "code": code,
            "analysis": analysis,
            "timestamp": datetime.now()
        })
        return code

    def run_sandbox_test(self) -> Dict[str, Any]:
        if not self.current_code:
            return {"success": False, "error": "No code available. Generate code first."}

        _safe_print(f"\n{'='*40}")
        _safe_print("SANDBOX TEST STARTED")
        _safe_print(f"{'='*40}")

        current_code = self.current_code

        for attempt in range(5):
            _safe_print(f"\nAttempt {attempt + 1}/5...")
            result = self.test_in_sandbox(current_code)

            if result["passed"]:
                _safe_print(f"Sandbox PASSED")
                self.sandbox_passed = True
                self.sandbox_result = result
                self.current_code = current_code
                return {"success": True, "passed": True, "attempts": attempt + 1, "result": result, "code": current_code}
            else:
                _safe_print(f"Sandbox FAILED (attempt {attempt + 1}/5): {result.get('error', 'Unknown')[:100]}")
                if attempt < 4:
                    current_code = self._fix_code_from_error(current_code, result.get("error", ""), "sandbox")
                else:
                    _safe_print("Max attempts reached")

        self.sandbox_result = result
        return {"success": False, "passed": False, "result": result}

    def run_integration_test(self) -> Dict[str, Any]:
        if not self.current_code:
            return {"success": False, "error": "No code available. Generate code first."}

        _safe_print(f"\n{'='*40}")
        _safe_print("INTEGRATION TEST STARTED")
        _safe_print(f"{'='*40}")

        current_code = self.current_code

        for attempt in range(5):
            _safe_print(f"\nAttempt {attempt + 1}/5...")
            result = self.test_integration(current_code, self.function_name)

            if result["passed"]:
                _safe_print(f"Integration PASSED")
                self.integration_passed = True
                self.integration_result = result
                self.current_code = current_code
                return {"success": True, "passed": True, "attempts": attempt + 1, "result": result, "code": current_code}
            else:
                _safe_print(f"Integration FAILED (attempt {attempt + 1}/5): {result.get('error', 'Unknown')[:100]}")
                if attempt < 4:
                    current_code = self._fix_code_from_error(current_code, result.get("error", ""), "integration")
                else:
                    _safe_print("Max attempts reached")

        self.integration_result = result
        return {"success": False, "passed": False, "result": result}

    def get_status(self) -> Dict[str, Any]:
        return {
            "has_code": self.current_code is not None,
            "sandbox_passed": self.sandbox_passed,
            "integration_passed": self.integration_passed,
            "ready_for_permanent": self.sandbox_passed and self.integration_passed,
            "function_name": self.function_name
        }

    # ================================================================
    # 🔥 PRODUCTION LEVEL apply_permanent_fix
    # ================================================================
    def apply_permanent_fix(self, code: str, file_path: str = None, function_name: str = None) -> Dict[str, Any]:
        """
        Production level: AI se sahi file dhundhwao, import add karo,
        function inject karo, aur verify karo ki sab kaam kar raha hai.
        """
        import os

        _safe_print("\n" + "="*50)
        _safe_print("PRODUCTION APPLY STARTED")
        _safe_print("="*50)

        # ── Step 1: AI se decide karwao ki code kahan jayega ──────────
        target_info = self._ai_decide_target_file(code, function_name)
        target_file  = file_path or target_info["file_path"]
        needs_import = target_info["needs_import"]
        import_line  = target_info["import_line"]
        caller_files = target_info["caller_files"]   # files jo is function ko use karengi

        _safe_print(f"Target file  : {target_file}")
        _safe_print(f"Needs import : {needs_import} → {import_line}")
        _safe_print(f"Caller files : {caller_files}")

        # ── Step 2: Directory banana ───────────────────────────────────
        dir_name = os.path.dirname(target_file)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        # ── Step 3: Existing content padhna ───────────────────────────
        existing_content = ""
        if os.path.exists(target_file):
            with open(target_file, "r", encoding="utf-8") as f:
                existing_content = f.read()

        # ── Step 4: Function inject / replace ─────────────────────────
        new_content = self._inject_function(existing_content, code, function_name)

        # ── Step 5: File likhna ────────────────────────────────────────
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(new_content)
        _safe_print(f"✅ Code written to {target_file}")

        # ── Step 6: Caller files mein import add karna ─────────────────
        import_results = []
        if needs_import and import_line and caller_files:
            for caller in caller_files:
                result = self._add_import_to_file(caller, import_line)
                import_results.append(result)
                _safe_print(f"Import in {caller}: {'✅' if result['success'] else '❌'} {result.get('message','')}")

        # ── Step 7: Syntax verify ──────────────────────────────────────
        syntax_ok = self._verify_file_syntax(target_file)
        _safe_print(f"Syntax check : {'✅ OK' if syntax_ok else '❌ FAIL'}")

        # ── Step 8: Live import test ───────────────────────────────────
        import_ok = self._verify_import(target_file, function_name)
        _safe_print(f"Import test  : {'✅ OK' if import_ok else '❌ FAIL'}")

        _safe_print("="*50)

        return {
            "success": syntax_ok,
            "file": target_file,
            "function": function_name,
            "import_line": import_line,
            "import_added_to": import_results,
            "syntax_ok": syntax_ok,
            "import_ok": import_ok,
            "message": f"✅ '{function_name}' successfully added to `{target_file}`" if syntax_ok
                       else f"❌ Code saved but syntax errors found in `{target_file}`"
        }

    # ── Helper: AI decides target file ────────────────────────────────
    def _ai_decide_target_file(self, code: str, function_name: str) -> Dict[str, Any]:
        """AI se poochho ki yeh code kahan jaana chahiye."""
        import os

        # Project structure scan karo
        project_files = self._scan_project_files()

        prompt = f"""
You are a Python project architect. Analyze this function and decide where it belongs in the project.

FUNCTION NAME: {function_name or 'unknown'}

CODE:
```python
{code[:800]}
```

PROJECT FILES FOUND:
{chr(10).join(project_files[:30])}

Respond ONLY in this exact JSON format (no explanation):
{{
  "file_path": "agents/my_agent.py",
  "reason": "one line reason",
  "needs_import": true,
  "import_line": "from agents.my_agent import {function_name}",
  "caller_files": ["app.py", "agents/router.py"]
}}

RULES:
- If function name has "agent" → put in agents/ folder
- If function name has "util" or "helper" → put in utils/ folder  
- If it's a handler → put in handlers/ folder
- If it processes data → put in utils/ folder
- If caller_files are unsure, return empty list []
- import_line must be valid Python import statement
- file_path must end in .py
"""

        try:
            response = self.brain.think(prompt)
            # JSON extract karo
            json_match = re.search(r'\{.*?\}', response, re.DOTALL)
            if json_match:
                import json
                data = json.loads(json_match.group(0))
                # Validate fields
                if "file_path" not in data or not data["file_path"].endswith(".py"):
                    raise ValueError("Invalid file_path")
                return data
        except Exception as e:
            _safe_print(f"AI file decision failed: {e}, using fallback")

        # Fallback: function name se decide karo
        return self._fallback_decide_target(function_name, code)

    def _fallback_decide_target(self, function_name: str, code: str) -> Dict[str, Any]:
        """AI fail hone pe rule-based fallback."""
        fn = (function_name or "generated_code").lower()

        if any(x in fn for x in ["agent", "handler", "router"]):
            folder = "agents"
        elif any(x in fn for x in ["util", "helper", "tool", "parse", "extract", "detect"]):
            folder = "utils"
        elif any(x in fn for x in ["handler", "process"]):
            folder = "handlers"
        elif any(x in fn for x in ["test", "check", "validate"]):
            folder = "tests"
        else:
            folder = "utils"

        file_name = f"{fn}.py" if function_name else "generated_code.py"
        file_path = f"{folder}/{file_name}"

        module_path = file_path.replace("/", ".").replace(".py", "")
        import_line = f"from {module_path} import {function_name}" if function_name else ""

        return {
            "file_path": file_path,
            "reason": "Rule-based fallback decision",
            "needs_import": bool(function_name),
            "import_line": import_line,
            "caller_files": []
        }

    def _scan_project_files(self) -> List[str]:
        """Project mein saari .py files dhundho."""
        import os
        py_files = []
        skip_dirs = {".git", "__pycache__", ".venv", "venv", "node_modules", ".env"}

        for root, dirs, files in os.walk("."):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for file in files:
                if file.endswith(".py"):
                    rel_path = os.path.relpath(os.path.join(root, file), ".")
                    py_files.append(rel_path)

        return sorted(py_files)

    def _inject_function(self, existing_content: str, new_code: str, function_name: str) -> str:
        """
        Agar function already exist karta hai → replace karo.
        Nahi karta → end mein add karo.
        """
        if not function_name:
            # Function name nahi pata — bas append karo
            return existing_content.rstrip() + "\n\n\n" + new_code.strip() + "\n"

        # Check karo ki function exist karta hai
        pattern = rf'^(def {re.escape(function_name)}\s*\(.*?)(?=\n^def |\n^class |\Z)'
        existing_match = re.search(
            rf'(def {re.escape(function_name)}\b)',
            existing_content
        )

        if existing_match:
            # Function exist karta hai — pura function block replace karo
            _safe_print(f"Function '{function_name}' found — replacing...")
            # Find full function block
            func_pattern = rf'(def {re.escape(function_name)}[\s\S]*?)(?=\ndef |\nclass |\Z)'
            new_content = re.sub(func_pattern, new_code.strip(), existing_content, count=1)
            return new_content
        else:
            # Function nahi hai — end mein add karo
            _safe_print(f"Function '{function_name}' not found — appending...")
            separator = "\n\n\n" if existing_content.strip() else ""
            return existing_content.rstrip() + separator + new_code.strip() + "\n"

    def _add_import_to_file(self, file_path: str, import_line: str) -> Dict[str, Any]:
        """
        Caller file mein import add karo — agar already nahi hai toh.
        Import ko sahi jagah daalo (existing imports ke saath).
        """
        import os

        if not os.path.exists(file_path):
            return {"success": False, "message": f"File not found: {file_path}"}

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Already import hai?
        if import_line in content:
            return {"success": True, "message": "Import already exists"}

        lines = content.split("\n")
        insert_at = 0

        # Last import line dhundho
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                insert_at = i + 1

        # Import inject karo
        lines.insert(insert_at, import_line)
        new_content = "\n".join(lines)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return {"success": True, "message": f"Import added at line {insert_at + 1}"}

    def _verify_file_syntax(self, file_path: str) -> bool:
        """File ki syntax check karo."""
        import os
        if not os.path.exists(file_path):
            return False
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
            ast.parse(source)
            return True
        except SyntaxError as e:
            _safe_print(f"Syntax error in {file_path}: {e}")
            return False

    def _verify_import(self, file_path: str, function_name: str) -> bool:
        """Live import karke check karo ki function actually load hota hai."""
        import importlib.util
        try:
            spec = importlib.util.spec_from_file_location("_verify_module", file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if function_name:
                return hasattr(module, function_name)
            return True
        except Exception as e:
            _safe_print(f"Import verify failed: {e}")
            return False

    # ================================================================
    # Baaki sab same — koi change nahi
    # ================================================================

    def _check_syntax(self, code: str) -> bool:
        try:
            ast.parse(code)
            return True
        except:
            return False

    def _self_validate(self, code: str, original_query: str) -> Dict[str, Any]:
        _safe_print("Validating code...")
        syntax_valid = self._check_syntax(code)
        requirements_met = self._check_requirements(code, original_query)
        best_practices = self._check_best_practices(code)
        security_check = self._check_security(code)

        issues = []
        if not syntax_valid: issues.append("Syntax errors")
        if not requirements_met["all_met"]: issues.extend(requirements_met["missing"])
        if best_practices["issues"]: issues.extend(best_practices["issues"])
        if not security_check["safe"]: issues.append("Security concerns")

        confidence = max(0.3, 1.0 - (len(issues) * 0.2)) if issues else 1.0

        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "syntax_valid": syntax_valid,
            "requirements_met": requirements_met,
            "best_practices": best_practices,
            "security": security_check,
            "confidence": confidence,
            "suggestions": self._generate_fix_suggestions(issues, code)
        }

    def _auto_fix(self, code: str, issues: List[str]) -> str:
        self.improvement_attempts += 1
        if any("multiple `button`" in issue.lower() or "duplicate" in issue.lower() for issue in issues):
            fixed_code = self._fix_streamlit_duplicate_keys(code)
            if fixed_code != code:
                return fixed_code
        prompt = f"""
        Fix this Python code:
        Issues: {', '.join(issues)}
        Code:
        ```python
        {code}
        ```
        Provide only the fixed code.
        """
        response = self.brain.think(prompt)
        return self._extract_code_block(response) or code

    def _apply_improvements(self, code: str, query: str) -> str:
        similar_past = self._find_similar_past(query)
        if similar_past:
            return self._incorporate_past_improvements(code, similar_past)
        return self._apply_general_improvements(code)

    def _generate_explanation(self, code: str, query: str) -> str:
        if getattr(self, "_last_generation_used_fallback", False):
            return "Local fallback code was used because Gemini was unavailable or quota was exceeded."
        if not getattr(self.brain, "gemini_available", True):
            return "Offline mode: Gemini is not available (missing key or quota)."
        prompt = f"""Explain this code in simple terms:\nUser Request: {query}\nCode:\n```python\n{code}\n```\nKeep it concise."""
        answer = self.brain.think(prompt)
        rl = (answer or "").lower()
        if any(x in rl for x in ("quota", "resource_exhausted", "429", "api key")):
            return "Gemini quota/API issue detected, explanation skipped."
        return answer

    def _learn_from_generation(self, query: str, code: str, validation: Dict):
        learning_entry = {
            "query_pattern": self._extract_pattern(query),
            "code_pattern": self._extract_code_pattern(code),
            "validation_results": validation,
            "timestamp": datetime.now(),
            "success": True
        }
        self.code_history.append(learning_entry)
        if len(self.code_history) > 100:
            self.code_history = self.code_history[-100:]

    def _learn_from_failure(self, query: str, error: str):
        interaction_data = {
            "agent": "coding_super_agent",
            "query": query,
            "error": error,
            "success": False,
            "timestamp": datetime.now()
        }
        self_improvement_engine.analyze_agent_performance("coding_super_agent", interaction_data)

    def _detect_language(self, text: str) -> str:
        text_lower = text.lower()
        for lang in ["python", "javascript", "java", "c++", "html", "css", "go", "rust", "php", "ruby", "swift", "kotlin", "typescript", "sql", "bash"]:
            if lang in text_lower:
                return lang
        return "python"

    def _detect_complexity(self, text: str) -> str:
        text_lower = text.lower()
        if any(w in text_lower for w in ["advanced", "complex", "expert"]):
            return "advanced"
        if any(w in text_lower for w in ["intermediate", "medium"]):
            return "intermediate"
        return "beginner"

    def _extract_requirements(self, text: str) -> List[str]:
        requirements = []
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith(('1.', '2.', '3.', '4.', '5.', '- ', '* ', '• ')):
                clean_line = re.sub(r'^[\d\.\-\*\•]\s*', '', line)
                if clean_line and len(clean_line) > 5:
                    requirements.append(clean_line)
            elif ':' in line and len(line) < 100 and len(line) > 5:
                parts = line.split(':', 1)
                clean_part = parts[1].strip() if len(parts) > 1 else line
                if len(clean_part) > 5:
                    requirements.append(clean_part)
        if not requirements:
            sentences = re.split(r'[.!?]+', text)
            for s in sentences[:3]:
                s = s.strip()
                if len(s) > 10:
                    requirements.append(s)
        return requirements[:5]

    def _detect_libraries(self, query: str) -> List[str]:
        query_lower = query.lower()
        common_libs = {
            "numpy": ["numpy", "array", "matrix", "numerical"],
            "pandas": ["pandas", "dataframe", "csv", "excel"],
            "matplotlib": ["matplotlib", "plot", "graph", "visualize"],
            "tensorflow": ["tensorflow", "neural", "deep learning"],
            "flask": ["flask", "web", "api", "backend"],
            "requests": ["requests", "http", "api", "get", "post"],
            "sqlite": ["sqlite", "database", "sql"],
            "opencv": ["opencv", "image", "computer vision", "cv2"]
        }
        libs = [lib for lib, kw in common_libs.items() if any(k in query_lower for k in kw)]
        return list(set(libs))[:3]

    def _estimate_code_size(self, query: str) -> int:
        words = len(query.split())
        if words < 10: return 10
        if words < 30: return 30
        return 50

    def _check_requirements(self, code: str, original_query: str) -> Dict[str, Any]:
        query_words = set(original_query.lower().split())
        code_lower = code.lower()
        found_words = [w for w in query_words if w in code_lower and len(w) > 3]
        return {
            "all_met": len(found_words) > 0,
            "found": found_words,
            "missing": [w for w in query_words if w not in code_lower and len(w) > 3],
            "match_percentage": len(found_words) / max(len(query_words), 1)
        }

    def _check_best_practices(self, code: str) -> Dict[str, Any]:
        issues, suggestions = [], []
        if '#' not in code and '"""' not in code and "'''" not in code:
            issues.append("No comments")
            suggestions.append("Add comments to explain code")
        if 'def ' not in code and 'class ' not in code and len(code.split('\n')) > 10:
            issues.append("No function/class structure")
            suggestions.append("Organize code into functions/classes")
        long_lines = [i+1 for i, line in enumerate(code.split('\n')) if len(line) > 79]
        if long_lines:
            issues.append(f"Lines too long: {long_lines[:3]}")
            suggestions.append("Keep lines under 79 characters")
        return {"issues": issues, "suggestions": suggestions, "score": max(0, 10-len(issues))/10.0}

    def _check_security(self, code: str) -> Dict[str, Any]:
        security_keywords = ["eval(", "exec(", "os.system", "subprocess.call", "pickle.load", "yaml.load", "sql injection"]
        issues = [kw for kw in security_keywords if kw in code.lower()]
        return {"safe": len(issues) == 0, "issues": issues, "suggestions": ["Use safer alternatives", "Add input validation"]}

    def _generate_fix_suggestions(self, issues: List[str], code: str) -> List[str]:
        return ["Check: " + i for i in issues]

    def _find_similar_past(self, query: str) -> Optional[Dict]:
        if not self.code_history: return None
        query_words = set(query.lower().split())
        for entry in reversed(self.code_history[-20:]):
            if "query" in entry:
                common = query_words.intersection(set(entry["query"].lower().split()))
                if len(common) >= 2:
                    return entry
        return None

    def _incorporate_past_improvements(self, code: str, past_entry: Dict) -> str:
        if "code" in past_entry and len(past_entry["code"]) > len(code)*0.5:
            return past_entry["code"]
        return code

    def _apply_general_improvements(self, code: str) -> str:
        if 'import ' not in code and ('numpy' in code or 'pandas' in code):
            code = "import numpy as np\nimport pandas as pd\n\n" + code
        if '__name__' not in code and 'def ' in code:
            code += "\n\nif __name__ == '__main__':\n    pass"
        return code

    def _extract_pattern(self, query: str) -> str:
        return " ".join(query.split()[:5])

    def _extract_code_pattern(self, code: str) -> str:
        for line in code.strip().split('\n'):
            if line.strip().startswith(('def ', 'class ')):
                return line.strip()
        return ""

    def _suggest_partial_solution(self, query: str) -> str:
        return self.brain.think(f'User asked: "{query}"\nSuggest key steps, libraries, and sample code structure.')

    def _generate_fix_for_error(self, error_message: str) -> str:
        return self.brain.think(f"Analyze this error: {error_message}. Suggest a fix.")

    def _extract_code_block(self, text: str) -> str:
        if not text: return ""
        matches = re.findall(r"```python\s*(.*?)\s*```", text, re.DOTALL)
        if matches: return matches[0].strip()
        matches = re.findall(r"```\s*(.*?)\s*```", text, re.DOTALL)
        if matches: return matches[0].strip()
        lines = text.strip().split('\n')
        code_lines = []
        in_code = False
        for line in lines:
            ls = line.strip()
            if (ls.startswith(('def ', 'class ', 'import ', 'from ', 'print(', 'return ')) or
                    '=' in ls or ls.startswith(('if ', 'for ', 'while ', 'try:', 'except'))):
                in_code = True
                code_lines.append(line)
            elif in_code and ls and not ls.startswith(('#', '//', '/*')):
                code_lines.append(line)
            elif in_code and not ls:
                code_lines.append(line)
            elif in_code and any(x in line.lower() for x in ['explanation', 'output:', 'result:', 'example:']):
                break
        if code_lines: return '\n'.join(code_lines)
        return text[:500]

    def get_agent_stats(self) -> Dict[str, Any]:
        total = len(self.code_history)
        success_rate = self.successful_generations / max(total, 1)
        return {
            "total_generations": total,
            "successful_generations": self.successful_generations,
            "improvement_attempts": self.improvement_attempts,
            "success_rate": success_rate,
            "common_languages": self._get_common_languages(),
            "recent_queries": [h.get("query", "no query")[:50] for h in self.code_history[-5:]],
            "status": "operational" if success_rate > 0.5 else "needs_attention"
        }

    def _fix_streamlit_duplicate_keys(self, code: str) -> str:
        if 'st.button' not in code: return code
        import uuid

        def add_unique_key_to_button(match):
            full_button = match.group(0)
            if 'key=' in full_button: return full_button
            unique_key = str(uuid.uuid4())[:8]
            if full_button.endswith(')'):
                return full_button[:-1] + f', key="{unique_key}")'
            return full_button + f', key="{unique_key}")'

        fixed_code = re.sub(r'st\.button\s*\([^)]*\)', add_unique_key_to_button, code)
        for element in ['st.text_input', 'st.text_area', 'st.number_input', 'st.selectbox',
                        'st.multiselect', 'st.radio', 'st.checkbox', 'st.slider',
                        'st.file_uploader', 'st.color_picker', 'st.date_input', 'st.time_input']:
            fixed_code = re.sub(rf'{element}\s*\([^)]*\)', add_unique_key_to_button, fixed_code)
        return fixed_code

    def test_in_sandbox(self, code: str) -> Dict[str, Any]:
        import subprocess, tempfile, os
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name
            result = subprocess.run(['python', temp_file], capture_output=True, text=True, timeout=30)
            os.unlink(temp_file)
            return {
                "passed": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "error": result.stderr if result.returncode != 0 else None
            }
        except subprocess.TimeoutExpired:
            return {"passed": False, "error": "Timeout - code took too long"}
        except Exception as e:
            return {"passed": False, "error": str(e)}

    def test_integration(self, code: str, function_name: str = None) -> Dict[str, Any]:
        try:
            namespace = {}
            exec(code, namespace)
            if function_name and function_name in namespace:
                func = namespace[function_name]
                test_results = self._run_basic_tests(func)
                return {"passed": test_results["passed"], "results": test_results}
            return {"passed": True, "message": "Code loaded successfully"}
        except Exception as e:
            return {"passed": False, "error": str(e)}

    def _run_basic_tests(self, func) -> Dict[str, Any]:
        import inspect
        tests = []
        passed = 0
        try:
            func_name = func.__name__
            sig = inspect.signature(func)
            params = list(sig.parameters.keys())
            docstring = inspect.getdoc(func) or ""
            test_cases = []

            example_pattern = r'>>>\s*\w+\((.*?)\)\s*==\s*(.*?)(?:\n|$)'
            for match in re.findall(example_pattern, docstring):
                try:
                    inp_str, expected_str = match
                    inp = inp_str[1:-1] if inp_str.startswith("'") and inp_str.endswith("'") else (int(inp_str) if inp_str.isdigit() else inp_str)
                    expected = (True if expected_str == "True" else False if expected_str == "False" else
                                int(expected_str) if expected_str.isdigit() else
                                expected_str[1:-1] if expected_str.startswith("'") else expected_str)
                    test_cases.append((inp, expected))
                except: pass

            if not test_cases:
                fn = func_name.lower()
                if any(x in fn for x in ["palindrome"]):
                    test_cases = [("madam", True), ("hello", False), ("", True)]
                elif any(x in fn for x in ["reverse", "rev"]):
                    test_cases = [("hello", "olleh"), ("python", "nohtyp"), ("", "")]
                elif "factorial" in fn:
                    test_cases = [(0, 1), (1, 1), (5, 120)]
                elif "fib" in fn:
                    test_cases = [(0, 0), (1, 1), (5, 5), (10, 55)]
                elif "prime" in fn:
                    test_cases = [(2, True), (3, True), (4, False), (17, True)]
                elif any(x in fn for x in ["sum", "add"]) and len(params) == 2:
                    test_cases = [((2, 3), 5), ((10, 20), 30)]
                elif "square" in fn:
                    test_cases = [(2, 4), (5, 25)]
                elif "cube" in fn:
                    test_cases = [(2, 8), (3, 27)]
                else:
                    if len(params) == 1:
                        test_cases = [("test", None)]

            if not test_cases:
                if len(params) == 0:
                    try:
                        result = func()
                        tests.append({"input": "no args", "got": str(result)[:100], "passed": True})
                        passed = 1
                    except Exception as e:
                        tests.append({"error": str(e), "passed": False})
                elif len(params) == 1:
                    for sample in [0, ""]:
                        try:
                            result = func(sample)
                            tests.append({"input": sample, "got": str(result)[:100], "passed": True})
                            passed = 1
                            break
                        except: pass

            for inp, expected in test_cases:
                try:
                    result = func(*inp) if isinstance(inp, tuple) else func(inp)
                    if expected is None:
                        passed += 1
                        tests.append({"input": inp, "got": str(result)[:100], "passed": True})
                    elif result == expected:
                        passed += 1
                        tests.append({"input": inp, "expected": expected, "got": result, "passed": True})
                    else:
                        tests.append({"input": inp, "expected": expected, "got": result, "passed": False})
                except Exception as e:
                    tests.append({"input": inp, "error": str(e), "passed": False})

        except Exception as e:
            tests.append({"error": str(e), "passed": False})

        return {"passed": passed == len(tests) if tests else True, "tests": tests}

    def _get_common_languages(self) -> List[str]:
        languages = [entry.get("analysis", {}).get("language") for entry in self.code_history if "analysis" in entry]
        languages = [l for l in languages if l]
        return [lang for lang, _ in Counter(languages).most_common(3)] if languages else ["python"]

    def _fix_code_from_error(self, code: str, error_msg: str, stage: str) -> str:
        if not error_msg: return code
        prompt = f"""
The following Python code failed during {stage} testing:
ERROR: {error_msg}
CODE:
```python
{code}
```
Fix the code. Return ONLY the fixed code, no explanations.
"""
        response = self.brain.think(prompt)
        return self._extract_code_block(response)

    def _fallback_code_from_query(self, query: str) -> str:
        q = query.lower()
        if "palindrome" in q or "polindrom" in q:
            return (
                "def is_palindrome(text: str) -> bool:\n"
                "    normalized = ''.join(ch.lower() for ch in text if ch.isalnum())\n"
                "    return normalized == normalized[::-1]\n\n"
                "if __name__ == '__main__':\n"
                "    s = input('Enter text: ')\n"
                "    print('Palindrome' if is_palindrome(s) else 'Not palindrome')\n"
            )
        return (
            "def solve():\n"
            "    # Fallback template when model API is unavailable.\n"
            "    pass\n\n"
            "if __name__ == '__main__':\n"
            "    solve()\n"
        )


# ✅ Global singleton — har jagah same instance milega
import builtins
if not hasattr(builtins, '_jarvis_coding_agent'):
    builtins._jarvis_coding_agent = CodingSuperAgent()
coding_super_agent = builtins._jarvis_coding_agent