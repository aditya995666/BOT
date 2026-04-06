import os
import re
import time

class OSHandler:

    SAFE_ACTIONS = {
        "open_app",
        "close_app",
        "type_text",
        "click_mouse",
        "search_google",
        "open_browser",
        "create_file",
        "run_python",
        "shutdown",
        "open_camera_live",
        "capture_webcam",
        "take_screenshot",
        "run_full_activity_capture",
        "web_scan",
        "search_in_current_tab",
        "search_on_youtube"
    }

    def __init__(self, os_agent):
        self.os_agent = os_agent
        self.pending_new_file = False  # 🔥 NEW: Track if waiting for filename

    def handle(self, q: str):
        if not self.os_agent:
            return {"content": "❌ OS agent available nahi hai (import failed)"}

        ql = q.lower().strip()

        # Jab user "new file banana hai" bolega to filename puchenge
        if self.pending_new_file:
            self.pending_new_file = False
            filename = q.strip()
            # Clean filename
            if '.' not in filename:
                filename = filename + '.txt'
            filename = re.sub(r'[^\w\-_\.]', '', filename)
            if not filename:
                filename = "note.txt"
            result = self.os_agent.create_and_open_file(filename)
            return {"content": result}

        if any(x in ql for x in ["ye search kro", "search now", "current tab mein search", "is page mein search", "ye search kar", "ab search kar"]):
            search_query = q
            for word in ["ye search kro", "search now", "current tab mein search", "is page mein search", "ye search kar", "ab search kar"]:
                search_query = search_query.replace(word, "")
            search_query = search_query.strip()
            
            if search_query and len(search_query) > 1:
                if hasattr(self.os_agent, 'search_in_current_tab'):
                    result = self.os_agent.search_in_current_tab(search_query)
                    return {"content": result}
                else:
                    return {"content": f"❌ search_in_current_tab method nahi hai."}
            else:
                return {"content": "Kya search karu? Query batao."}

        if any(x in ql for x in ["youtube search", "youtube par search", "yt search", "youtube pe search"]):
            search_query = q
            for word in ["youtube search", "youtube par search", "yt search", "youtube pe search"]:
                search_query = search_query.replace(word, "")
            search_query = search_query.strip()
            
            if search_query and len(search_query) > 1:
                if hasattr(self.os_agent, 'search_on_youtube'):
                    result = self.os_agent.search_on_youtube(search_query)
                    return {"content": result}
                else:
                    return {"content": f"❌ search_on_youtube method nahi hai."}
            else:
                return {"content": "YouTube par kya search karu? Batao."}

        if ql.startswith("search ") and not any(x in ql for x in ["youtube", "google"]):
            search_query = q[7:].strip()
            if search_query:
                if hasattr(self.os_agent, 'search_on_google'):
                    result = self.os_agent.search_on_google(search_query)
                    return {"content": result}
                else:
                    self.os_agent.open_app("google")
                    time.sleep(2)
                    if hasattr(self.os_agent, 'search_in_current_tab'):
                        result = self.os_agent.search_in_current_tab(search_query)
                        return {"content": result}
                    else:
                        return {"content": f"🔍 Google search for '{search_query}'"}
            else:
                return {"content": "Kya search karu? Batao."}

        # Jab user "nayi file banao" ya "new file" bole
        if any(x in ql for x in ["nayi file banao", "new file", "create new file", "naya file banao", "nayi file create karo"]):
            # Reset current file pointer - purani file close nahi hogi, bas nayi banegi
            self.pending_new_file = True
            return {"content": "Nayi file ka kya naam rakhna hai? (Jaise: my_notes, project, etc.)"}

        # Agar user ne directly "file naam.txt banao" bola
        if any(x in ql for x in ["banao", "create file", "file banao"]) and not self.pending_new_file:
            # Extract filename
            filename = None
            
            # Pattern 1: "file naam.txt banao"
            match = re.search(r'(?:file|note)\s+([^\s]+\.txt)\s+(?:banao|create)', ql)
            if match:
                filename = match.group(1)
            
            # Pattern 2: "banao file naam.txt"
            if not filename:
                match = re.search(r'banao\s+(?:file|note)\s+([^\s]+)', ql)
                if match:
                    filename = match.group(1)
            
            # Pattern 3: "create file naam.txt"
            if not filename:
                match = re.search(r'create\s+file\s+([^\s]+)', ql)
                if match:
                    filename = match.group(1)
            
            if filename:
                if '.' not in filename:
                    filename += '.txt'
                filename = re.sub(r'[^\w\-_\.]', '', filename)
                result = self.os_agent.create_and_open_file(filename)
                return {"content": result}
            else:
                # Agar filename nahi diya to pucho
                self.pending_new_file = True
                return {"content": "File ka kya naam rakhna hai? (Jaise: myfile.txt)"}

        # Jab user "file kholo" bole
        if any(x in ql for x in ["file kholo", "open file", "note kholo", "open note"]):
            # Check if specific filename given
            remaining = q.replace("file kholo", "").replace("open file", "").replace("note kholo", "").replace("open note", "").strip()
            
            if remaining and len(remaining) > 2:
                # Specific file open karna hai
                filename = remaining
                if '.' not in filename:
                    filename += '.txt'
                filename = re.sub(r'[^\w\-_\.]', '', filename)
                
                # Check in multiple locations
                possible_paths = [
                    os.path.join("files", filename),
                    os.path.join(os.getcwd(), filename),
                    os.path.join(os.getcwd(), "files", filename),
                ]
                
                file_opened = False
                for path in possible_paths:
                    if os.path.exists(path):
                        os.startfile(path)
                        self.os_agent.current_file = path
                        print(f"📂 Opened: {path}")
                        return {"content": f"{filename} opened ✅"}
                
                # File exist nahi karti
                return {"content": f"File '{filename}' exist nahi karti. Pehle 'nayi file banao' se banao."}
            else:
                # Sirf "open file" bola - current file kholo ya notepad
                if self.os_agent.current_file and os.path.exists(self.os_agent.current_file):
                    os.startfile(self.os_agent.current_file)
                    return {"content": f"Current file opened: {os.path.basename(self.os_agent.current_file)} ✅"}
                else:
                    # Notepad khol do
                    os.system("notepad.exe")
                    return {"content": "Notepad opened ✅ (koi active file nahi hai)"}

        if any(x in ql for x in ["open camera", "start camera", "camera on", "camera khol"]):
            result = self.os_agent.open_camera_live()
            return {"content": result}

        if any(x in ql for x in ["take photo", "capture photo", "click photo", "webcam photo", "photo le"]):
            path = self.os_agent.capture_webcam()
            return {"content": f"📸 Photo captured: {path}" if path else "Photo try kiya gaya"}

        if any(x in ql for x in ["screenshot le", "screenshot lo", "capture screen", "take screenshot"]):
            match = re.search(r'(?:screenshot le|screenshot lo|screenshot|screen)(?:\s+as\s+|\s+name\s+|\s+)(.+?)(?:\s*$)', q, re.IGNORECASE)
            if match:
                filename = match.group(1).strip()
                result = self.os_agent.take_screenshot(filename)
            else:
                self.os_agent.pending_screenshot_name = True
                return {"content": "Kis naam se screenshot save karu?", "needs_filename": True}
            return {"content": result}

        if any(x in ql for x in ["web scan", "scan website", "website scan", "page scan"]):
            match = re.search(r'(?:web scan|scan website|website scan)(?:\s+as\s+|\s+name\s+|\s+)(.+?)(?:\s*$)', q, re.IGNORECASE)
            if match:
                filename = match.group(1).strip()
                result = self.os_agent.run_web_scan(filename)
            else:
                self.os_agent.pending_webscan_name = True
                return {"content": "Kis naam se web scan save karu?", "needs_filename": True}
            return {"content": result}

        if "shutdown" in ql:
            result = self.os_agent.shutdown()
            return {"content": result}

        if "open " in ql and not any(x in ql for x in ["open file", "open camera"]):
            app = ql.split("open ", 1)[1].strip()
            result = self.os_agent.open_app(app)
            return {"content": result}

        if "close " in ql:
            app = ql.split("close ", 1)[1].strip()
            result = self.os_agent.close_app(app)
            return {"content": result}

        if "start writing" in ql:
            if not self.os_agent.current_file:
                return {"content": "Pehle 'nayi file banao' ya 'file kholo' command se file create/open karo."}
            self.os_agent.live_writing = True
            return {"content": f"✍️ Writing mode started in {os.path.basename(self.os_agent.current_file)}"}

        if "stop writing" in ql:
            self.os_agent.live_writing = False
            import pyautogui
            pyautogui.hotkey('ctrl', 's')
            return {"content": "✅ Writing stopped and file saved"}

        if any(x in ql for x in ["type ", "write ", "enter text"]) or self.os_agent.live_writing:
            text_to_type = ""
            for prefix in ["type ", "write ", "enter text "]:
                if prefix in q:
                    text_to_type = q.split(prefix, 1)[1].strip()
                    break
            
            if not text_to_type:
                return {"content": "Kya type karu? Text batao."}
            
            if self.os_agent.current_file:
                result = self.os_agent.append_to_file(os.path.basename(self.os_agent.current_file), text_to_type)
                return {"content": result}
            else:
                # Pehle file banane ko bolo
                return {"content": "Pehle 'nayi file banao' command se file banao, phir likho."}

        if "click" in ql:
            self.os_agent.click_mouse()
            return {"content": "Mouse click kar diya"}

        if any(x in ql for x in ["run python", "execute python"]):
            parts = q.split()
            filename = parts[-1] if parts[-1].endswith(".py") else "script.py"
            result = self.os_agent.run_python(filename)
            return {"content": result}

        if hasattr(self.os_agent, 'pending_screenshot_name') and self.os_agent.pending_screenshot_name:
            self.os_agent.pending_screenshot_name = False
            filename = q.strip()
            result = self.os_agent.take_screenshot(filename)
            return {"content": result}
            
        if hasattr(self.os_agent, 'pending_webscan_name') and self.os_agent.pending_webscan_name:
            self.os_agent.pending_webscan_name = False
            filename = q.strip()
            result = self.os_agent.run_web_scan(filename)
            return {"content": result}

        return {"content": "OS command samajh nahi aaya"}