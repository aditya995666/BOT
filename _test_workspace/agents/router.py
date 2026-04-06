import time
import re
from agents.browser_control_agent import BrowserControlAgent
import requests
from agents.system_evolution_advisor import SystemEvolutionAdvisor
from handlers.os_handler import OSHandler
from handlers.browser_handler import BrowserHandler
from handlers.research_handler import ResearchHandler
from concurrent.futures import ThreadPoolExecutor
import uuid
from threading import Lock
from agents.master_agent import master_agent  
from agents.master_autofix_agent import MasterAutoFixAgent

_AUTOCLICKER_PRINTED = False
_AGENTS_PRINTED = False
_OCR_PRINTED = False
_GLOBAL_MEMORY_PRINTED = False

# AutoClicker Agent
try:
    from agents.autoclicker_handler import autoclicker_handler
    AUTOCLICKER_AVAILABLE = True
    if not _AUTOCLICKER_PRINTED:
        print("✅ AutoClicker Agent loaded")
        _AUTOCLICKER_PRINTED = True
except ImportError:
    AUTOCLICKER_AVAILABLE = False

OS_API = "http://127.0.0.1:8000"

from utils.clarification_engine import clarification_engine
try:
    from agents.os_control_agent import OSControlAgent
    OS_AGENT_AVAILABLE = True
except ImportError:
    OS_AGENT_AVAILABLE = False

try:
    from utils.code_cleaner import extract_pure_python_code
except ImportError:
    def extract_pure_python_code(code):
        return code

try:
    from agents.pdf_agent import PDFAgent
    PDF_AGENT_AVAILABLE = True
except ImportError:
    PDF_AGENT_AVAILABLE = False

try:
    from ocr_utils import extract_text_from_pdf_ocr
    OCR_AVAILABLE = True
    if not _OCR_PRINTED:
        print("✅ OCR utils loaded")
        _OCR_PRINTED = True
except ImportError:
    OCR_AVAILABLE = False
    def extract_text_from_pdf_ocr(pdf_path):
        return "OCR not available."

def call_os_api(url, payload=None):
    try:
        headers = {"Authorization": "Bearer jarvis123"}
        r = requests.post(url, json=payload or {}, headers=headers, timeout=5)
        return r.json().get("result", "No result")
    except Exception as e:
        return f"OS API error: {e}"

def extract_failure_reason(logs: str) -> str:
    if not logs:
        return "Unknown failure"
    lines = logs.split("\n")
    keywords = ["❌","error","exception","traceback","failed","timeout",
                "syntaxerror","importerror","modulenotfounderror",
                "attributeerror","nameerror","typeerror"]
    bad = []
    for line in lines:
        if any(k in line.lower() for k in keywords):
            bad.append(line.strip())
    if bad:
        return "\n".join(bad[:5])
    return "Tests failed but no clear error found"

from datetime import datetime
from memory.global_memory import global_memory
from agents.gemini_fix_engine import generate_fix_with_gemini
from agents.master_autofix_agent import MasterAutoFixAgent

try:
    from brain.neural_engine import neural_engine
except ImportError:
    neural_engine = None

try:
    from brain.gemini_llm import GeminiBrain
    BRAIN_AVAILABLE = True
except ImportError:
    BRAIN_AVAILABLE = False
    class GeminiBrain:
        def think(self, prompt, history=None):
            return f"I am JARVIS (fallback). You said: {prompt}"

# 🌐 UNIVERSAL WEB KNOWLEDGE AGENT
try:
    from agents.web_agent import train_website, train_youtube, train_github, train_pdf, ask_knowledge
    WEB_AGENT_AVAILABLE = True
except ImportError:
    WEB_AGENT_AVAILABLE = False

# ✅ FIXED: Import real coding_super_agent
try:
    from agents.coding_super_agent import coding_super_agent
    from agents.document_agent import document_agent
    from agents.emotion_agent import detect_emotion as emotion_agent
    from agents.image_agent import image_agent
    AGENTS_AVAILABLE = True
    if not _AGENTS_PRINTED:
        print("✅ All agents loaded")
        _AGENTS_PRINTED = True
except ImportError:
    AGENTS_AVAILABLE = False
    class coding_super_agent:
        @staticmethod
        def code(q, history=None):
            return {"success": False, "error": "Coding agent not available", "stage": "failed"}
    emotion_agent = lambda x: "neutral"
    image_agent = lambda x: f"image({x})"

# 🔐 SAFE MEMORY LOADER
try:
    from memory.global_memory import global_memory
    if not _GLOBAL_MEMORY_PRINTED:
        print("🧠 Global Memory Ready")
        _GLOBAL_MEMORY_PRINTED = True
except ImportError:
    from memory.memory_manager import MemoryManager
    global_memory = MemoryManager()
    if not _GLOBAL_MEMORY_PRINTED:
        print("🧠 Global Memory Created")
        _GLOBAL_MEMORY_PRINTED = True

# SAFETY LAYERS
try:
    from agents.firmware_controller_agent import firmware_controller
    FIRMWARE_AVAILABLE = True
except ImportError:
    FIRMWARE_AVAILABLE = False
    class firmware_controller:
        @staticmethod
        def inspect(q, history=None, context=None):
            return {"allowed": True, "modified_query": q}

try:
    from agents.moderation_agent import moderate_content
    MODERATION_AVAILABLE = True
except ImportError:
    MODERATION_AVAILABLE = False  
    def moderate_content(text): return {"verdict": "SAFE"}

try:
    from agents.system_reflection_engine import system_reflect
    SYSTEM_REFLECTION_AVAILABLE = True
except ImportError:
    SYSTEM_REFLECTION_AVAILABLE = False
    def system_reflect(q): return "system reflection unavailable"

try:
    from agents.self_improvement_engine import self_improvement_engine
    IMPROVEMENT_ENGINE_AVAILABLE = True
except ImportError:
    IMPROVEMENT_ENGINE_AVAILABLE = False
    class self_improvement_engine:
        @staticmethod
        def analyze_agent_performance(a, d): pass
        @staticmethod
        def learning_cycle(): return {"status": "noop"}

try:
    from agents.humanoid_decision_layer import HumanoidDecisionLayer
    HUMANOID_AVAILABLE = True
except ImportError:
    HUMANOID_AVAILABLE = False
    class HumanoidDecisionLayer:
        def __init__(self, engine=None): pass
        def decide_agent(self, query, context=None, history=None):
            return None

# ================= ROUTER =================
class IntelligentRouter:
    def __init__(self):
        from memory.vector_store import load_existing_memory
        load_existing_memory()
        
        # From first __init__
        self._brain_instance = None
        self.memory = global_memory
        self.browser_agent = BrowserControlAgent()
        self.humanoid = HumanoidDecisionLayer(self_improvement_engine)
        self.browser_form_active = False
        self.autofix_engine = MasterAutoFixAgent()
        
        # From second __init__
        self.form_session = {
            "active": False,
            "fields": [],
            "current_index": 0,
            "answers": {}
        }
        
        # Research agent
        try:
            from agents.research_agent import ResearchAgent
            self.research_agent = ResearchAgent()
            self.RESEARCH_AVAILABLE = True
        except:
            self.research_agent = None
            self.RESEARCH_AVAILABLE = False

        # Handlers
        self.os_agent = OSControlAgent() if OS_AGENT_AVAILABLE else None
        self.os_handler = OSHandler(self.os_agent)
        self.browser_handler = BrowserHandler(self.browser_agent)
        self.research_handler = ResearchHandler("http://127.0.0.1:8000")

        # Evolution advisor
        self.evolution_advisor = None
        
        # PDF Agent
        if PDF_AGENT_AVAILABLE:
            self.pdf_agent = PDFAgent()
        else:
            self.pdf_agent = None
        self.autoclicker_handler = autoclicker_handler if AUTOCLICKER_AVAILABLE else None

        self.agents = {
            "coding": self._coding,
            "document": self._document,
            "knowledge": self._knowledge,
            "general": self._general,
            "emotion": self._emotion,
            "image": self._image,
            "voice": self._general,
            "system": self._system,
            "improvement": self._improvement,
            "weblearn": self._web_learn,
            "webask": self._web_ask,  
            "os": self._handle_os,
            "browser_action": self._handle_browser,
            "research": self._handle_research,
            "evolution": self._evolution,
            "pdf": self._handle_pdf,
            "autoclicker": self._handle_autoclicker,
            "browser_form": self._handle_browser_form,
        }

        self.executor = ThreadPoolExecutor(max_workers=3)
        self.tasks = {}
        self.task_lock = Lock()

    @property
    def brain(self):
        if self._brain_instance is None:
            self._brain_instance = GeminiBrain()
        return self._brain_instance

    def _safe_history(self, history):
        if not history:
            return []
        safe = []
        for h in history:
            if isinstance(h, str):
                safe.append(h)
            elif isinstance(h, dict):
                safe.append(f"{h.get('role','user')}: {h.get('content','')}")
            else:
                safe.append(str(h))
        return safe

    def submit_task(self, query, user_id="default", context=None, history=None):
        task_id = str(uuid.uuid4())
        with self.task_lock:
            self.tasks[task_id] = {
                "query": query,
                "status": "running",
                "result": None,
                "created_at": datetime.now().strftime("%H:%M:%S"),
                "user_id": user_id
            }
        def run():
            try:
                result = self.route(query, user_id, context, history)
                with self.task_lock:
                    self.tasks[task_id]["status"] = "completed"
                    self.tasks[task_id]["result"] = result
                    self.tasks[task_id]["completed_at"] = datetime.now().strftime("%H:%M:%S")
            except Exception as e:
                with self.task_lock:
                    self.tasks[task_id]["status"] = "failed"
                    self.tasks[task_id]["result"] = str(e)
                    self.tasks[task_id]["failed_at"] = datetime.now().strftime("%H:%M:%S")
        self.executor.submit(run)
        return task_id

    def get_tasks(self, limit=10):
        with self.task_lock:
            all_tasks = dict(self.tasks)
            if len(all_tasks) > limit:
                sorted_tasks = sorted(all_tasks.items(), key=lambda x: x[1].get('created_at', ''), reverse=True)
                return dict(sorted_tasks[:limit])
            return all_tasks

    def _extract_url(self, text):
        urls = re.findall(r'(https?://\S+)', text)
        return urls[0] if urls else None

    def _detect_intent(self, q, context=None, history=None):
        ql = q.lower()
        url = self._extract_url(q)
        
        if self.browser_form_active and hasattr(self.browser_agent, 'form_session') and self.browser_agent.form_session:
            return "browser_form"
        
        autoclicker_keywords = ['click', 'press', 'tap', 'double click', 'right click', 'type', 'keyboard', 'press key', 'scroll', 'mouse', 'auto click', 'autoclicker', 'button', 'submit', 'ok', 'cancel', 'next', 'previous', 'save', 'delete', 'edit', 'open', 'close', 'minimize', 'maximize', 'search']
        
        if any(kw in ql for kw in autoclicker_keywords):
            return "autoclicker"
        
        form_keywords = ["form bharo", "form fill", "ye form bhar do", "form fill karo", "signup karo", "login karo", "register karo", "naya account bana", "account create", "create account", "sign up", "log in"]
        
        if any(kw in ql for kw in form_keywords):
            return "browser_form"
        
        if self.browser_form_active and any(kw in ql for kw in ["yes", "no", "haan", "nahi", "ji", "skip"]):
            return "browser_form"
        
        if any(x in ql for x in ["from learned data", "from knowledge", "from stored", "learned data me", "jo maine paste kiya"]):
            return "webask"  

        research_keywords = ["research", "do research", "research about", "research on", "deep research", "internet research", "find information on", "search for topic", "look up topic", "study topic"]
        
        for keyword in research_keywords:
            if keyword in ql:
                return "research"
        
        knowledge_patterns = ["what is", "explain", "tell me about", "define", "what are", "how does", "why is", "when did", "who is", "where is", "meaning of"]
        coding_words = ["code","python","java","c++","javascript","program","script","function","algorithm","api","generate","develop","bot","app","website","bug","error","fix"]
        
        if any(word in ql for word in coding_words):
            return "coding" 
        
        for pattern in knowledge_patterns:
            if ql.startswith(pattern) or f" {pattern}" in ql:
                return "knowledge"

        if url and ("open" in ql or "visit" in ql):
            return "browser_action"
        
        if any(x in ql for x in ["learn website","train website","crawl website", "learn youtube","train youtube", "learn github","train github", "learn pdf"]):
            return "weblearn"

        if any(x in ql for x in ["from learned data","from website","from youtube","from github"]):
            return "webask"
        
        pdf_words = ["generate pdf", "create pdf", "make pdf", "pdf bana", "pdf generate", "convert to pdf", "save as pdf"]
        if any(word in ql for word in pdf_words):
            return "pdf"

        if any(x in ql for x in ["evolve system","system evolution","upgrade system","analyze architecture"]):
            return "evolution"
        
        os_words = ["open app","close","shutdown","type","click", "run python","create file","camera","screenshot", "write","enter text"]
        if any(word in ql for word in os_words):
            return "os"
        
        doc_keywords = ["document", "pdf", "file", "in the document", "according to document", "from document", "from pdf", "is document me", "document me kya"]
        if context and context.get("document_text"):
            return "document"
        
        if any(x in ql for x in ["image","photo"]): return "image"
        if any(x in ql for x in ["voice","audio","speak","bolo"]): return "voice"
        if any(x in ql for x in ["emotion","sad","happy"]): return "emotion"
        if any(x in ql for x in ["system","health","logs"]): return "system"
        if any(x in ql for x in ["improve ai","self improve"]): return "improvement"
        
        if url and ("apply" in ql or "fill" in ql):
            return "browser"
        
        browser_keywords = ["chrome open", "browser khol", "chrome kholo", "google chrome open", "site kholo", "url open", "website khol", "page open karo", "click karo", "ispe click", "button dabao", "link pe jaao", "submit kar do", "form submit"]
        if any(kw in ql for kw in browser_keywords):
            return "browser_action"

        return "general"

    def _handle_os(self, q, c, h):
        return self.os_handler.handle(q)

    def _handle_browser(self, q, c, h):
        result = self.browser_handler.handle(q, self._extract_url)
        if isinstance(result, dict):
            if "content" not in result:
                result = {"content": str(result)}
        else:
            result = {"content": str(result)}
        if "Browser closed" in str(result):
            self.browser_form_active = False
        return result

    def _handle_browser_form(self, q, c, h):
        try:
            if not self.browser_form_active:
                result = self.browser_agent.start_form_filling()
                if result["success"]:
                    self.browser_form_active = True
                    next_field = result.get("next_field")
                    if next_field:
                        return {"success": True, "content": next_field["question"]}
                    else:
                        return {"success": True, "content": result["message"]}
                else:
                    return {"success": False, "content": result["message"]}
            
            fill_result = self.browser_agent.fill_field(q)
            if not fill_result["success"]:
                self.browser_form_active = False
                return {"success": False, "content": fill_result["message"]}
            
            if fill_result.get("complete"):
                self.browser_form_active = False
                submit_result = self.browser_agent.submit_form()
                return {"success": True, "content": f"{fill_result['message']}\n\n{submit_result}"}
            
            next_field = fill_result.get("next_field")
            if next_field:
                return {"success": True, "content": next_field["question"]}
            
            if fill_result.get("done_required"):
                return {"success": True, "content": "All required fields filled! Do you want to fill optional fields? (yes/no)"}
            
            return {"success": True, "content": "Form filling in progress..."}
        except Exception as e:
            self.browser_form_active = False
            return {"success": False, "content": f"Form filling error: {str(e)}"}

    def _handle_research(self, q, c, h):
        if not self.RESEARCH_AVAILABLE:
            return {"success": False, "content": "⚠️ Research agent is not available."}
        try:
            result = self.research_handler.handle(q)
            content = result.get("content", str(result)) if isinstance(result, dict) else str(result)
            return {"success": True, "content": content, "agent_used": "research"}
        except Exception as e:
            return {"success": False, "content": f"Research failed: {str(e)}"}

    def route(self, query, user_id="default", context=None, history=None):
        if not master_agent.is_active():
            return {"success": False, "reason": "🚨 System disabled by Master Agent"}
    
        ethical_result = master_agent.analyze_ethicality(query)
        if not ethical_result["is_ethical"]:
            if context is None:
                context = {}
            context["pending_unethical"] = {
                "query": query,
                "category": ethical_result["category"],
                "reason": ethical_result["reason"],
                "confidence": ethical_result["confidence"],
                "timestamp": datetime.now().isoformat()
            }
            return {
                "success": False,
                "requires_permission": True,
                "ethical_result": ethical_result,
                "reason": f"⚠️ This command appears to be unethical: {ethical_result['reason']}",
                "content": f"⚠️ **Permission Required**\n\nThis command was flagged as potentially unethical:\n**{ethical_result['reason']}**\n\nDo you want to proceed?",
                "timestamp": datetime.now().isoformat()
            }
    
        if FIRMWARE_AVAILABLE:
            fw = firmware_controller.inspect(query, history, context)
            if not fw.get("allowed"):
                return {"success": False, "reason": "blocked by firmware"}
            query = fw.get("modified_query", query)

        if MODERATION_AVAILABLE:
            mod_result = moderate_content(query)
            if mod_result.get("action") == "BAN":
                return {"success": False, "reason": "🚫 Blocked by moderation"}
        
        start = time.time()
        intent = self._detect_intent(query, context, history)
        agent_fn = self.agents.get(intent, self._general)
        
        result = self._call_agent_with_fallback(agent_fn, query, context, history, intent)

        if isinstance(result, dict) and "content" in result:
            pass
        elif isinstance(result, str):
            result = {"content": result}
        elif isinstance(result, dict) and "result" in result:
            if isinstance(result["result"], dict) and "content" in result["result"]:
                result = {"content": result["result"]["content"]}
            else:
                result = {"content": str(result["result"])}
        else:
            result = {"content": str(result)}

        if intent == "coding" and isinstance(result, dict):
            return {
                "success": True,
                "agent_used": "coding",
                "result": {
                    "content": result.get("content", ""),
                    "generated_code": result.get("generated_code"),
                    "stage": result.get("stage"),
                    "autofix_logs": result.get("autofix_logs")
                },
                "timestamp": datetime.now().isoformat()
            }

        response = {
            "success": True,
            "agent_used": intent,
            "response_time": round(time.time() - start, 3),
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        return response

    def _call_agent_with_fallback(self, agent_fn, q, c, h, intent, brain_hint=None):
        result = {"content": "No result"}
        try:
            temp_result = agent_fn(q, c, h)
            if intent == "coding":
                return temp_result
            if isinstance(temp_result, str):
                result = {"content": temp_result}
            elif isinstance(temp_result, dict):
                if "content" in temp_result:
                    result = {"content": temp_result["content"]}
                elif "result" in temp_result and isinstance(temp_result["result"], dict):
                    if "content" in temp_result["result"]:
                        result = {"content": temp_result["result"]["content"]}
                    else:
                        result = {"content": str(temp_result["result"])}
                else:
                    result = {"content": str(temp_result)}
            else:
                result = {"content": str(temp_result)}
        except Exception as e:
            result = {"content": f"Agent failed: {e}"}
        
        if intent not in ["autoclicker", "browser_form"]:
            try:
                answer = result.get("content", "")
                if answer and len(str(answer).strip()) > 5:
                    self.memory.store(question=q, answer=str(answer), source_agent=intent, content_type="qa", confidence=0.9)
            except:
                pass
        return result

    def _document(self, q, c, h):
        document_text = c.get("document_text") if c else None
        if not document_text:
            return {"success": False, "result": {"content": "❌ No document uploaded."}}
        from agents.document_agent import document_agent
        result = document_agent(context=document_text, query=q, history=h, pdf_path=None)
        
        # 🔥 FIX: Ensure result is properly formatted
        if isinstance(result, dict):
            if "result" in result and isinstance(result["result"], dict):
                if "content" in result["result"]:
                    return result
            elif "content" in result:
                return {"success": True, "result": {"content": result["content"]}}
    
    # Fallback
    return {"success": True, "result": {"content": str(result)}}
    def _handle_pdf(self, q, c, h):
        if not PDF_AGENT_AVAILABLE or not self.pdf_agent:
            return {"success": False, "content": "❌ PDF agent not available."}
        try:
            content = re.sub(r"(generate|create|make|convert).*pdf", "", q, flags=re.I).strip()
            if not content and c and c.get("generated_code"):
                content = c.get("generated_code")
            if not content:
                content = "No content provided."
            pdf_file = self.pdf_agent.generate_pdf(content)
            return {"success": True, "type": "pdf", "file": pdf_file, "content": f"📄 PDF generated: {pdf_file}"}
        except Exception as e:
            return {"success": False, "content": f"PDF generation failed: {str(e)}"}

    def _handle_autoclicker(self, q, c, h):
        if not AUTOCLICKER_AVAILABLE or not self.autoclicker_handler:
            return {"success": False, "content": "❌ AutoClicker agent not available."}
        try:
            result = self.autoclicker_handler.handle(q)
            return {"success": result["success"], "content": result["content"]}
        except Exception as e:
            return {"success": False, "content": f"AutoClicker error: {str(e)}"}

    def _coding(self, q, c, h):
        try:
            result = coding_super_agent.code(q, h)
            generated_code = result.get("code") or result.get("generated_code", "")
            return {
                "agent_used": "coding",
                "stage": "generated",
                "generated_code": generated_code,
                "result": {"content": f"💻 Code Generated\n```python\n{generated_code}\n```"}
            }
        except Exception as e:
            return {"agent_used": "coding", "stage": "failed", "result": {"content": f"❌ Code generation failed: {e}"}}

    def _knowledge(self, q, c, h):
        return self.brain.think(q, self._safe_history(h))

    def _general(self, q, c, h):
        return self.brain.think(q, self._safe_history(h))

    def _emotion(self, q, c, h):
        return emotion_agent(q)

    def _image(self, q, c, h):
        return image_agent(q)

    def _system(self, q, c, h):
        reflection = system_reflect(q)
        return {"content": reflection, "success": True}

    def _improvement(self, q, c, h):
        return {"content": "Self-improvement cycle executed", "success": True}

    def _web_learn(self, q, c, h):
        if not WEB_AGENT_AVAILABLE:
            return {"content": "Web agent not installed", "success": False}
        try:
            url = self._extract_url(q)
            if not url:
                return {"content": "Please paste a valid URL", "success": False}
            learn_result = train_website(url)
            return learn_result
        except Exception as e:
            return {"content": str(e), "success": False}

    def _web_ask(self, q, c, h):
        if not WEB_AGENT_AVAILABLE:
            return {"content": "Web knowledge not available"}
        try:
            result = ask_knowledge(q)
            return {"content": str(result), "success": True}
        except Exception as e:
            return {"content": f"Knowledge retrieval failed: {e}", "success": False}

    def _evolution(self, q, c, h):
        return {"content": "Evolution not available", "success": False}

def get_system_problems():
    from agents.system_health_agent import SystemHealthAgent
    return SystemHealthAgent().full_system_scan()

def generate_ai_fix(problem, extra_context=""):
    from agents.gemini_fix_engine import generate_fix_with_gemini
    return generate_fix_with_gemini(problem, extra_context=extra_context)

def start_background_self_healing():
    import threading
    def run():
        time.sleep(5)
        run_full_self_heal()
    threading.Thread(target=run, daemon=True).start()

def run_full_self_heal(apply_permanent=False):
    from agents.master_autofix_agent import MasterAutoFixAgent  # ← YEH LINE ADD KARO
    logs = ["🧠 MASTER SELF-HEAL STARTED"]
    try:
        problems = get_system_problems()
        if not problems:
            logs.append("✅ System already healthy")
            return "\n".join(logs)
        logs.append(f"⚠️ {len(problems)} problems detected")
        master = MasterAutoFixAgent()
        for problem in problems:
            fix = generate_ai_fix(problem)
            result = master.run_autofix_pipeline([problem], [fix], apply_permanent=apply_permanent)
            if "success" in result.lower():
                logs.append(f"✅ Fixed: {getattr(problem, 'title', 'Unknown')}")
            else:
                logs.append(f"❌ Failed: {getattr(problem, 'title', 'Unknown')}")
    except Exception as e:
        logs.append(f"❌ Error: {e}")
    logs.append("🏁 SELF-HEAL FINISHED")
    return "\n".join(logs)

router = IntelligentRouter()