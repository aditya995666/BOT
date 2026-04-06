import streamlit as st
import tempfile
import os
import sys
import time
import io
import re
import requests
import json
from agents.master_agent import master_agent  # ✅ Direct instance import
from memory.database import init_db
import sqlite3
from pathlib import Path

# ✅ Database check - only initialize if needed
DB_PATH = Path(__file__).parent / "memory" / "memory.db"
if DB_PATH.exists():
    # Database already exists, just verify
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM memory")
        count = cursor.fetchone()[0]
        conn.close()
    except:
        init_db()
else:
    init_db()

from agents.system_health_agent import SystemHealthAgent
from streamlit_mic_recorder import mic_recorder
from agents.master_autofix_agent import MasterAutoFixAgent
from agents.autoclicker_handler import autoclicker_handler

from memory.vector_store import load_existing_memory
load_existing_memory()
from agents.router import start_background_self_healing
# Master Agent global instance (lazy / direct creation)
from agents.master_agent import master_agent  # ✅ Direct instance import


OS_API_URL = "http://127.0.0.1:8000/system/evolve"
TOKEN = "jarvis123"

def generate_ai_fix(problem_data):
    """Generate AI fix for system problems - with lazy import to avoid circular imports"""
    try:
        from agents.router import generate_ai_fix as _generate
        return _generate(problem_data)
    except ImportError:
        try:
            from agents.gemini_fix_engine import generate_fix_with_gemini
            return generate_fix_with_gemini(problem_data)
        except:
            return f"# Fix generation failed for: {problem_data}"

def extract_pure_python_code(text: str) -> str:
    """Extract ONLY python code from LLM response."""
    if not text:
        return ""

    code_blocks = re.findall(r"```python(.*?)```", text, re.DOTALL)
    if code_blocks:
        return code_blocks[0].strip()

    code_blocks = re.findall(r"```(.*?)```", text, re.DOTALL)
    if code_blocks:
        return code_blocks[0].strip()

    lines = text.split("\n")
    filtered = []
    for line in lines:
        if any(word in line.lower() for word in [
            "here", "example", "explanation", "this code",
            "complete code", "usage", "output"
        ]):
            continue
        filtered.append(line)

    return "\n".join(filtered).strip()

@st.cache_resource
def get_tts_engine():
    import pyttsx3
    engine = pyttsx3.init()
    engine.setProperty('rate',170)
    return engine

def extract_failure_reason(logs: str) -> str:
    if not logs:
        return "No logs available – unknown failure"

    lines = logs.split('\n')
    failure_keywords = [
        '❌','failed','error','exception','crashed','timeout',
        'syntaxerror','importerror','traceback','modulenotfounderror',
        'attributeerror','nameerror','typeerror'
    ]

    failure_lines = []
    for line in lines:
        if any(kw in line.lower() for kw in failure_keywords):
            failure_lines.append(line.strip())
    if failure_lines:
        return '\n'.join(failure_lines[:5])

    return "Test failed but specific error not found in logs."

try:
    import pyttsx3
    import speech_recognition as sr
    VOICE_AVAILABLE = True
except Exception as e:
    VOICE_AVAILABLE = False
    sr = None

# normalize_router_response function
def normalize_router_response(response: dict) -> dict:
    """Normalize router response for UI display - FIXED for form filling"""
    if not isinstance(response, dict):
        return {"agent_used": "unknown", "content": str(response), "success": False}

    # 🔥 FIX: Direct content field (most common)
    if "content" in response:
        content = response["content"]
        # Check if content is a form question
        if content and isinstance(content, str) and (content.startswith("📝") or content.startswith("📱") or content.startswith("⚪")):
            return {
                "agent_used": response.get("agent_used", "browser"),
                "content": content,
                "success": response.get("success", True),
                "is_question": True
            }
        return {
            "agent_used": response.get("agent_used", "general"),
            "content": content,
            "success": response.get("success", True)
        }
    
    # CASE: Result with nested result
    if "result" in response:
        result_data = response["result"]
        
        content = None
        
        if isinstance(result_data, dict):
            if "content" in result_data:
                content = result_data["content"]
            elif "result" in result_data and isinstance(result_data["result"], dict):
                if "content" in result_data["result"]:
                    content = result_data["result"]["content"]
            elif "message" in result_data:
                content = result_data["message"]
            elif "text" in result_data:
                content = result_data["text"]
            elif "answer" in result_data:
                content = result_data["answer"]
            else:
                # Try to find any string value
                for key, value in result_data.items():
                    if isinstance(value, str) and len(value) > 5:
                        content = value
                        break
                if not content:
                    content = str(result_data)
        else:
            content = str(result_data)
        
        normalized = {
            "agent_used": response.get("agent_used", "general"),
            "content": content,
            "success": response.get("success", True)
        }
        
        # Copy coding-specific fields
        if response.get("agent_used") == "coding":
            if "generated_code" in result_data:
                normalized["generated_code"] = result_data["generated_code"]
            elif "generated_code" in response:
                normalized["generated_code"] = response["generated_code"]
            
            if "autofix_logs" in result_data:
                normalized["autofix_logs"] = result_data["autofix_logs"]
            elif "autofix_logs" in response:
                normalized["autofix_logs"] = response["autofix_logs"]
            
            if "stage" in result_data:
                normalized["stage"] = result_data["stage"]
            elif "stage" in response:
                normalized["stage"] = response["stage"]
        
        return normalized
    
    # CASE: Next field in form filling (when result is next_field dict)
    if "next_field" in response:
        next_field = response["next_field"]
        if isinstance(next_field, dict):
            question = next_field.get("question", "Enter value:")
            return {
                "agent_used": "browser",
                "content": question,
                "success": True,
                "is_question": True
            }
        elif isinstance(next_field, str):
            return {
                "agent_used": "browser",
                "content": next_field,
                "success": True,
                "is_question": True
            }
    
    # CASE: Coding agent direct response
    if response.get("agent_used") == "coding":
        content = response.get("result", {}).get("content", "")
        if not content:
            content = response.get("content", "")
        if not content and response.get("generated_code"):
            content = f"💻 Generated Code:\n```python\n{response['generated_code']}\n```"
        
        return {
            "agent_used": "coding",
            "content": content,
            "generated_code": response.get("generated_code"),
            "autofix_logs": response.get("autofix_logs"),
            "stage": response.get("stage"),
            "success": True
        }
    
    # CASE: Try to extract from common fields
    for field in ["message", "text", "answer", "output", "response"]:
        if field in response:
            return {
                "agent_used": response.get("agent_used", "general"),
                "content": response[field],
                "success": response.get("success", True)
            }
    
    # Fallback
    return {
        "agent_used": "unknown",
        "content": str(response),
        "success": False
    }

@st.cache_data
def extract_document_text(file, file_type):
    from utils.nlp_utils import extract_pdf_text, extract_docx_text
    if file_type == "pdf":
        return extract_pdf_text(file)
    elif file_type == "docx":
        return extract_docx_text(file)
    return ""

@st.cache_resource
def load_router():
    if "task_watcher_started" not in st.session_state:
        st.session_state.task_watcher_started = True
    from agents.router import IntelligentRouter
    return IntelligentRouter()

@st.cache_resource
def load_system_agent():
    from agents.system_health_agent import SystemHealthAgent
    return SystemHealthAgent()

@st.cache_resource
def load_suggestion_agent():
    from agents.self_suggestion_agent import SelfSuggestionAgent
    return SelfSuggestionAgent()

@st.cache_resource
def get_cached_system_problems():
    agent = SystemHealthAgent()
    return agent.full_system_scan()

from utils.ocr_utils import extract_text_from_pdf_ocr
from utils.nlp_utils import extract_pdf_text, extract_docx_text
from utils.language_utils import detect_language
from utils.hash_utils import hash_text

# Initialize session state
if "self_heal_started" not in st.session_state:
    st.session_state.self_heal_started = False
# 🔥 NEW: Permission handling for unethical commands
if "pending_unethical" not in st.session_state:
    st.session_state.pending_unethical = None
if "pending_query" not in st.session_state:
    st.session_state.pending_query = None
if "router" not in st.session_state:
    st.session_state.router = load_router()

router = st.session_state.router
if "self_heal_started" not in st.session_state:
    try:
        start_background_self_healing()
    except Exception as e:
        print("Self-healing start error:", e)

    st.session_state.self_heal_started = True

router = load_router()

st.set_page_config(
    page_title="JARVIS - Self-Improving AI System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize all session state variables
defaults = {
    "messages": [],
    "tasks": {},
    "document_text": None,
    "document_lang": None,
    "document_hash": None,
    "voice_enabled": False,
    "voice_mode": False,
    "last_spoken": None,
    "coding_state": "idle",
    "last_generated_code": None,
    "last_autofix_logs": None,
    "waiting_for": None,
    "awaiting_clarification": False,
    "direct_messages": [],
    "processing_voice": False, 
    "last_generated_pdf": None,
    "processed_message_ids": set(),
    "pdf_path": None,
    "pdf_paths": [],  # 🔥 NEW: Multiple PDF paths
    "uploaded_files_count": 0,  # 🔥 NEW: Count of uploaded files
    "test_passed": False,
    "ready_for_permanent": False,
    "current_code": None,
    "stage1_logs": None,
    "stage2_logs": None,
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Header
st.markdown("""
<style>
.stApp { background: linear-gradient(135deg,#0f0c29,#302b63,#24243e); }
.main-header {
    font-size:3rem; text-align:center; font-weight:800;
    background:linear-gradient(90deg,#00DBDE,#FC00FF);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
}
.sub-header { text-align:center; color:#a0a0c0; margin-bottom:2rem; }
.chat-bubble { padding:12px 18px; border-radius:18px; margin:8px 0; max-width:80%; }
.user-bubble { background:#667eea; color:white; margin-left:auto; }
.ai-bubble { background:white; color:#222; margin-right:auto; }
.ai-bubble code { background:#f0f0f0; padding:2px 4px; border-radius:4px; }
.ai-bubble pre { background:#f5f5f5; padding:10px; border-radius:8px; overflow-x:auto; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">🧠 JARVIS</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Multi-Agent • Router-Driven • TRUE Voice-to-Voice</p>', unsafe_allow_html=True)

# Voice functions
def speak_voice(text):
    if not VOICE_AVAILABLE or not st.session_state.voice_enabled:
        return
    try:
        engine = get_tts_engine()
        engine.stop()
        engine.say(text[:400])
        engine.runAndWait()
        engine.stop()
    except Exception as e:
        print("TTS error:", e)

# Handlers
from handlers.os_handler import OSHandler
from handlers.browser_handler import BrowserHandler
from handlers.research_handler import ResearchHandler
from agents.os_control_agent import OSControlAgent
from agents.browser_control_agent import BrowserControlAgent

@st.cache_resource
def load_handlers():
    return (
        OSHandler(OSControlAgent()),
        BrowserHandler(BrowserControlAgent()),
        ResearchHandler("http://127.0.0.1:8000")
    )
os_handler, browser_handler, research_handler = load_handlers()

# Voice functions
def listen_voice(lang="hi-IN", timeout=5, phrase_time_limit=6):
    if not VOICE_AVAILABLE:
        return None
    try:
        r = sr.Recognizer()
        r.pause_threshold = 0.8
        r.energy_threshold = 300
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, 0.5)
            audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        return r.recognize_google(audio, language=lang)
    except:
        return None

# SIDEBAR
with st.sidebar:
    st.markdown("### 🧠 AI System Health")

    if "system_problems" not in st.session_state:
        st.session_state.system_problems = None

    col_scan, col_clear = st.columns([3, 1])
    if col_scan.button("🔍 Scan System Health", use_container_width=True):
        from agents.system_health_agent import SystemHealthAgent
        with st.spinner("Scanning full AI system..."):
            agent = SystemHealthAgent()
            st.session_state.system_problems = agent.full_system_scan()
            start_background_self_healing()
            st.session_state.healing_logs = None
            for key in list(st.session_state.keys()):
                if key.startswith("fix_result_") or key.startswith("fix_text_") or key.startswith("fix_failure_reason_") or key.startswith("fix_logs_"):
                    st.session_state.pop(key, None)
            st.session_state.healing_logs = None
            st.session_state.pop("fix_result_", None)
        st.rerun()

    if col_clear.button("🧹 Clear", help="Reset scan results"):
        st.session_state.system_problems = None
        st.rerun()

    problems = st.session_state.system_problems

    if problems is None:
        st.info("Scan karo system health check karne ke liye")
    elif len(problems) == 0:
        st.success("✅ System bilkul healthy hai – koi problem nahi mila")
    else:
        st.error(f"⚠️ {len(problems)} problems detected")
        for i, p in enumerate(problems):
            title = getattr(p, 'title', f'Problem #{i+1}')
            cause = getattr(p, 'cause', '—')
            severity = getattr(p, 'severity', '—')
            with st.expander(f"⚠️ {title} (Severity: {severity})", expanded=False):
                st.write("**Cause:**", cause)
                col_gen, col_perm = st.columns(2)
                if col_gen.button(f"🤖 Generate & Test Fix #{i+1}", key=f"gen_test_{i}", use_container_width=True):
                    with st.spinner(f"Generating fix for problem {i+1}..."):
                        try:
                            from agents.router import generate_ai_fix
                            from agents.master_autofix_agent import MasterAutoFixAgent
                            fix_text = generate_ai_fix(p)
                            master = MasterAutoFixAgent()
                            single_result = master.run_autofix_pipeline(
                                problems=[p],
                                fixes=[fix_text],
                                apply_permanent=False
                            )
                            st.session_state[f"fix_result_{i}"] = single_result
                            st.session_state[f"fix_text_{i}"] = fix_text
                            st.session_state[f"fix_failure_reason_{i}"] = extract_failure_reason(single_result)
                            st.session_state[f"fix_logs_{i}"] = single_result
                            st.rerun()
                        except Exception as e:
                            st.error(f"Fix generation mein error: {str(e)}")

    st.markdown("---")
    st.markdown("### 🧠 Master Control Panel")

    if master_agent.is_active():
        st.success("🟢 System Active")
    else:
        st.error("🔴 System Disabled")

    col1, col2 = st.columns(2)
    if col1.button("🚨 Disable JARVIS", use_container_width=True):
        master_agent.disable_system()
        st.error("🚨 JARVIS Disabled!")
        st.rerun()
    if col2.button("✅ Enable JARVIS", use_container_width=True):
        master_agent.enable_system()
        st.success("✅ JARVIS Enabled!")
        st.rerun()

    st.markdown("---")
    st.markdown("### 🎤 Voice Control")
    st.session_state.voice_enabled = st.checkbox(
        "Enable Voice Output",
        value=st.session_state.voice_enabled
    )
    if st.button("🎙️ Start Voice Chat"):
        st.session_state.voice_mode = True
        st.session_state.processing_voice = False
    if st.button("🛑 Stop Voice Chat"):
        st.session_state.voice_mode = False
        st.session_state.processing_voice = False    

    st.markdown("---")
    st.markdown("### 📄 Upload Document(s)")

    uploaded_files = st.file_uploader(
        "Upload Document(s)",
        type=["txt", "pdf", "docx"],
        accept_multiple_files=True,
        key="document_upload_multiple"
    )

    if uploaded_files:
        all_texts = []
        pdf_paths = []
        for uploaded_file in uploaded_files:
            ext = uploaded_file.name.split(".")[-1].lower()
            text = ""
            try:
                if ext == "txt":
                    text = uploaded_file.read().decode("utf-8", errors="ignore")
                elif ext == "pdf":
                    pdf_bytes = uploaded_file.read()
                    text = extract_document_text(io.BytesIO(pdf_bytes), "pdf")
                    if not text or len(text.strip()) < 50:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                            tmp.write(pdf_bytes)
                            tmp_path = tmp.name
                        text = extract_text_from_pdf_ocr(tmp_path)
                        pdf_paths.append(tmp_path)
                elif ext == "docx":
                    text = extract_document_text(uploaded_file, "docx")
                if text and len(text.strip()) > 20:
                    text = text[:15000]
                    all_texts.append(f"\n{'='*60}\n📁 FILE: {uploaded_file.name}\n{'='*60}\n{text}")
            except Exception as e:
                st.error(f"Error in {uploaded_file.name}: {str(e)}")
        if all_texts:
            combined_text = "\n\n".join(all_texts)
            st.session_state.document_text = combined_text
            st.session_state.document_lang = detect_language(combined_text)
            st.session_state.document_hash = hash_text(combined_text)
            st.session_state.pdf_paths = pdf_paths
            st.session_state.uploaded_files_count = len(uploaded_files)
            st.success(f"✅ {len(uploaded_files)} files loaded successfully!")
            with st.expander(f"📚 Loaded Files ({len(uploaded_files)})"):
                for f in uploaded_files:
                    st.write(f"📄 {f.name}")
        else:
            st.error("❌ No text could be extracted from uploaded files")

    st.markdown("---")
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.session_state.processed_message_ids = set()
        st.rerun()

# UNIVERSAL VOICE MODE
if st.session_state.voice_mode:
    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 20px; padding: 20px; text-align: center; margin: 10px 0;'>
        <h3>🎤 Universal Voice Mode Active</h3>
        <p style='font-size: 14px;'>
        ✅ Coding | ✅ Browser | ✅ AutoClicker | ✅ Research | ✅ Document | ✅ PDF | ✅ OS | ✅ Evolution
        </p>
        <p style='font-size: 12px; margin-top: 10px;'>
        🗣️ Jo bhi command doge, voice se hoga!
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    audio = mic_recorder(
        start_prompt="🎤 Click and Speak",
        stop_prompt="⏹️ Stop",
        just_once=True,
        format="wav",
        key="universal_voice",
        use_container_width=True,
    )
    
    if audio is not None and not st.session_state.processing_voice:
        st.session_state.processing_voice = True
        with st.spinner("🎙️ Processing your voice command..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                f.write(audio["bytes"])
                audio_path = f.name
            try:
                if sr is not None:
                    r = sr.Recognizer()
                    with sr.AudioFile(audio_path) as source:
                        r.adjust_for_ambient_noise(source, duration=0.5)
                        audio_data = r.record(source)
                    lang = "hi-IN" if st.session_state.get("document_lang") == "hi" else "en-US"
                    user_voice = r.recognize_google(audio_data, language=lang)
                    st.success(f"🎤 You said: {user_voice}")
                    st.session_state.messages.append({
                        "role": "user",
                        "content": f"🎤 {user_voice}"
                    })
                    from agents.voice_chat_agent import voice_brain
                    with st.spinner("🧠 JARVIS is thinking..."):
                        response_text = voice_brain(user_voice, voice_mode=True)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response_text
                    })
                    if st.session_state.voice_enabled:
                        from agents.voice_chat_agent import speak_voice
                        speak_voice(response_text)
                    st.success("✅ Response received!")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
            finally:
                if os.path.exists(audio_path):
                    os.unlink(audio_path)
                st.session_state.processing_voice = False

# PDF Download
if st.session_state.last_generated_pdf:
    pdf_path = st.session_state.last_generated_pdf
    if os.path.exists(pdf_path):
        st.markdown("### 📄 Generated PDF")
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        st.download_button(
            label="⬇️ Download Generated PDF",
            data=pdf_bytes,
            file_name=os.path.basename(pdf_path),
            mime="application/pdf",
            use_container_width=True
        )
        
# FIXED: Text Chat Pipeline

# 🔥 NEW: Check for pending unethical command
if st.session_state.pending_unethical:
    st.warning("⚠️ **Permission Required**")
    st.error(f"Unethical command detected: {st.session_state.pending_unethical['reason']}")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Allow", type="primary", key="allow_unethical"):
            with st.spinner("Executing command..."):
                response = router.route(
                    query=st.session_state.pending_query,
                    context=context if 'context' in locals() else {},
                    history=st.session_state.messages[-5:]
                )
                data = normalize_router_response(response)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": data.get("content", "Command executed")
                })
            st.session_state.pending_unethical = None
            st.session_state.pending_query = None
            st.rerun()
    with col2:
        if st.button("❌ Block", type="secondary", key="block_unethical"):
            st.session_state.pending_unethical = None
            st.session_state.pending_query = None
            st.success("Command blocked")
            st.rerun()
    st.stop()

# 🎤 BROWSER VOICE INPUT
if st.session_state.voice_mode:
    st.markdown("### 🎙️ Speak now")
    audio = mic_recorder(
        start_prompt="🎤 Start recording",
        stop_prompt="⏹️ Stop",
        just_once=True,
        use_container_width=True,
    )
    if audio:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(audio["bytes"])
            audio_path = f.name
        try:
            r = sr.Recognizer()
            with sr.AudioFile(audio_path) as source:
                audio_data = r.record(source)
        except Exception as e:
            st.warning("Audio processing failed")
            audio_data = None
        try:
            lang = st.session_state.document_lang or "en-US"
            user_voice = r.recognize_google(audio_data, language=lang)
        except Exception as e:
            user_voice = None
            st.warning(f"Voice recognition failed: {str(e)}")
        if user_voice:
            st.session_state.messages.append({"role":"user","content":user_voice})
            voice_context = {
                "voice_mode": True,
                "coding_stage": st.session_state.coding_state,
                "generated_code": st.session_state.last_generated_code,
            }
            response = router.route(
                query=user_voice,
                context=voice_context,
                history=st.session_state.messages[-5:]
            )
            data = normalize_router_response(response)
            if isinstance(response, dict):
                needs_clarification = response.get("result", {}).get("needs_clarification")
                if needs_clarification:
                    st.session_state.awaiting_clarification = True
                else:
                    st.session_state.awaiting_clarification = False
            ai_text = data["content"]
            st.session_state.messages.append({"role":"assistant","content":ai_text})
            if st.session_state.voice_enabled:
                speak_voice(ai_text)
            st.rerun()
        if 'audio_path' in locals() and os.path.exists(audio_path):
            os.unlink(audio_path)

# 💬 TEXT CHAT PIPELINE
user_input = st.chat_input("Type message…")

if user_input:
    message_id = f"{time.time()}_{hash(user_input)}"
    if message_id in st.session_state.processed_message_ids:
        st.rerun()
    st.session_state.processed_message_ids.add(message_id)
    if len(st.session_state.processed_message_ids) > 100:
        st.session_state.processed_message_ids = set(list(st.session_state.processed_message_ids)[-50:])

    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })
    
    context = {
        "voice_mode": False,
        "coding_stage": st.session_state.coding_state,
        "generated_code": st.session_state.last_generated_code,
    }
    
    if st.session_state.document_text:
        context.update({
            "document_text": st.session_state.document_text,
            "document_lang": st.session_state.document_lang,
            "document_hash": st.session_state.document_hash,
            "pdf_paths": st.session_state.get("pdf_paths", []),
            "uploaded_files_count": st.session_state.get("uploaded_files_count", 0)
        })
    
    if st.session_state.awaiting_clarification:
        context["clarification_reply"] = True
    
    history = st.session_state.messages[-5:]
    
    if not master_agent.is_active():
        st.session_state.messages.append({
            "role": "assistant",
            "content": "🚨 System disabled by Master Agent"
        })
        st.rerun()
    
    with st.spinner("JARVIS soch raha hai..."):
        try:
            response = router.route(
                query=user_input,
                context=context,
                history=history
            )
            if isinstance(response, dict) and response.get("requires_permission"):
                st.session_state.pending_unethical = response.get("ethical_result")
                st.session_state.pending_query = user_input
                st.rerun()
            if response is None:
                response = {"success": False, "content": "No response from router"}
            
            data = normalize_router_response(response)
            
            if isinstance(response, dict):
                needs_clarification = response.get("result", {}).get("needs_clarification")
                st.session_state.awaiting_clarification = bool(needs_clarification)
            
            if isinstance(response, dict) and response.get("type") == "pdf":
                st.session_state.last_generated_pdf = response.get("file")
            
            raw_code = data.get("generated_code") or response.get("generated_code")
            content_text = data.get("content", "")
            code_match = re.search(r"```(\w+)?(.*?)```", content_text, re.DOTALL)
            
            if not raw_code and code_match:
                raw_code = code_match.group(2)
            
            if raw_code:
                cleaned_code = raw_code.strip()
                st.session_state.last_generated_code = cleaned_code
                stage_value = data.get("stage") or response.get("stage")
                if stage_value:
                    st.session_state.coding_state = stage_value
                else:
                    st.session_state.coding_state = "generated"
                if "autofix_logs" in response or data.get("autofix_logs"):
                    st.session_state.last_autofix_logs = data.get("autofix_logs") or response.get("autofix_logs")
            
            assistant_content = data.get("content", "No content")
            if assistant_content and assistant_content.strip():
                if assistant_content.startswith("{'") or assistant_content.startswith('{"'):
                    try:
                        import ast
                        parsed = ast.literal_eval(assistant_content)
                        if isinstance(parsed, dict) and "content" in parsed:
                            assistant_content = parsed["content"]
                    except:
                        pass
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": assistant_content
                })
            
            if data["agent_used"] == "coding":
                raw_code = data.get("generated_code") or data.get("content", "")
                cleaned_code = extract_pure_python_code(raw_code)
                st.session_state.last_generated_code = cleaned_code
                st.session_state.last_autofix_logs = data.get("autofix_logs")
                st.session_state.coding_state = data.get("stage") or "generated"
            
        except Exception as e:
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"Sorry, error aaya: {str(e)}"
            })
    st.rerun()

# Evolution button
st.title("JARVIS System Evolution Dashboard")

def trigger_evolution():
    headers = {"Authorization": f"Bearer {TOKEN}"}
    try:
        response = requests.post(OS_API_URL, headers=headers)
        if response.status_code == 200:
            data = response.json()
            pdf_path = data['result']['pdf_report']
            return pdf_path, "✅ PDF generated successfully!"
        else:
            return None, f"❌ Failed: {response.status_code}, {response.text}"
    except Exception as e:
        return None, f"❌ Error: {e}"

if st.button("Run Evolution & Generate PDF"):
    with st.spinner("Running evolution cycle..."):
        pdf_path, message = trigger_evolution()
        st.success(message)
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="Download Evolution PDF",
                    data=f.read(),
                    file_name=os.path.basename(pdf_path),
                    mime="application/pdf"
                )

# 🖱️ AUTOCLICKER CONTROL
st.markdown("---")
st.markdown("## 🖱️ AutoClicker")

col1, col2 = st.columns([3, 1])

with col1:
    autoclicker_input = st.text_input(
        "🎯 Command:",
        placeholder="e.g., click on Scan System Health, click on Disable JARVIS, click on Clear Chat",
        key="autoclicker_simple"
    )

with col2:
    st.markdown("### ")
    if st.button("🚀 Execute", type="primary", use_container_width=True):
        if autoclicker_input:
            with st.spinner("Working..."):
                try:
                    button_match = re.search(r'(?:click|press|tap)\s+(?:on\s+)?(?:the\s+)?["\']?([^"\']+)["\']?\s*(?:button|link|option)?', autoclicker_input.lower())
                    if button_match:
                        button_text = button_match.group(1).strip()
                        button_lower = button_text.lower()
                        
                        if "scan system health" in button_lower or "system health" in button_lower:
                            from agents.system_health_agent import SystemHealthAgent
                            with st.spinner("Scanning system..."):
                                st.session_state.system_problems = SystemHealthAgent().full_system_scan()
                                from agents.router import start_background_self_healing
                                start_background_self_healing()
                            st.success("✅ Clicked on 'Scan System Health'")
                            st.rerun()
                        elif "clear" in button_lower and "health" not in button_lower:
                            st.session_state.system_problems = None
                            st.success("✅ Clicked on 'Clear'")
                            st.rerun()
                        elif "disable jarvis" in button_lower or "disable" in button_lower:
                            master_agent.disable_system("AutoClicker command")
                            st.error("🔴 JARVIS Disabled!")
                            st.rerun()
                        elif "enable jarvis" in button_lower or "enable" in button_lower:
                            master_agent.enable_system("AutoClicker command")
                            st.success("🟢 JARVIS Enabled!")
                            st.rerun()
                        elif "start voice chat" in button_lower or "voice chat" in button_lower:
                            st.session_state.voice_mode = True
                            st.success("🎤 Voice Chat Started!")
                            st.rerun()
                        elif "stop voice chat" in button_lower or "stop voice" in button_lower:
                            st.session_state.voice_mode = False
                            st.success("🛑 Voice Chat Stopped!")
                            st.rerun()
                        elif "clear chat" in button_lower or "clear history" in button_lower:
                            st.session_state.messages = []
                            st.session_state.processed_message_ids = set()
                            st.success("🗑️ Chat History Cleared!")
                            st.rerun()
                        elif "reset coding" in button_lower or "coding pipeline" in button_lower:
                            st.session_state.coding_state = "idle"
                            st.session_state.last_generated_code = None
                            st.session_state.last_autofix_logs = None
                            st.session_state.test_passed = False
                            st.session_state.ready_for_permanent = False
                            st.session_state.current_code = None
                            st.success("🔄 Coding Pipeline Reset!")
                            st.rerun()
                        elif "toggle gemini" in button_lower or "gemini" in button_lower:
                            API_URL = "http://127.0.0.1:8000"
                            HEADERS = {"Authorization": "Bearer jarvis123"}
                            try:
                                res = requests.post(f"{API_URL}/system/toggle-gemini", headers=HEADERS)
                                if res.status_code == 200:
                                    state = res.json().get("gemini_enabled")
                                    if state:
                                        st.success("🟢 Gemini Enabled")
                                    else:
                                        st.warning("🔴 Gemini Disabled")
                                else:
                                    st.error(f"Failed: {res.status_code}")
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                            st.rerun()
                        else:
                            from agents.autoclicker_agent import autoclicker_agent
                            result = autoclicker_agent.process_command(autoclicker_input)
                            if result["success"]:
                                st.success(f"✅ {result['message']}")
                            else:
                                st.error(f"❌ {result['message']}")
                    else:
                        st.error(f"❌ Could not understand: '{autoclicker_input}'")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

# Direct System Control
st.markdown("---")
st.markdown("## ⚡ Direct System Control (OS / Browser / Research)")

direct_input = st.text_input("⚡ Direct System Command", key="direct_chat")

col1, col2 = st.columns(2)

with col1:
    if st.button("Send Direct Command", use_container_width=True):
        if not direct_input.strip():
            st.warning("Please enter command first")
        else:
            st.session_state.direct_messages.append({
                "role": "user",
                "content": direct_input
            })
            response_text = ""
            ql = direct_input.lower()
            try:
                # 🔥 FIX: Research commands pehle check karo
                research_keywords = ["research", "do research", "research about", "research on", 
                                    "deep research", "internet research", "find information on", 
                                    "search for topic", "look up topic", "study topic", 
                                    "train yourself", "trained on"]
                
                if any(x in ql for x in research_keywords):
                    result = research_handler.handle(direct_input)
                    response_text = result.get("content", str(result))
                else:
                    result = os_handler.handle(direct_input)
                    response_text = result.get("content", str(result))
            except Exception as e:
                response_text = f"Error: {str(e)}"
            st.session_state.direct_messages.append({
                "role": "assistant",
                "content": response_text
            })
            st.rerun()
with col2:
    if st.button("❌ Clear History", use_container_width=True):
        st.session_state.direct_messages = []
        st.rerun()

# Direct chat display
for msg in st.session_state.direct_messages[-6:]:
    if msg["role"] == "user":
        st.markdown(f"<div class='chat-bubble user-bubble'>⚡ {msg['content']}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='chat-bubble ai-bubble'>🛠 {msg['content']}</div>", unsafe_allow_html=True)

# ✅ ADD THIS INSTEAD (2 buttons only)

st.markdown("### 🤖 AI Model Selector")

current_model = st.session_state.get("ai_model", "gemini")

# Display current model status
if current_model == "gemini":
    st.info("🟢 Using **Gemini** (Google)")
else:
    st.info("🔵 Using **Claude** (Anthropic)")

# Model selection buttons
col_gem, col_claude = st.columns(2)

with col_gem:
    if st.button("🤖 Gemini", use_container_width=True):
        st.session_state.ai_model = "gemini"
        st.success("Switched to Gemini!")
        st.rerun()

with col_claude:
    if st.button("🧠 Claude", use_container_width=True):
        st.session_state.ai_model = "claude"
        st.success("Switched to Claude!")
        st.rerun()
st.markdown("---")
st.markdown("### 💬 Conversation")
for msg in st.session_state.messages[-12:]:
    if msg["role"] == "user":
        st.markdown(f"<div class='chat-bubble user-bubble'>👤 {msg['content']}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='chat-bubble ai-bubble'>🤖 {msg['content']}</div>", unsafe_allow_html=True)

st.markdown("---")
st.markdown("© 2024 JARVIS AI System")