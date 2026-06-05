import streamlit as st
import tempfile
import os
import sys
import time
import io
import re
import requests
import json
from agents.master_agent import master_agent
from memory.database import init_db
import sqlite3
from pathlib import Path
from utils.code_cleaner import extract_pure_python_code

# ✅ Database check - only initialize if needed
DB_PATH = Path(__file__).parent / "memory" / "memory.db"
if DB_PATH.exists():
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
from agents.master_agent import master_agent

OS_API_URL = "http://127.0.0.1:8000/system/evolve"
TOKEN = "jarvis123"

@st.cache_resource
def get_tts_engine():
    import pyttsx3
    engine = pyttsx3.init()
    engine.setProperty('rate',170)
    return engine

try:
    import pyttsx3
    import speech_recognition as sr
    VOICE_AVAILABLE = True
except Exception as e:
    VOICE_AVAILABLE = False
    sr = None
def extract_failure_reason(logs: str) -> str:
    """Extract failure reason from logs"""
    if not logs:
        return "Unknown failure"
    
    lines = logs.split("\n")
    keywords = ["❌", "error", "exception", "traceback", "failed", "timeout",
                "syntaxerror", "importerror", "modulenotfounderror",
                "attributeerror", "nameerror", "typeerror"]
    
    bad = []
    for line in lines:
        if any(k in line.lower() for k in keywords):
            bad.append(line.strip())
    
    if bad:
        return "\n".join(bad[:5])
    
    return "Tests failed but no clear error found"
def normalize_router_response(response: dict) -> dict:
    if not isinstance(response, dict):
        return {"agent_used": "unknown", "content": str(response), "success": False}

    # 🔥 CRITICAL: Agar coding response hai to IMMEDIATELY return
    if response.get("agent_used") == "coding":
        return {
            "agent_used": "coding",
            "content": response.get("content", ""),
            "generated_code": response.get("generated_code", ""),
            "stage": response.get("stage", "generated"),
            "success": response.get("success", True)
        }

    # Baaki code yahan...
    generated_code = response.get("generated_code", "")
    if "content" in response:
        content = response["content"]
        if content and isinstance(content, str) and (content.startswith("📝") or content.startswith("📱") or content.startswith("⚪")):
            return {"agent_used": response.get("agent_used", "browser"), "content": content, "success": response.get("success", True), "is_question": True}
        return {"agent_used": response.get("agent_used", "general"), "content": content, "success": response.get("success", True)}

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
                for key, value in result_data.items():
                    if isinstance(value, str) and len(value) > 5:
                        content = value
                        break
                if not content:
                    content = str(result_data)
        else:
            content = str(result_data)

        normalized = {"agent_used": response.get("agent_used", "general"), "content": content, "success": response.get("success", True)}

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

    if "next_field" in response:
        next_field = response["next_field"]
        if isinstance(next_field, dict):
            question = next_field.get("question", "Enter value:")
            return {"agent_used": "browser", "content": question, "success": True, "is_question": True}
        elif isinstance(next_field, str):
            return {"agent_used": "browser", "content": next_field, "success": True, "is_question": True}

    for field in ["message", "text", "answer", "output", "response"]:
        if field in response:
            return {"agent_used": response.get("agent_used", "general"), "content": response[field], "success": response.get("success", True)}

    return {"agent_used": "unknown", "content": str(response), "success": False}

@st.cache_data
def extract_document_text(file, file_type):
    from utils.nlp_utils import extract_pdf_text, extract_docx_text
    if file_type == "pdf":
        return extract_pdf_text(file)
    elif file_type == "docx":
        return extract_docx_text(file)
    return ""

# 🔥 TEMPORARY: Remove cache to debug
# @st.cache_resource
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
def get_cached_system_problems():
    agent = SystemHealthAgent()
    return agent.full_system_scan()

from utils.ocr_utils import extract_text_from_pdf_ocr
from utils.nlp_utils import extract_pdf_text, extract_docx_text
from utils.language_utils import detect_language
from utils.hash_utils import hash_text

if "self_heal_started" not in st.session_state:
    st.session_state.self_heal_started = False
if "pending_unethical" not in st.session_state:
    st.session_state.pending_unethical = None
if "pending_query" not in st.session_state:
    st.session_state.pending_query = None
if "router" not in st.session_state:
    st.session_state.router = load_router()

router = st.session_state.router

# ✅ REPLACE WITH:
if "self_heal_started" not in st.session_state:
    st.session_state.self_heal_started = False
print("✅ Auto self-healing DISABLED - Manual only")

router = load_router()

st.set_page_config(
    page_title="JARVIS - Self-Improving AI System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    "pdf_paths": [],
    "uploaded_files_count": 0,
    "test_passed": False,
    "ready_for_permanent": False,
    "current_code": None,
    "stage1_logs": None,
    "stage2_logs": None,
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

st.markdown("""
<style>
.stApp { background: linear-gradient(135deg,#0f0c29,#302b63,#24243e); }
.main-header { font-size:3rem; text-align:center; font-weight:800; background:linear-gradient(90deg,#00DBDE,#FC00FF); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
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

from handlers.os_handler import OSHandler
from handlers.browser_handler import BrowserHandler
from handlers.research_handler import ResearchHandler
from agents.os_control_agent import OSControlAgent
from agents.browser_control_agent import BrowserControlAgent

@st.cache_resource
def load_handlers():
    return (OSHandler(OSControlAgent()), BrowserHandler(BrowserControlAgent()), ResearchHandler("http://127.0.0.1:8000"))
os_handler, browser_handler, research_handler = load_handlers()

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
            st.session_state.healing_logs = None
            for key in list(st.session_state.keys()):
                if key.startswith("fix_result_"):
                    st.session_state.pop(key, None)
            st.session_state.healing_logs = None
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
                            single_result = master.run_autofix_pipeline(problems=[p], fixes=[fix_text], apply_permanent=False)
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
    st.session_state.voice_enabled = st.checkbox("Enable Voice Output", value=st.session_state.voice_enabled)
    if st.button("🎙️ Start Voice Chat"):
        st.session_state.voice_mode = True
        st.session_state.processing_voice = False
    if st.button("🛑 Stop Voice Chat"):
        st.session_state.voice_mode = False
        st.session_state.processing_voice = False
    st.markdown("---")
    st.markdown("### 📄 Upload Document(s)")
    uploaded_files = st.file_uploader("Upload Document(s)", type=["txt", "pdf", "docx"], accept_multiple_files=True, key="document_upload_multiple")
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
                    
                    # 🔥 FIX 1: Har PDF ka temp file HAMESHA banao
                    with tempfile.NamedTemporaryFile(
                        delete=False, 
                        suffix=".pdf",
                        prefix=f"jarvis_{uploaded_file.name.replace('.pdf','')}_"
                    ) as tmp:
                        tmp.write(pdf_bytes)
                        tmp_path = tmp.name
                    
                    # 🔥 FIX 2: Path HAMESHA add karo (OCR se pehle bhi)
                    pdf_paths.append(tmp_path)
                    print(f"📄 PDF saved to: {tmp_path}")
                    
                    # Pehle normal extraction try karo
                    try:
                        text = extract_pdf_text(io.BytesIO(pdf_bytes))
                    except:
                        text = ""
                    
                    # Agar normal extraction fail ho toh OCR
                    if not text or len(text.strip()) < 50:
                        print(f"🔄 Normal extraction failed, trying OCR...")
                        text = extract_text_from_pdf_ocr(tmp_path)
                        print(f"✅ OCR extracted {len(text)} chars")
                    else:
                        print(f"✅ Normal extraction: {len(text)} chars")
                
                elif ext == "docx":
                    text = extract_docx_text(uploaded_file)
                
                # Valid text hai toh add karo
                if text and len(text.strip()) > 20:
                    text = text[:15000]
                    all_texts.append(
                        f"\n{'='*60}\n📁 FILE: {uploaded_file.name}\n{'='*60}\n{text}"
                    )
                    print(f"✅ {uploaded_file.name}: {len(text)} chars added")
                else:
                    st.warning(f"⚠️ {uploaded_file.name} se text extract nahi hua")
                    
            except Exception as e:
                st.error(f"Error in {uploaded_file.name}: {str(e)}")
                print(f"❌ Error processing {uploaded_file.name}: {e}")
        
        if all_texts:
            combined_text = "\n\n".join(all_texts)
            
            # Session state update karo
            st.session_state.document_text = combined_text
            st.session_state.document_lang = detect_language(combined_text)
            st.session_state.document_hash = hash_text(combined_text)
            st.session_state.pdf_paths = pdf_paths  # ✅ Sab PDFs ke paths
            st.session_state.uploaded_files_count = len(uploaded_files)
            
            # 🔥 FIX 3: PDF ko turant FAISS mein store karo
            if pdf_paths:
                try:
                    from memory.vector_store import add_pdf_to_index
                    for i, (path, text_content) in enumerate(zip(pdf_paths, all_texts)):
                        chunks = add_pdf_to_index(text_content, path)
                        print(f"✅ PDF {i+1} stored in FAISS: {chunks} chunks")
                except Exception as e:
                    print(f"⚠️ FAISS store failed: {e}")
            
            st.success(f"✅ {len(uploaded_files)} files loaded!")
            
            with st.expander(f"📚 Loaded Files ({len(uploaded_files)})"):
                for f in uploaded_files:
                    st.write(f"📄 {f.name}")
                if pdf_paths:
                    st.write(f"🗂️ PDF paths: {len(pdf_paths)} stored")
        else:
            st.error("❌ No text could be extracted from uploaded files")
    st.markdown("---")
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.session_state.processed_message_ids = set()
        st.rerun()

if st.session_state.voice_mode:
    st.markdown("""<div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 20px; padding: 20px; text-align: center; margin: 10px 0;'><h3>🎤 Universal Voice Mode Active</h3><p style='font-size: 14px;'>✅ Coding | ✅ Browser | ✅ AutoClicker | ✅ Research | ✅ Document | ✅ PDF | ✅ OS | ✅ Evolution</p><p style='font-size: 12px; margin-top: 10px;'>🗣️ Jo bhi command doge, voice se hoga!</p></div>""", unsafe_allow_html=True)
    audio = mic_recorder(start_prompt="🎤 Click and Speak", stop_prompt="⏹️ Stop", just_once=True, format="wav", key="universal_voice", use_container_width=True)
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
                    st.session_state.messages.append({"role": "user", "content": f"🎤 {user_voice}"})
                    from agents.voice_chat_agent import voice_brain
                    with st.spinner("🧠 JARVIS is thinking..."):
                        response_text = voice_brain(user_voice, voice_mode=True)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
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

if st.session_state.last_generated_pdf:
    pdf_path = st.session_state.last_generated_pdf
    if os.path.exists(pdf_path):
        st.markdown("### 📄 Generated PDF")
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        st.download_button(label="⬇️ Download Generated PDF", data=pdf_bytes, file_name=os.path.basename(pdf_path), mime="application/pdf", use_container_width=True)

if st.session_state.pending_unethical:
    st.warning("⚠️ **Permission Required**")
    st.error(f"Unethical command detected: {st.session_state.pending_unethical['reason']}")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Allow", type="primary", key="allow_unethical"):
            with st.spinner("Executing command..."):
                response = router.route(query=st.session_state.pending_query, context=context if 'context' in locals() else {}, history=st.session_state.messages[-5:])
                data = normalize_router_response(response)
                st.write(f"DEBUG: data.get('generated_code') length = {len(data.get('generated_code', ''))}")
                st.write(f"DEBUG: data.get('agent_used') = {data.get('agent_used')}")
                st.session_state.messages.append({"role": "assistant", "content": data.get("content", "Command executed")})
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

if st.session_state.voice_mode:
    st.markdown("### 🎙️ Speak now")
    audio = mic_recorder(start_prompt="🎤 Start recording", stop_prompt="⏹️ Stop", just_once=True, use_container_width=True)
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
            voice_context = {"voice_mode": True, "coding_stage": st.session_state.coding_state, "generated_code": st.session_state.last_generated_code}
            response = router.route(query=user_voice, context=voice_context, history=st.session_state.messages[-5:])
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

user_input = st.chat_input("Type message…")

if user_input:
    message_id = f"{time.time()}_{hash(user_input)}"
    if message_id in st.session_state.processed_message_ids:
        st.rerun()
    st.session_state.processed_message_ids.add(message_id)
    if len(st.session_state.processed_message_ids) > 100:
        st.session_state.processed_message_ids = set(list(st.session_state.processed_message_ids)[-50:])
    st.session_state.messages.append({"role": "user", "content": user_input})
    context = {"voice_mode": False, "coding_stage": st.session_state.coding_state, "generated_code": st.session_state.last_generated_code}
    if st.session_state.document_text:
        context.update({"document_text": st.session_state.document_text, "document_lang": st.session_state.document_lang, "document_hash": st.session_state.document_hash, "pdf_paths": st.session_state.get("pdf_paths", []), "uploaded_files_count": st.session_state.get("uploaded_files_count", 0)})
    if st.session_state.awaiting_clarification:
        context["clarification_reply"] = True
    history = st.session_state.messages[-5:]
    if not master_agent.is_active():
        st.session_state.messages.append({"role": "assistant", "content": "🚨 System disabled by Master Agent"})
        st.rerun()
    with st.spinner("JARVIS soch raha hai..."):
        try:
            response = router.route(query=user_input, context=context, history=history)
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
                st.session_state.messages.append({"role": "assistant", "content": assistant_content})

                # 🔥 CODING AGENT HANDLING - FIXED INDENTATION
                # ========== CODING AGENT HANDLING ==========
                                # ========== CODING AGENT HANDLING (Single + Multi-file) ==========
                if data.get("agent_used") == "coding":
                    
                    # ========== CHECK IF MULTI-FILE PROJECT ==========
                    if data.get("is_multi_file") and data.get("files"):
                        # Multi-file project display
                        files = data.get("files", [])
                        project_name = data.get("project_name", "project")
                        
                        st.success(f"📁 **Project: {project_name}** - {len(files)} files generated!")
                        
                        # Show file structure
                        with st.expander("📂 Project Structure", expanded=True):
                            st.code("\n".join([f"├── {f['path']}" for f in files]), language="text")
                        
                        # Show each file content
                        for file_info in files:
                            with st.expander(f"📄 {file_info['path']} ({len(file_info['content'])} chars)", expanded=False):
                                ext = file_info['path'].split('.')[-1]
                                if ext in ['py', 'python']:
                                    st.code(file_info['content'], language="python")
                                elif ext in ['json', 'yaml', 'yml']:
                                    st.code(file_info['content'], language="json")
                                elif ext in ['md', 'markdown']:
                                    st.markdown(file_info['content'])
                                else:
                                    st.code(file_info['content'], language="text")
                        
                        # Download ZIP button
                        from agents.coding_super_agent import coding_super_agent
                        zip_data = coding_super_agent.get_downloadable_project()
                        if zip_data:
                            st.download_button(
                                label="📦 Download Complete Project (ZIP)",
                                data=zip_data,
                                file_name=f"{project_name}.zip",
                                mime="application/zip",
                                use_container_width=True
                            )
                        
                        # Also show content for conversation
                        assistant_content = data.get("content", f"✅ Project '{project_name}' generated with {len(files)} files!")
                        st.session_state.messages[-1]["content"] = assistant_content
                        
                    else:
                        # ========== SINGLE FILE CODE HANDLING ==========
                        generated_code = data.get("generated_code", "")
                        
                        # Agar generated_code empty hai to content se extract karo
                        if not generated_code or len(generated_code) < 50:
                            content = data.get("content", "")
                            match = re.search(r"```python\n(.*?)\n```", content, re.DOTALL)
                            if match:
                                generated_code = match.group(1)
                            else:
                                match = re.search(r"```\n(.*?)\n```", content, re.DOTALL)
                                if match:
                                    generated_code = match.group(1)
                        
                        if generated_code and len(generated_code) > 50:
                            from agents.coding_super_agent import coding_super_agent
                            
                            # Current code set karo
                            coding_super_agent.current_code = generated_code
                            func_match = re.search(r'def\s+(\w+)\s*\(', generated_code)
                            if func_match:
                                coding_super_agent.function_name = func_match.group(1)
                            
                            with st.expander("📝 Generated Code", expanded=True):
                                st.code(generated_code, language="python")
                            
                            status = coding_super_agent.get_status()
                            
                            # Button hamesha dikhega jab tak permanently add nahi hota
                            if status.get("permanently_added"):
                                st.success("🎉 Code permanently added to project!")
                            elif status.get("ready_for_permanent"):
                                st.success("🎉 All tests passed! Code is ready.")
                                if st.button("✅ Add Permanently to Project", key="permanent_btn"):
                                    with st.spinner("Adding code to project..."):
                                        func_match = re.search(r'def\s+(\w+)\s*\(', generated_code)
                                        function_name = func_match.group(1) if func_match else None
                                        result = coding_super_agent.apply_permanent_fix(generated_code, function_name=function_name)
                                        if result.get("success"):
                                            st.success(f"✅ Code permanently added to `{result['file']}`")
                                            coding_super_agent.permanently_added = True
                                            st.rerun()
                                        else:
                                            st.error("Failed to add code permanently")
                            else:
                                # ✅ Always show Run button - NO rerun after tests
                                st.info("⚡ Click the button below to run all tests (Sandbox + Integration)")
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.button("🚀 Run All Tests", key="run_all_tests_btn"):
                                        with st.spinner("Running Sandbox tests..."):
                                            sandbox_result = coding_super_agent.run_sandbox_test()
                                            
                                            if sandbox_result.get("passed"):
                                                st.success("✅ Sandbox tests passed!")
                                                
                                                with st.spinner("Running Integration tests..."):
                                                    integration_result = coding_super_agent.run_integration_test()
                                                    
                                                    if integration_result.get("passed"):
                                                        st.success("✅ Integration tests passed!")
                                                        st.balloons()
                                                        # Update status
                                                        coding_super_agent.sandbox_passed = True
                                                        coding_super_agent.integration_passed = True
                                                        st.session_state.coding_state = "ready"
                                                    else:
                                                        st.error(f"❌ Integration tests failed: {integration_result.get('error', 'Unknown error')}")
                                                        # Auto-fix attempt
                                                        st.info("🔧 Attempting to auto-fix code...")
                                                        fixed_code = coding_super_agent._fix_code_from_error(
                                                            coding_super_agent.current_code, 
                                                            integration_result.get('error', ''), 
                                                            "integration"
                                                        )
                                                        if fixed_code and fixed_code != coding_super_agent.current_code:
                                                            coding_super_agent.current_code = fixed_code
                                                            st.success("✅ Code auto-fixed! Click Run Tests again.")
                                                        else:
                                                            st.warning("⚠️ Could not auto-fix automatically")
                                            else:
                                                st.error(f"❌ Sandbox tests failed: {sandbox_result.get('error', 'Unknown error')}")
                                                # Auto-fix attempt
                                                st.info("🔧 Attempting to auto-fix code...")
                                                fixed_code = coding_super_agent._fix_code_from_error(
                                                    coding_super_agent.current_code, 
                                                    sandbox_result.get('error', ''), 
                                                    "sandbox"
                                                )
                                                if fixed_code and fixed_code != coding_super_agent.current_code:
                                                    coding_super_agent.current_code = fixed_code
                                                    st.success("✅ Code auto-fixed! Click Run Tests again.")
                                                else:
                                                    st.warning("⚠️ Could not auto-fix automatically")
                                        
                                        # DO NOT call st.rerun() - let button stay visible
                                        st.rerun()  # Remove this line or keep but button will reappear
                                
                                with col2:
                                    if st.button("🔄 Reset Coding", key="reset_coding_btn"):
                                        if hasattr(coding_super_agent, 'reset'):
                                            coding_super_agent.reset()
                                        st.session_state.coding_state = "idle"
                                        st.session_state.last_generated_code = None
                                        st.rerun()
                                
                                # Show status icons (show real status)
                                sandbox_passed = coding_super_agent.sandbox_passed
                                integration_passed = coding_super_agent.integration_passed
                                sandbox_icon = "✅" if sandbox_passed else "⏳"
                                integration_icon = "✅" if integration_passed else "⏳"
                                st.info(f"📊 Status: Sandbox {sandbox_icon} | Integration {integration_icon}")
                                                        
                            if not (generated_code and len(generated_code) > 50):
                                st.warning(f"⚠️ Generated code is too short ({len(generated_code) if generated_code else 0} chars). Please try again.")
        except Exception as e:
            st.session_state.messages.append({"role": "assistant", "content": f"Sorry, error aaya: {str(e)}"})


st.markdown("---")
st.markdown("## 🖱️ AutoClicker")
col1, col2 = st.columns([3, 1])
with col1:
    autoclicker_input = st.text_input("🎯 Command:", placeholder="e.g., click on Scan System Health, click on Disable JARVIS, click on Clear Chat", key="autoclicker_simple")
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

st.markdown("---")
st.markdown("## ⚡ Direct System Control (OS / Browser / Research)")
direct_input = st.text_input("⚡ Direct System Command", key="direct_chat")
col1, col2 = st.columns(2)
with col1:
    if st.button("Send Direct Command", use_container_width=True):
        if not direct_input.strip():
            st.warning("Please enter command first")
        else:
            st.session_state.direct_messages.append({"role": "user", "content": direct_input})
            response_text = ""
            ql = direct_input.lower()
            try:
                research_keywords = ["research", "do research", "research about", "research on", "deep research", "internet research", "find information on", "search for topic", "look up topic", "study topic", "train yourself", "trained on"]
                if any(x in ql for x in research_keywords):
                    result = research_handler.handle(direct_input)
                    response_text = result.get("content", str(result))
                else:
                    result = os_handler.handle(direct_input)
                    response_text = result.get("content", str(result))
            except Exception as e:
                response_text = f"Error: {str(e)}"
            st.session_state.direct_messages.append({"role": "assistant", "content": response_text})
            st.rerun()
with col2:
    if st.button("❌ Clear History", use_container_width=True):
        st.session_state.direct_messages = []
        st.rerun()
for msg in st.session_state.direct_messages[-6:]:
    if msg["role"] == "user":
        st.markdown(f"<div class='chat-bubble user-bubble'>⚡ {msg['content']}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='chat-bubble ai-bubble'>🛠 {msg['content']}</div>", unsafe_allow_html=True)

st.markdown("---")
st.markdown("### 💬 Conversation")
for msg in st.session_state.messages[-12:]:
    if msg["role"] == "user":
        st.markdown(f"<div class='chat-bubble user-bubble'>👤 {msg['content']}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='chat-bubble ai-bubble'>🤖 {msg['content']}</div>", unsafe_allow_html=True)
st.markdown("---")
st.markdown("© 2024 JARVIS AI System")
