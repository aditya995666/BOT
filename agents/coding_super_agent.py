"""
Coding Super Agent - Self-improving coding assistant
CLEAN & PRODUCTION READY VERSION
"""
import ast
import re
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from collections import Counter

from brain.gemini_llm import GeminiBrain
from agents.self_improvement_engine import self_improvement_engine
from utils.prompt_templates import CODING_PROMPT, CODING_IMPROVEMENT_PROMPT

class CodingSuperAgent:
    def __init__(self):
        self.brain = GeminiBrain()
        self.code_history = []
        self.improvement_attempts = 0
        self.successful_generations = 0

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
        start_time = time.time()
        history = history or []

        try:
            understanding = self._understand_request(query, history)
            initial_code = self._generate_initial_code(query, understanding)
            code_to_use = initial_code
            max_attempts = 5

            for attempt in range(max_attempts):
                validation_result = self._self_validate(code_to_use, query)

                if validation_result["is_valid"]:
                    print(f"✅ Code valid on attempt {attempt+1}")
                    break

                print(f"⚠️ Validation failed (attempt {attempt+1})")
                print("Issues:", validation_result["issues"])
                
                # Improve code using previous issues
                code_to_use = self._auto_fix(code_to_use, validation_result["issues"])

            improved_code = self._apply_improvements(code_to_use, query)
            validation_result = self._self_validate(improved_code, query)

            if not validation_result["is_valid"]:
                fixed_code = self._auto_fix(initial_code, validation_result["issues"])
                validation_result = self._self_validate(fixed_code, query)
                code_to_use = fixed_code
            else:
                code_to_use = initial_code

            improved_code = self._apply_improvements(code_to_use, query)
            explanation = self._generate_explanation(improved_code, query)
            self._learn_from_generation(query, improved_code, validation_result)

            response_time = time.time() - start_time
            self.successful_generations += 1

            return {
                "success": True,
                "code": improved_code,
                "explanation": explanation,
                "validation": validation_result,
                "improvements_applied": self.improvement_attempts,
                "response_time": round(response_time, 2),
                "confidence": validation_result["confidence"],
                "learning_entry": {
                    "query": query[:100],
                    "success": True,
                    "timestamp": datetime.now()
                }
            }

        except Exception as e:
            response_time = time.time() - start_time
            self._learn_from_failure(query, str(e))
            return {
                "success": False,
                "error": str(e),
                "response_time": round(response_time, 2),
                "suggestion": "Try simplifying your request or provide more context",
                "partial_solution": self._suggest_partial_solution(query)
            }

    # Core Helper Functions
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
        prompt = CODING_PROMPT.format(
            query=query,
            language=analysis["language"],
            requirements=", ".join(analysis["requirements"]),
            libraries=", ".join(analysis["libraries"])
        )
        response = self.brain.think(prompt)
        code = self._extract_code_block(response)
        code = self._fix_streamlit_duplicate_keys(code)
        self.code_history.append({
            "query": query,
            "code": code,
            "analysis": analysis,
            "timestamp": datetime.now()
        })
        return code

    def _check_syntax(self, code: str) -> bool:
        try:
            ast.parse(code)
            return True
        except:
            return False

    def _self_validate(self, code: str, original_query: str) -> Dict[str, Any]:
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
    
    # 🔥 Check if issue is Streamlit duplicate key error
        if any("multiple `button`" in issue.lower() or "duplicate" in issue.lower() for issue in issues):
            print("⚠️ Detected Streamlit duplicate key issue - auto-fixing...")
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
        prompt = f"""
Explain this code in simple terms:

User Request: {query}

Code:

```python

{code}
Explain:

What the code does

Key functions/classes

How it solves the user's problem

Any important considerations

Keep it concise and beginner-friendly.
"""
        return self.brain.think(prompt)


    
    def _learn_from_generation(self, query: str, code: str, validation: Dict):
        learning_entry = {
            "query_pattern": self._extract_pattern(query),
            "code_pattern": self._extract_code_pattern(code),
            "validation_results": validation,
            "timestamp": datetime.now(),
            "success": True
        }
        self.code_history.append(learning_entry)
        if len(self.code_history) > 100: self.code_history = self.code_history[-100:]

    def _learn_from_failure(self, query: str, error: str):
        fix_suggestion = self._generate_fix_for_error(error)
        learning_entry = {
"query": query,
"error": error,
"timestamp": datetime.now(),
"success": False,
"fix_applied": fix_suggestion
}
        interaction_data = {
"agent": "coding_super_agent",
"query": query,
"error": error,
"success": False,
"timestamp": datetime.now()
}
        self_improvement_engine.analyze_agent_performance("coding_super_agent", interaction_data)


    
    # Utility Functions
    def _detect_language(self, text: str) -> str:
        text_lower = text.lower()
        for lang in ["python", "javascript", "java", "c++", "html", "css"]:
            if lang in text_lower: return lang
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
            if line.startswith(('1.', '2.', '3.', '4.', '5.', '- ', '* ', '• ')):
                clean_line = re.sub(r'^[\d\.\-\*\•]\s*', '', line)
                if clean_line and len(clean_line) > 5:
                    requirements.append(clean_line)
            elif ':' in line and len(line) < 100:
                requirements.append(line)
                if clean_line and len(clean_line) > 5: requirements.append(clean_line)
            elif ':' in line and len(line) < 100: requirements.append(line)
        if not requirements:
            sentences = re.split(r'[.!?]+', text)
            requirements = [s.strip() for s in sentences[:3] if len(s.strip()) > 10]
        return requirements[:5]

    def _detect_libraries(self, query: str) -> List[str]:
        query_lower = query.lower()
        common_libs = {
"numpy": ["numpy", "array", "matrix", "numerical"],
"pandas": ["pandas", "dataframe", "csv", "excel"],
"matplotlib": ["matplotlib", "plot", "graph", "visualize"],
"tensorflow": ["tensorflow", "tensor", "neural", "deep learning"],
"pytorch": ["pytorch", "torch"],
"flask": ["flask", "web", "api", "backend"],
"django": ["django", "web", "framework"],
"requests": ["requests", "http", "api", "get", "post"],
"sqlite": ["sqlite", "database", "sql"],
"opencv": ["opencv", "image", "computer vision", "cv2"]
}
            
        libs = [lib for lib, kw in common_libs.items() if any(k in query_lower for k in kw)]
        return list(set(libs))[:3]

    def _estimate_code_size(self, query: str) -> int:
        words = len(query.split())
        if words < 10:
            return 10
        if words < 30:
            return 30
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
        long_lines = [i+1 for i, line in enumerate(code.split('\n')) if len(line) > 79]

        if 'def ' not in code and 'class ' not in code and len(code.split('\n')) > 10:
            issues.append("No function/class structure")
            suggestions.append("Organize code into functions/classes")
        long_lines = [i+1 for i, line in enumerate(code.split('\n')) if len(line) > 79]
        if long_lines:
            issues.append(f"Lines too long: {long_lines[:3]}")
            suggestions.append("Keep lines under 79 characters")
        return {"issues": issues, "suggestions": suggestions, "score": max(0, 10-len(issues))/10.0}

    def _check_security(self, code: str) -> Dict[str, Any]:
        security_keywords = [
"eval(", "exec(", "import", "os.system", "subprocess.call",
"pickle.load", "yaml.load", "input()", "open(", "sql injection"
]
            
        issues = [kw for kw in security_keywords if kw in code.lower()]
        return {"safe": len(issues) == 0, "issues": issues, "suggestions": ["Use safer alternatives", "Add input validation"]}

    def _generate_fix_suggestions(self, issues: List[str], code: str) -> List[str]:
        return ["Check: " + i for i in issues]

    def _find_similar_past(self, query: str) -> Optional[Dict]:
        if not self.code_history:
            return None
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
        lines = code.strip().split('\n')
        for line in lines:
            if line.strip().startswith(('def ', 'class ')):
                return line.strip()
            

    def _suggest_partial_solution(self, query: str) -> str:
        prompt = f"""
User asked: "{query}"
Suggest key steps, libraries, and sample code structure.
"""
        
        return self.brain.think(prompt)

    def _generate_fix_for_error(self, error_message: str) -> str:
        prompt = f"Analyze this error: {error_message}. Suggest a fix."
        return self.brain.think(prompt)

    def _extract_code_block(self, text: str) -> str:
        """Extract code block from Gemini response - CLEAN VERSION"""
        if not text:
            return ""
        
        # Method 1: Python code block
        matches = re.findall(r"```python\s*(.*?)\s*```", text, re.DOTALL)
        if matches:
            return matches[0].strip()
        
        # Method 2: Generic code block
        matches = re.findall(r"```\s*(.*?)\s*```", text, re.DOTALL)
        if matches:
            return matches[0].strip()
        
        # Method 3: Look for function/class definitions
        lines = text.strip().split('\n')
        code_lines = []
        in_code = False
        
        for line in lines:
            line_stripped = line.strip()
            
            # Start collecting at code indicators
            if (line_stripped.startswith(('def ', 'class ', 'import ', 'from ')) or
                line_stripped.startswith(('print(', 'return ')) or
                '=' in line_stripped or
                line_stripped.startswith(('if ', 'for ', 'while ', 'try:', 'except'))):
                in_code = True
                code_lines.append(line)
            elif in_code and line_stripped and not line_stripped.startswith(('#', '//', '/*')):
                code_lines.append(line)
            elif in_code and not line_stripped:
                code_lines.append(line)
            elif in_code and any(x in line.lower() for x in ['explanation', 'output:', 'result:', 'example:']):
                break
        
        if code_lines:
            return '\n'.join(code_lines)
        
        return text[:500]  # Return first 500 chars as fallback
            
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
        """
        Fix Streamlit duplicate key error by adding unique keys to all buttons
        """
        if 'st.button' not in code:
            return code
        
        import re
        import uuid
        
        print("🔧 Fixing Streamlit duplicate button keys...")
        
        def add_unique_key_to_button(match):
            full_button = match.group(0)
            
            # Check if key already exists
            if 'key=' in full_button:
                return full_button
            
            # Generate unique key
            unique_key = str(uuid.uuid4())[:8]
            
            # Add key parameter before closing parenthesis
            if full_button.endswith(')'):
                # Insert key before the last parenthesis
                modified = full_button[:-1] + f', key="{unique_key}")'
                return modified
            elif full_button.endswith(','):
                modified = full_button + f' key="{unique_key}")'
                return modified
            else:
                # If no clear pattern, just append
                modified = full_button + f', key="{unique_key}")'
                return modified
        
        # Pattern to find all st.button calls
        button_pattern = r'st\.button\s*\([^)]*\)'
        
        # Replace all buttons with unique keys
        fixed_code = re.sub(button_pattern, add_unique_key_to_button, code)
        
        # Also fix any other Streamlit elements that might need keys
        elements_to_fix = ['st.text_input', 'st.text_area', 'st.number_input', 
                           'st.selectbox', 'st.multiselect', 'st.radio',
                           'st.checkbox', 'st.slider', 'st.file_uploader',
                           'st.color_picker', 'st.date_input', 'st.time_input']
        
        for element in elements_to_fix:
            pattern = rf'{element}\s*\([^)]*\)'
            fixed_code = re.sub(pattern, add_unique_key_to_button, fixed_code)
        
        return fixed_code

    def _get_common_languages(self) -> List[str]:
        languages = [entry.get("analysis", {}).get("language", None) for entry in self.code_history if "analysis" in entry]
        languages = [l for l in languages if l]
        return [lang for lang, _ in Counter(languages).most_common(3)] if languages else ["python"]

coding_super_agent = CodingSuperAgent()

