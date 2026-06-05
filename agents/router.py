import time
import re
from agents.browser_control_agent import BrowserControlAgent
import requests
from handlers.os_handler import OSHandler
from handlers.browser_handler import BrowserHandler
from handlers.research_handler import ResearchHandler
from concurrent.futures import ThreadPoolExecutor
import uuid
import hashlib  # Add this line
from threading import Lock
from agents.master_agent import master_agent  
from agents.master_autofix_agent import MasterAutoFixAgent

_AUTOCLICKER_PRINTED = False
_AGENTS_PRINTED = False
_OCR_PRINTED = False
_GLOBAL_MEMORY_PRINTED = False
# ========== LANGGRAPH PRODUCTION IMPORTS ==========
# Ye lines existing imports ke BAAD add karo (line ~10 ke around)
try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint import MemorySaver
    from typing import TypedDict, List, Dict, Any, Optional
    import hashlib
    import json
    from datetime import datetime
    import asyncio
    LANGGRAPH_AVAILABLE = True
    print("✅ LangGraph Production Ready")
except ImportError:
    LANGGRAPH_AVAILABLE = False
    print("⚠️ LangGraph not installed. Run: pip install langgraph")
    # Fallback - dummy classes
    class StateGraph: pass
    END = None
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

from utils.code_cleaner import extract_pure_python_code

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
# 🔥 IMPORT EPISODIC MEMORY AND NEURAL ENGINE
try:
    from memory.episodic_memory import episodic_memory
    EPISODIC_AVAILABLE = True
except ImportError:
    EPISODIC_AVAILABLE = False

try:
    from brain.neural_engine import neural_engine
    NEURAL_AVAILABLE = True
except ImportError:
    NEURAL_AVAILABLE = False
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
# 🌐 UNIVERSAL WEB KNOWLEDGE AGENT
# 🌐 UNIVERSAL WEB KNOWLEDGE AGENT
# Yeh purana hai:
# 🌐 UNIVERSAL WEB KNOWLEDGE AGENT - SINGLE IMPORT
try:
    from agents.web_agent import (
        train_website, 
        train_youtube, 
        train_github, 
        train_pdf, 
        ask_knowledge, 
        process_url_if_present, 
        is_url_processed,
        get_active_url  # ✅ IMPORTANT - yeh add karo
    )
    WEB_AGENT_AVAILABLE = True
    print("✅ Web agent loaded successfully")
except ImportError as e:
    WEB_AGENT_AVAILABLE = False
    print(f"⚠️ Web agent import warning: {e}")
    # Fallback functions
    def ask_knowledge(q): return "❌ Web agent missing. Run: pip install beautifulsoup4 gitpython youtube-transcript-api pypdf"
    def train_website(url): return {"success": False, "content": "Web agent dependencies missing"}
    def train_youtube(url): return {"success": False, "content": "YouTube agent missing"}
    def train_github(url): return {"success": False, "content": "GitHub agent missing"}
    def train_pdf(path): return {"success": False, "content": "PDF agent missing"}
    def process_url_if_present(text): return False, None
    def is_url_processed(url): return False
    def get_active_url(): return None
# 🔥 Yeh naya karo:

# Coding agent loads alone so a failure in document/image/emotion does not disable it.
try:
    from agents.coding_super_agent import coding_super_agent
    if not _AGENTS_PRINTED:
        print("✅ Coding super agent loaded")
except ImportError:
    class coding_super_agent:
        @staticmethod
        def code(q, history=None):
            return {"success": False, "error": "Coding agent not available", "stage": "failed"}

try:
    from agents.document_agent import document_agent
    from agents.emotion_agent import detect_emotion as emotion_agent
    from agents.image_agent import image_agent
    AGENTS_AVAILABLE = True
    if not _AGENTS_PRINTED:
        print("✅ Document / emotion / image agents loaded")
        _AGENTS_PRINTED = True
except ImportError:
    AGENTS_AVAILABLE = False

    def document_agent(context: str, query: str, history=None, pdf_path=None, pdf_paths=None):
        return {"success": False, "error": "Document agent not available"}

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
        self.session_context = {}  # Optional, can keep as cache

        
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
            "pdf": self._handle_pdf,
            "autoclicker": self._handle_autoclicker,
            "browser_form": self._handle_browser_form,
        }

        self.executor = ThreadPoolExecutor(max_workers=3)
        self.tasks = {}
        self.task_lock = Lock()
                # ========== LANGGRAPH PRODUCTION SETUP ==========
        if LANGGRAPH_AVAILABLE:
            self.langgraph_enabled = True
            self.langgraph_graph = self._build_langgraph()
            self.response_cache = {}
            self.cache_ttl = 3600
            self.rate_limit = {}
            print("🚀 LangGraph Production Router Active")
        else:
            self.langgraph_enabled = False
                # ========== SMART CACHE & ANALYTICS ==========
        from collections import OrderedDict
        self.smart_cache = OrderedDict()
        self.cache_max_size = 500
        self.cache_ttl_seconds = 1800  # 30 minutes
        self.analytics = {
            "total_requests": 0,
            "agent_usage": {},
            "total_response_time": 0,
            "cache_hits": 0,
            "start_time": datetime.now()
        }
        print("✅ Smart Cache & Analytics Enabled")

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
        # ========== LANGGRAPH PRODUCTION METHODS ==========
    
    def _build_langgraph(self):
        """Production-grade LangGraph workflow"""
        
        class ProductionState(TypedDict):
            query: str
            user_id: str
            context: Dict
            history: List
            intent: Optional[str]
            result: Dict
            start_time: float
            cache_hit: bool
            retry_count: int
            error: Optional[str]
        
        builder = StateGraph(ProductionState)
        
        builder.add_node("rate_limit_check", self._langgraph_rate_limit)
        builder.add_node("cache_check", self._langgraph_cache_check)
        builder.add_node("intent_detection", self._langgraph_intent)
        builder.add_node("safety_check", self._langgraph_safety)
        builder.add_node("memory_check", self._langgraph_memory)
        builder.add_node("agent_execution", self._langgraph_execute)
        builder.add_node("cache_store", self._langgraph_cache_store)
        builder.add_node("response_format", self._langgraph_format)
        
        builder.set_entry_point("rate_limit_check")
        builder.add_edge("rate_limit_check", "cache_check")
        
        builder.add_conditional_edges(
            "cache_check", 
            self._langgraph_cache_decision,
            {"hit": "response_format", "miss": "intent_detection"}
        )
        
        builder.add_edge("intent_detection", "safety_check")
        builder.add_edge("safety_check", "memory_check")
        builder.add_edge("memory_check", "agent_execution")
        builder.add_edge("agent_execution", "cache_store")
        builder.add_edge("cache_store", "response_format")
        builder.add_edge("response_format", END)
        
        return builder.compile(checkpointer=MemorySaver())
    
    def _langgraph_rate_limit(self, state):
        user_key = f"ratelimit:{state['user_id']}"
        current_minute = datetime.now().strftime("%Y%m%d%H%M")
        
        if state['user_id'] not in self.rate_limit:
            self.rate_limit[state['user_id']] = {}
        if current_minute not in self.rate_limit[state['user_id']]:
            self.rate_limit[state['user_id']][current_minute] = 0
        
        self.rate_limit[state['user_id']][current_minute] += 1
        
        if self.rate_limit[state['user_id']][current_minute] > 100:
            state['error'] = "Rate limit exceeded"
        return state
    
    def _langgraph_cache_check(self, state):
        if not self.langgraph_enabled:
            return state
        
        cache_key = hashlib.md5(f"{state['query']}:{state['user_id']}".encode()).hexdigest()
        
        if cache_key in self.response_cache:
            cache_entry = self.response_cache[cache_key]
            if (datetime.now() - cache_entry['timestamp']).seconds < self.cache_ttl:
                state['result'] = cache_entry['response']
                state['cache_hit'] = True
                return state
        
        state['cache_hit'] = False
        return state
    
    def _langgraph_cache_decision(self, state):
        return "hit" if state.get('cache_hit') else "miss"
    
    def _langgraph_intent(self, state):
        try:
            intent = self._detect_intent(state['query'], state.get('context'), state.get('history'))
            state['intent'] = intent
        except Exception as e:
            state['intent'] = "general"
            state['error'] = str(e)
        return state
    
    def _langgraph_safety(self, state):
        if not master_agent.is_active():
            state['error'] = "System disabled by Master Agent"
            return state
        
        ethical_result = master_agent.analyze_ethicality(state['query'])
        if not ethical_result.get("is_ethical", True):
            state['error'] = f"Unethical query blocked"
            return state
        
        if MODERATION_AVAILABLE:
            mod_result = moderate_content(state['query'])
            if mod_result.get("action") == "BAN":
                state['error'] = "Blocked by moderation"
                return state
        return state
    
    def _langgraph_memory(self, state):
        if NEURAL_AVAILABLE:
            neural_hint = neural_engine.get_suggestion(state['query'])
            if neural_hint:
                if state.get('context') is None:
                    state['context'] = {}
                state['context']['neural_hint'] = neural_hint
        
        if EPISODIC_AVAILABLE:
            similar_past = episodic_memory.recall(state['query'], limit=3)
            if similar_past:
                if state.get('context') is None:
                    state['context'] = {}
                state['context']['similar_past'] = similar_past
        return state
    
    def _langgraph_execute(self, state):
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                state['start_time'] = time.time()
                intent = state.get('intent', 'general')
                agent_fn = self.agents.get(intent, self._general)
                
                result = self._call_agent_with_fallback(
                    agent_fn, state['query'],
                    state.get('context', {}),
                    state.get('history', []),
                    intent
                )
                
                state['result'] = result
                state['retry_count'] = retry_count
                return state
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    state['error'] = str(e)
                    state['result'] = {"content": f"Failed: {e}"}
                    return state
                time.sleep(2 ** retry_count)
        return state
    
    def _langgraph_cache_store(self, state):
        if not state.get('cache_hit') and state.get('result') and not state.get('error'):
            cache_key = hashlib.md5(f"{state['query']}:{state['user_id']}".encode()).hexdigest()
            self.response_cache[cache_key] = {
                'response': state['result'],
                'timestamp': datetime.now()
            }
        return state
    
    def _langgraph_format(self, state):
        if state.get('error'):
            return {
                "success": False,
                "error": state['error'],
                "agent_used": state.get('intent', 'unknown'),
                "timestamp": datetime.now().isoformat()
            }
        
        response = state.get('result', {})
        if isinstance(response, dict):
            if "content" not in response:
                response = {"content": str(response)}
        elif isinstance(response, str):
            response = {"content": response}
        
        return {
            "success": True,
            "agent_used": state.get('intent', 'general'),
            "result": response,
            "cache_hit": state.get('cache_hit', False),
            "response_time": round(time.time() - state.get('start_time', time.time()), 3),
            "timestamp": datetime.now().isoformat()
        }

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
        
        # 🔥 FIX 1: SABSE PEHLE - PDF context check
        if context:
            has_pdf_paths = context.get("pdf_paths") and len(context.get("pdf_paths", [])) > 0
            has_doc_text = context.get("document_text") and len(context.get("document_text", "")) > 100
            if has_pdf_paths or has_doc_text:
                print("📄 PDF context detected - forcing document intent")
                return "document"
        
        # ========== MANUAL KEYWORDS (Only for specific agents as requested) ==========
        
        # AutoClicker - MANUAL (as requested)
        # autoclicker_keywords = ['click', 'press', 'tap', 'double click', 'right click', 'type', 'keyboard', 
        #                     'press key', 'scroll', 'mouse', 'auto click', 'autoclicker', 'button', 'submit', 
        #                     'ok', 'cancel', 'next', 'previous', 'save', 'delete', 'edit', 'open', 'close', 
        #                     'minimize', 'maximize', 'search']
        # if any(kw in ql for kw in autoclicker_keywords):
        #     return "autoclicker"a
        
        # OS Commands - MANUAL (as requested)
        os_words = ["open app", "close", "shutdown", "type", "click", "run python", "create file", 
                "camera", "screenshot", "write", "enter text"]
        if any(word in ql for word in os_words):
            return "os"
        
        # Browser Actions - MANUAL (as requested)
        browser_keywords = ["chrome open", "browser khol", "chrome kholo", "google chrome open", 
                        "site kholo", "url open", "website khol", "page open karo", "click karo", 
                        "ispe click", "button dabao", "link pe jaao", "submit kar do", "form submit"]
        if any(kw in ql for kw in browser_keywords):
            return "browser_action"
        
        # Research - MANUAL (as requested)
        research_keywords = ["research", "do research", "research about", "research on", "deep research", 
                            "internet research", "find information on", "search for topic", "look up topic", 
                            "study topic", "train yourself", "trained on"]
        for keyword in research_keywords:
            if keyword in ql:
                return "research"
        
        # PDF Generation - MANUAL
        pdf_words = ["generate pdf", "create pdf", "make pdf", "pdf bana", "pdf generate", 
                    "convert to pdf", "save as pdf"]
        if any(word in ql for word in pdf_words):
            return "pdf"
        
        # Evolution - MANUAL
        if any(x in ql for x in ["evolve system", "system evolution", "upgrade system", "analyze architecture"]):
            return "evolution"
        
        # ========== STATE/URL BASED (No keywords) ==========
        
        # Browser form active
        if self.browser_form_active and hasattr(self.browser_agent, 'form_session') and self.browser_agent.form_session:
            return "browser_form"
        
        # URL present → webask
        # URL present - AI ko chance do pehle
        url = self._extract_url(q)
        if url:
            # 🔥 AI intent detection for URL queries (same prompt use karo)
            print(f"🔗 URL detected: {url}, checking AI intent...")
            # Yahan AI detection allow karo, manual fallback baad mein
            pass  # AI detection niche already hai, isliye yahan return mat karo
        
        # Form filling - detect patterns
        form_keywords = ["form bharo", "form fill", "ye form bhar do", "form fill karo", "signup karo", 
                        "login karo", "register karo", "naya account bana", "account create", "create account", 
                        "sign up", "log in"]
        if any(kw in ql for kw in form_keywords):
            return "browser_form"
        
        # Document uploaded and asking about it
        if context and context.get("document_text"):
            doc_keywords = ["document me", "pdf me", "file me", "is document", "uploaded file", 
                        "according to document", "from document", "document me kya"]
            if any(kw in ql for kw in doc_keywords):
                return "document"
        
        # ========== AI-BASED INTENT DETECTION (For remaining: coding, knowledge, general, etc.) ==========
        
                # ========== AI-BASED INTENT DETECTION ==========
        
        print(f"🤖 AI Intent Detection: {q[:50]}...")
        
        # Check if query has pasted content (long text)
        has_pasted_content = len(q) > 500 or "```" in q
        
        try:
            prompt = f"""
Analyze this user query and classify into ONE intent.

Query: "{q}"

Intent categories:
- coding: asking for NEW code, function, program, algorithm (NOT asking to explain existing code)
- knowledge: asking to EXPLAIN or SUMMARIZE content that was just shared, or asking ANY question about pasted text
- general: casual chat, greeting, small talk, thanks, bye, how are you
- document: asking about uploaded document file (PDF/DOCX)
- webask: asking about a website URL
- image: asking about image, photo, picture
- voice: asking about voice, audio, speak
- emotion: asking about emotion, sad, happy, feeling

🔴 CRITICAL RULES:
1. If user query is LONG (>300 chars) AND contains question words → knowledge
2. If user is asking "ye kya hai", "explain this", "summary do" → knowledge
3. If user shared code/text and asking about it → knowledge
4. If user is asking to GENERATE new code (not explain existing) → coding
5. If none of above, use general

Return ONLY the intent name, nothing else.
"""
            result = self.brain.think(prompt).strip().lower()
            
            valid_intents = ["coding", "knowledge", "general", "document", "webask", 
                            "image", "voice", "emotion"]
            
            if result in valid_intents:
                print(f"🤖 AI detected intent: {result}")
                return result
                
        except Exception as e:
            print(f"AI intent detection failed: {e}")
        url = self._extract_url(q)
        if url:
            print(f"🔗 Fallback: URL detected -> webask")
            return "webask"
        # Fallback to general
        return "general"
    
    def _call_agent_with_fallback(self, agent_fn, q, c, h, intent, brain_hint=None):
        """Call agent with fallback handling"""
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
        
        # Store in memory for learning
        if intent not in ["autoclicker", "browser_form","document"]:
            try:
                answer = result.get("content", "")
                if answer and len(str(answer).strip()) > 5:
                    self.memory.store(question=q, answer=str(answer), source_agent=intent, content_type="qa", confidence=0.9)
            except:
                pass
        return result
    
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
        """PRODUCTION ROUTE WITH LANGGRAPH - ALL ORIGINAL FEATURES INTACT"""
                # ========== SMART CACHE CHECK ==========
                # ========== SMART CACHE CHECK (WITH INTENT) ==========
        # Pehle intent detect karo for cache key
        temp_intent_for_cache = self._detect_intent(query, context, history)
        
        cache_key = hashlib.md5(f"{query}:{user_id}:{temp_intent_for_cache}".encode()).hexdigest()
        
        if hasattr(self, 'smart_cache') and cache_key in self.smart_cache:
            cached_time, cached_response = self.smart_cache[cache_key]
            if (datetime.now() - cached_time).seconds < self.cache_ttl_seconds:
                self.smart_cache.move_to_end(cache_key)
                self.analytics["cache_hits"] += 1
                print(f"✅ SMART CACHE HIT: {query[:50]}... (intent: {temp_intent_for_cache})")
                return cached_response
            else:
                del self.smart_cache[cache_key]
                print(f"⏰ Cache expired for: {query[:50]}...")
        
        # ========== LANGGRAPH WRAPPER (PRODUCTION) ==========
        if self.langgraph_enabled:
            initial_state = {
                "query": query,
                "user_id": user_id,
                "context": context or {},
                "history": history or [],
                "intent": None,
                "result": {},
                "start_time": time.time(),
                "cache_hit": False,
                "retry_count": 0,
                "error": None
            }
            try:
                final_state = self.langgraph_graph.invoke(initial_state)
                if final_state and final_state.get("result"):
                    return final_state
            except Exception as e:
                print(f"⚠️ LangGraph failed: {e}, using original route")
        
        # ========== ORIGINAL ROUTE - NO FEATURE MISSING ==========
        
        # ========== EPISODIC MEMORY & NEURAL ENGINE ==========
        if NEURAL_AVAILABLE:
            neural_hint = neural_engine.get_suggestion(query)
            if neural_hint:
                print(f"🧠 Neural hint: {neural_hint.get('action', 'be careful')}")
                context = context or {}
                context["neural_hint"] = neural_hint
        
        if EPISODIC_AVAILABLE:
            similar_past = episodic_memory.recall(query, limit=3)
            if similar_past:
                print(f"📚 Found {len(similar_past)} similar past interactions")
                context = context or {}
                context["similar_past"] = similar_past
        
        # ========== STEP 0: SESSION CONTEXT MEMORY ==========
        is_content_shared = (
            "```" in query or
            "def " in query or
            "class " in query or
            "import " in query or
            "{" in query and "}" in query or
            "<" in query and ">" in query or
            len(query) > 200
        )
        
        if is_content_shared:
            content_type = "unknown"
            if "def " in query or "class " in query or "import " in query:
                content_type = "code"
            elif "{" in query and "}" in query:
                content_type = "json"
            elif "<" in query and ">" in query:
                content_type = "html/xml"
            else:
                content_type = "text"
            
            self.memory.store_conversation_context(user_id, "last_content", query)
            self.memory.store_conversation_context(user_id, "last_content_type", content_type)
            print(f"📝 [CONTEXT] Stored {content_type} content for user {user_id}")
        
        reference_keywords = [
            "esko", "isko", "ye", "yeh", "this", "that", "it", "these",
            "is content ko", "this content", "that content",
            "upar wala", "previous", "last", "pehle wala",
            "jo maine bheja", "paste kiya", "share kiya"
        ]
        
        if any(kw in query.lower() for kw in reference_keywords):
            previous_content = self.memory.get_conversation_context(user_id, "last_content")
            content_type = self.memory.get_conversation_context(user_id, "last_content_type")
            
            if previous_content:
                context = context or {}
                context["previous_content"] = previous_content
                context["previous_content_type"] = content_type or "content"
                context["has_previous_context"] = True
                
                print(f"📝 [CONTEXT] Retrieved previous {content_type} for user {user_id}")
                
                if history is None:
                    history = []
                history.append({
                    "role": "user",
                    "content": f"[Previous content shared by user]:\n{previous_content}\n\n[Current query]: {query}"
                })
        
        # ========== INTENT DETECTION ==========
        temp_intent = self._detect_intent(query, context, history)
        
        # ========== CODING INTENT DIRECT HANDLING ==========
        if temp_intent == "coding":
            print("🎯 Coding intent - calling coding agent directly")
            intent = "coding"
            agent_fn = self.agents.get(intent, self._general)
            result = self._call_agent_with_fallback(agent_fn, query, context, history, intent)
            return result
        
        # ========== CLARIFICATION CHECK ==========
        skip_clarification = False
        
        if temp_intent == "document":
            if context and context.get("pdf_paths") and len(context.get("pdf_paths", [])) > 0:
                skip_clarification = True
                print("📄 Skipping clarification - PDF already uploaded")
            elif context and context.get("document_text") and len(context.get("document_text", "")) > 100:
                skip_clarification = True
                print("📄 Skipping clarification - Document text available")
        
        if temp_intent == "coding":
            skip_clarification = True
        
        if self._extract_url(query):
            skip_clarification = True
        
        if not skip_clarification:
            clar_result = clarification_engine.analyze_query(
                query=query,
                intent=temp_intent,
                history=history or [],
                user_id=user_id
            )
            
            if clar_result.get("unclear") and clar_result.get("question"):
                return {
                    "success": True,
                    "agent_used": "clarification",
                    "result": {
                        "content": f"🤔 **Clarification Needed:**\n\n{clar_result['question']}",
                        "needs_clarification": True,
                        "original_query": query
                    },
                    "timestamp": datetime.now().isoformat()
                }
        
        # ========== URL PROCESSING ==========
        url = self._extract_url(query)
        
        if url and WEB_AGENT_AVAILABLE:
            from agents.web_agent import process_url_if_present, is_url_processed, ask_knowledge
            
            if not is_url_processed(url):
                process_url_if_present(url)
                
                if len(query.strip().split()) <= 2:
                    return {
                        "success": True,
                        "agent_used": "web_auto",
                        "result": {
                            "content": f"🔍 **URL Detected: {url}**\n\n"
                                    f"I'm learning about this website in the background.\n"
                                    f"You can ask me questions about it in a few moments!\n\n"
                                    f"💡 Try asking:\n"
                                    f"- 'What is this website about?'\n"
                                    f"- 'Give me summary of this site'\n"
                                    f"- '{url} me kya likha hai?'"
                        },
                        "timestamp": datetime.now().isoformat()
                    }
            
            ask_keywords = ['kya hai', 'what is', 'tell me', 'about', 'summary', 
                        'content', 'bataye', 'padhkar', 'explain', 'describe']

            if any(kw in query.lower() for kw in ask_keywords):
                answer = ask_knowledge(query)
                
                if answer and "No relevant knowledge" not in answer and len(answer) > 50:
                    return {
                        "success": True,
                        "agent_used": "web_answer",
                        "result": {"content": f"📚 **Answer from learned data:**\n\n{answer}"},
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "success": True,
                        "agent_used": "web_answer",
                        "result": {"content": f"📚 I've learned about {url} but couldn't find specific info. Try asking differently!"},
                        "timestamp": datetime.now().isoformat()
                    }
        
        # ========== MASTER AGENT CHECK ==========
        if not master_agent.is_active():
            return {"success": False, "reason": "🚨 System disabled by Master Agent"}
        
        # ========== ETHICAL CHECK ==========
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
        
        # ========== MEMORY CHECK ==========
        try:
            if len(query.strip()) > 3:
                has_pdf = (
                    context and (
                        (context.get("pdf_paths") and len(context.get("pdf_paths", [])) > 0)
                        or
                        (context.get("document_text") and len(context.get("document_text", "")) > 100)
                    )
                )
                
                if has_pdf:
                    print("📄 PDF context present - skipping memory")
                else:
                    mem_answer = self.memory.query_knowledge(query, top_k=5)
                    if mem_answer and len(str(mem_answer).strip()) > 30:
                        
                        summary_prompt = f"""User ne poocha: "{query}"

Niche website ka raw content hai. Iske basis par ek clean, helpful summary do.
- Bullet points use karo
- Simple language mein likho  
- Raw text copy mat karo
- 150 words se zyada mat likho

Raw content:
{str(mem_answer)[:2000]}"""

                        try:
                            clean_summary = self.brain.think(summary_prompt)
                            return {
                                "success": True,
                                "agent_used": "knowledge_memory",
                                "result": {"content": f"📚 **Summary:**\n\n{clean_summary}"},
                                "timestamp": datetime.now().isoformat()
                            }
                        except:
                            return {
                                "success": True,
                                "agent_used": "knowledge_memory", 
                                "result": {"content": f"📚 **From stored knowledge:**\n\n{mem_answer}"},
                                "timestamp": datetime.now().isoformat()
                            }
        except Exception as e:
            print(f"Memory knowledge query error: {e}")
        
        # ========== SAFETY LAYERS ==========
        if FIRMWARE_AVAILABLE:
            fw = firmware_controller.inspect(query, history, context)
            if not fw.get("allowed"):
                return {"success": False, "reason": "blocked by firmware"}
            query = fw.get("modified_query", query)

        if MODERATION_AVAILABLE:
            mod_result = moderate_content(query)
            if mod_result.get("action") == "BAN":
                return {"success": False, "reason": "🚫 Blocked by moderation"}
        
        # ========== FINAL AGENT EXECUTION ==========
        start = time.time()
        intent = temp_intent
        agent_fn = self.agents.get(intent, self._general)

        result = self._call_agent_with_fallback(agent_fn, query, context, history, intent)
        
        # ========== RESULT FORMATTING ==========
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

        # ========== CODING AGENT SPECIAL HANDLING ==========
        if intent == "coding" and isinstance(result, dict):
            content = result.get("content", "")
            if not content and "result" in result:
                content = result["result"].get("content", "")
            
            return {
                "success": True,
                "agent_used": "coding",
                "result": {
                    "content": content,
                    "generated_code": result.get("generated_code") or result.get("result", {}).get("generated_code"),
                    "stage": result.get("stage") or result.get("result", {}).get("stage"),
                    "autofix_logs": result.get("autofix_logs") or result.get("result", {}).get("autofix_logs")
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
        
        # ========== STORE IN EPISODIC MEMORY & NEURAL ENGINE ==========
        if EPISODIC_AVAILABLE:
            episodic_memory.remember({
                "query": query,
                "response": response,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat()
            })
        
        if NEURAL_AVAILABLE:
            neural_engine.learn_from_interaction({
                "query": query,
                "response": response,
                "user_id": user_id
            })
                # ========== UPDATE ANALYTICS & SMART CACHE ==========
                # ========== UPDATE ANALYTICS & SMART CACHE ==========
        response_time = round(time.time() - start, 3)
        
        # Update analytics
        self.analytics["total_requests"] += 1
        self.analytics["agent_usage"][intent] = self.analytics["agent_usage"].get(intent, 0) + 1
        self.analytics["total_response_time"] += response_time
        
        # ========== FIX: Only cache complete responses ==========
        should_cache = False
        
        if response.get("success", True) and hasattr(self, 'smart_cache'):
            if intent == "coding":
                # For coding responses, only cache if generated_code is complete (> 100 chars)
                generated_code = response.get("generated_code") or response.get("result", {}).get("generated_code", "")
                if len(generated_code) > 100:
                    should_cache = True
                    print(f"💾 Caching complete coding response ({len(generated_code)} chars)")
                else:
                    print(f"⚠️ Skipping cache - incomplete coding response ({len(generated_code)} chars)")
            else:
                # Non-coding responses - cache normally
                should_cache = True
        
        if should_cache:
            if len(self.smart_cache) >= self.cache_max_size:
                self.smart_cache.popitem(last=False)
            self.smart_cache[cache_key] = (datetime.now(), response)
            print(f"💾 SMART CACHE STORED: {query[:50]}...")
        
        # Print analytics summary every 100 requests
        if self.analytics["total_requests"] % 100 == 0:
            avg_time = self.analytics["total_response_time"] / self.analytics["total_requests"]
            cache_rate = (self.analytics["cache_hits"] / self.analytics["total_requests"]) * 100
            print(f"📊 ANALYTICS: {self.analytics['total_requests']} req | Avg: {avg_time:.2f}s | Cache: {cache_rate:.1f}%")
        
        return response
    def _document(self, q, c, h):
        # 🔥 Get document text from context
        document_text = c.get("document_text") if c else None
        
        # 🔥 CRITICAL: Get PDF paths from context
        pdf_paths = c.get("pdf_paths", []) if c else []
        
        # 🔥 Also check session state for PDF paths
        if not pdf_paths and hasattr(self, 'memory'):
            # Try to get from memory manager
            stored_paths = self.memory.get_conversation_context("default", "pdf_paths")
            if stored_paths:
                import json
                try:
                    pdf_paths = json.loads(stored_paths)
                except:
                    pdf_paths = []
        
        print(f"📄 [ROUTER] Document query: {q[:50]}...")
        print(f"📄 [ROUTER] Has document_text: {bool(document_text)}")
        print(f"📄 [ROUTER] PDF paths count: {len(pdf_paths)}")
        
        if not document_text and not pdf_paths:
            return {"success": False, "result": {"content": "❌ No document uploaded. Please upload a PDF or text file first."}}
        
        from agents.document_agent import document_agent
        
        # Pass pdf_paths to document_agent
        result = document_agent(
            context=document_text or "", 
            query=q, 
            history=h, 
            pdf_path=None,
            pdf_paths=pdf_paths
        )
        
        # Ensure result is properly formatted
        if isinstance(result, dict):
            if "result" in result and isinstance(result["result"], dict):
                if "content" in result["result"]:
                    return result
            elif "content" in result:
                return {"success": True, "result": {"content": result["content"]}}
        
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
            print("\n" + "="*60)
            print("🔍 [ROUTER DEBUG] _coding() CALLED")
            print(f"🔍 [ROUTER DEBUG] Query: {q[:100]}")
            print("="*60)
            
            # ========== DETECT IF USER WANTS MULTI-FILE PROJECT ==========
            project_keywords = [
                'project', 'full code', 'complete code', 'multi file', 
                'multiple files', 'folder', 'app banaye', 'pura code', 
                'system banaye', 'chatbot project', 'api project',
                'web app project', 'cli tool', 'scraper'
            ]
            
            is_project_request = any(kw in q.lower() for kw in project_keywords)
            
            if is_project_request:
                print("🎯 PROJECT REQUEST DETECTED - Generating multi-file project")
                result = coding_super_agent.generate_full_project(q)
            else:
                print("🎯 CODE REQUEST DETECTED - Generating single file")
                result = coding_super_agent.code(q, h)
            
            print(f"🔍 [ROUTER DEBUG] result.get('success'): {result.get('success')}")
            print(f"🔍 [ROUTER DEBUG] result keys: {result.keys() if result else 'None'}")
            
            if result.get("success"):
                # Check if this is a multi-file project response
                if result.get("is_multi_file"):
                    # Multi-file project response
                    output = result.get("content", "")
                    files = result.get("files", [])
                    project_name = result.get("project_name", "project")
                    
                    return_dict = {
                        "agent_used": "coding",
                        "content": output,
                        "files": files,
                        "project_name": project_name,
                        "is_multi_file": True,
                        "success": True,
                        "stage": "generated"
                    }
                    
                    # Also store first file as generated_code for compatibility
                    if files and len(files) > 0:
                        return_dict["generated_code"] = files[0].get("content", "")
                    
                    print(f"🔍 [ROUTER DEBUG] Multi-file project with {len(files)} files")
                    return return_dict
                else:
                    # Single file code response
                    generated_code = result.get("code", "")
                    explanation = result.get("explanation", "")
                    
                    print(f"🔍 [ROUTER DEBUG] generated_code length: {len(generated_code)}")
                    print(f"🔍 [ROUTER DEBUG] explanation length: {len(explanation) if explanation else 0}")
                    
                    output = f"💻 **Code Generated**\n\n```python\n{generated_code}\n```\n\n"
                    if explanation:
                        output += f"📖 **Explanation:**\n{explanation}\n"
                    
                    return_dict = {
                        "agent_used": "coding",
                        "content": output,
                        "generated_code": generated_code,
                        "success": True,
                        "stage": "generated",
                        "is_multi_file": False
                    }
                    
                    print(f"🔍 [ROUTER DEBUG] RETURNING: agent_used={return_dict['agent_used']}")
                    return return_dict
            else:
                print(f"🔍 [ROUTER DEBUG] FAILED: {result.get('error', 'Unknown error')}")
                print("="*60 + "\n")
                return {
                    "agent_used": "coding",
                    "content": f"❌ Code generation failed: {result.get('error', 'Unknown error')}",
                    "success": False
                }
        except Exception as e:
            print(f"🔍 [ROUTER DEBUG] EXCEPTION: {str(e)}")
            print("="*60 + "\n")
            return {
                "agent_used": "coding",
                "content": f"❌ Code generation failed: {str(e)}",
                "success": False
            }
    def _knowledge(self, q, c, h):
        """Knowledge agent - handles questions about pasted content"""
        
        print(f"📚 [KNOWLEDGE AGENT] Processing: {q[:100]}...")
        
        # Get last shared content from memory (if user pasted earlier)
        last_content = self.memory.get_conversation_context("default", "last_content")
        
        # Check if current query has pasted content (long text)
        has_pasted_content = len(q) > 500 or "```" in q
        
        if has_pasted_content or last_content:
            # Use the content (either from current query or memory)
            content_to_use = q if has_pasted_content else last_content
            
            # Limit content length to avoid token issues
            if len(content_to_use) > 3000:
                content_to_use = content_to_use[:3000] + "..."
            
            prompt = f"""
You are JARVIS, a helpful AI assistant.

USER'S QUESTION: {q if not has_pasted_content else "Explain/summarize this content"}

CONTENT TO ANALYZE:
{content_to_use}

INSTRUCTIONS:
1. If user asked "ye kya hai" or "what is this" → Give a clear summary of what this content is about
2. If user asked "explain" → Explain step by step
3. If user asked "summary" → Provide a concise summary
4. If user asked a specific question → Answer based ONLY on this content
5. Be helpful and conversational

YOUR ANSWER:
"""
            response = self.brain.think(prompt)
            return response
        else:
            # No pasted content, use regular brain
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
            return {"content": "Web knowledge not available", "success": False}
        try:
            result = ask_knowledge(q)
            # Better formatting
            if result and "No relevant knowledge" not in result:
                return {"content": f"📚 **Information:**\n\n{result}", "success": True}
            else:
                return {"content": "📚 No relevant knowledge found. Share a URL first and I'll learn about it!", "success": True}
        except Exception as e:
            return {"content": f"Knowledge retrieval failed: {e}", "success": False}
    
    

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
    logs = ["🧠 MASTER SELF-HEAL STARTED"]
    try:
        problems = get_system_problems()
        if not problems:
            logs.append("✅ System already healthy")
            return "\n".join(logs)
        logs.append(f"⚠️ {len(problems)} problems detected")
        
        # ❌ AUTO-FIX DISABLED - Only manual button click!
        # master = MasterAutoFixAgent()
        # for problem in problems:
        #     fix = generate_ai_fix(problem)  # TOKEN WASTE!
        #     result = master.run_autofix_pipeline(...)
        
        logs.append("💡 Click 'Generate & Test Fix' button to fix")
    except Exception as e:
        logs.append(f"❌ Error: {e}")
    logs.append("🏁 SCAN COMPLETE")
    return "\n".join(logs)

router = IntelligentRouter()
####
