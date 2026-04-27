from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from agents.os_control_agent import OSControlAgent
from agents.browser_control_agent import BrowserControlAgent
from agents.research_agent import ResearchAgent
from brain.gemini_llm import GeminiBrain


app = FastAPI(title="JARVIS OS API")
import uuid

research_jobs = {}

os_agent = OSControlAgent()
browser_agent = BrowserControlAgent()
research_agent = ResearchAgent()


security = HTTPBearer()
SECRET_TOKEN = "jarvis123"   # 🔐 Change in production

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid or Missing Token")


class GeminiAdapter:
    def __init__(self):
        self.brain = GeminiBrain()

    def generate(self, prompt: str):
        return self.brain.think(prompt)

llm_adapter = GeminiAdapter()
from agents.router import IntelligentRouter

router_instance = IntelligentRouter()


@app.get("/")
def root():
    return {"status": "JARVIS OS API Running 🚀"}# --- Basic Browser Operations ---

@app.post("/browser/open")
def open_browser(url: str, token: HTTPAuthorizationCredentials = Depends(verify_token)):
    try:
        result = browser_agent.open_url(url)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/browser/close")
def close_browser(token: HTTPAuthorizationCredentials = Depends(verify_token)):
    try:
        result = browser_agent.close_browser()
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/browser/extract-form")
def extract_form(token: HTTPAuthorizationCredentials = Depends(verify_token)):
    try:
        fields = browser_agent.extract_form_fields()
        return {"success": True, "fields": fields}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/browser/fill-form")
def fill_form(data: dict, token: HTTPAuthorizationCredentials = Depends(verify_token)):
    try:
        result = browser_agent.fill_form(data)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/browser/click")
def click_element(text: str, token: HTTPAuthorizationCredentials = Depends(verify_token)):
    try:
        result = browser_agent.click_element(text)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/browser/submit")
def submit_form(token: HTTPAuthorizationCredentials = Depends(verify_token)):
    try:
        result = browser_agent.submit_form()
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/browser/screenshot")
def screenshot(token: HTTPAuthorizationCredentials = Depends(verify_token)):
    try:
        path = browser_agent.take_screenshot()
        return {"success": True, "result": f"Screenshot saved: {path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Form Operations ---
@app.get("/browser/extract-form")
def extract_form_duplicate(token: HTTPAuthorizationCredentials = Depends(verify_token)):
    """Extract all form fields from current page"""
    try:
        fields = browser_agent.extract_form_fields()
        return {"success": True, "fields": fields}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/browser/fill-form")
def fill_form_duplicate(data: dict, token: HTTPAuthorizationCredentials = Depends(verify_token)):
    """Fill multiple form fields at once"""
    try:
        result = browser_agent.fill_form(data)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/browser/close_duplicate")
def close_browser_duplicate(token: HTTPAuthorizationCredentials = Depends(verify_token)):
    try:
        result = browser_agent.close_browser()
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/browser/fill-single")
def fill_single_field(identifier: str, value: str, token: HTTPAuthorizationCredentials = Depends(verify_token)):
    """Fill a single form field"""
    try:
        result = browser_agent.fill_single_field(identifier, value)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/browser/submit_duplicate")
def submit_form_duplicate(token: HTTPAuthorizationCredentials = Depends(verify_token)):
    """Submit the current form"""
    try:
        result = browser_agent.submit_form()
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Smart Form Filling (Step by Step) ---
@app.post("/browser/form/start")
def start_form_filling(token: HTTPAuthorizationCredentials = Depends(verify_token)):
    """Start an interactive form filling session"""
    try:
        result = browser_agent.start_form_filling()
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/browser/form/fill")
def fill_form_field(value: str, token: HTTPAuthorizationCredentials = Depends(verify_token)):
    """Fill the current field in the form session"""
    try:
        result = browser_agent.fill_field(value)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/browser/form/complete")
def complete_form(token: HTTPAuthorizationCredentials = Depends(verify_token)):
    """Complete the form filling session"""
    try:
        result = browser_agent.complete_form()
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/browser/form/fields")
def get_form_fields(token: HTTPAuthorizationCredentials = Depends(verify_token)):
    """Get all form fields (alias for extract-form)"""
    try:
        fields = browser_agent.extract_form_fields()
        return {"success": True, "fields": fields}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


from fastapi import BackgroundTasks

def run_research(job_id: str, topic: str):
    try:
        print(f"\n🔎 [JOB {job_id}] Research Started for topic: {topic}")

        research_jobs[job_id]["status"] = "running"
        result = research_agent.research_topic(topic)

        research_jobs[job_id]["status"] = "completed"
        research_jobs[job_id]["result"] = result

        print(f"\n✅ [JOB {job_id}] Research COMPLETED successfully!\n")

    except Exception as e:
        research_jobs[job_id]["status"] = "failed"
        research_jobs[job_id]["result"] = str(e)

        print(f"\n❌ [JOB {job_id}] Research FAILED: {str(e)}\n")
        
@app.post("/research/train")
def research_and_train(
    topic: str,
    background_tasks: BackgroundTasks,
    token: HTTPAuthorizationCredentials = Depends(verify_token)
):
    job_id = str(uuid.uuid4())

    research_jobs[job_id] = {
        "status": "queued",
        "result": None
    }

    run_research(job_id, topic)

    return {
        "success": True,
        "job_id": job_id,
        "status": research_jobs[job_id]["status"],
        "result": research_jobs[job_id]["result"]
    }

@app.get("/research/status/{job_id}")
def get_research_status(
    job_id: str,
    token: HTTPAuthorizationCredentials = Depends(verify_token)
):
    if job_id not in research_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return research_jobs[job_id]

@app.post("/research/train_sync")
def research_and_train_sync(topic: str, token: HTTPAuthorizationCredentials = Depends(verify_token)):
    try:
        result = research_agent.research_topic(topic)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/camera/open")
def open_camera(token: HTTPAuthorizationCredentials = Depends(verify_token)):
    try:
        result = os_agent.open_camera_live()
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/camera/photo")
def take_photo(token: HTTPAuthorizationCredentials = Depends(verify_token)):
    try:
        path = os_agent.capture_webcam()
        return {"success": True, "result": f"Photo saved: {path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/screen/capture")
def capture_screen(token: HTTPAuthorizationCredentials = Depends(verify_token)):
    try:
        result = os_agent.run_full_activity_capture()
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/app/open")
def open_app(app: str, token: HTTPAuthorizationCredentials = Depends(verify_token)):
    try:
        result = os_agent.open_app(app)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/app/close")
def close_app(app: str, token: HTTPAuthorizationCredentials = Depends(verify_token)):
    try:
        result = os_agent.close_app(app)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mouse/click")
def click_mouse(token: HTTPAuthorizationCredentials = Depends(verify_token)):
    try:
        result = os_agent.click_mouse()
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/keyboard/type")
def type_text(text: str, token: HTTPAuthorizationCredentials = Depends(verify_token)):
    try:
        result = os_agent.type_text(text)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/file/create")
def create_file(name: str, content: str = "", token: HTTPAuthorizationCredentials = Depends(verify_token)):
    try:
        result = os_agent.create_file(name, content)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/file/append")
def append_file(name: str, content: str, token: HTTPAuthorizationCredentials = Depends(verify_token)):
    try:
        result = os_agent.append_to_file(name, content)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/python/run")
def run_python(name: str, token: HTTPAuthorizationCredentials = Depends(verify_token)):
    try:
        result = os_agent.run_python(name)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/system/shutdown")
def shutdown(token: HTTPAuthorizationCredentials = Depends(verify_token)):
    try:
        result = os_agent.shutdown()
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/web/scan")
def web_scan(filename: str = None, token: HTTPAuthorizationCredentials = Depends(verify_token)):
    try:
        if filename:
            result = os_agent.run_web_scan(filename)
        else:
            result = os_agent.run_web_scan()
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




