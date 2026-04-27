from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import os
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time
import re
from typing import Dict, List, Optional, Any
import logging

logging.basicConfig(
    filename="automation.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class BrowserControlAgent:
    def __init__(self):
        self.driver = None
        self.form_session = None
        self._chrome_path = None
        self.multi_step_data = {}
        self.current_step = 0
        self.total_steps = 0
        self.step_completed = False

    def _find_chrome_path(self):
        if self._chrome_path:
            return self._chrome_path
            
        possible_paths = [
            
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                self._chrome_path = path
                return path
        
        return None

    def _init_driver(self):
        if self.driver:
            return True
    
        try:
            chrome_path = self._find_chrome_path()
        
            if not chrome_path:
                logging.error("Chrome not found.")
                return False
        
            options = Options()
            options.add_argument("--start-maximized")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.page_load_strategy = "eager"
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.binary_location = chrome_path
        
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
        
            return True
        
        except Exception as e:
            logging.error(f"Failed to initialize Chrome driver: {e}")
            return False

    def open_url(self, url: str):
        try:
            if not self._init_driver():
                return "❌ Failed to initialize Chrome driver"
            
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            
            self.driver.set_page_load_timeout(15)
            
            try:
                self.driver.get(url)
            except TimeoutException:
                self.driver.execute_script("window.stop();")
                time.sleep(1)
            
            time.sleep(2)
            return f"✅ Site opened: {url}"
                
        except Exception as e:
            return f"❌ Failed to open {url}: {str(e)}"

    def click_element(self, text: str):
        if not self.driver:
            return "Browser not started."

        text = text.strip().lower()
        
        try:
            xpaths = [
                f"//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{text}')]",
                f"//a[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{text}')]",
                f"//span[contains(text(), '{text}')]",
                f"//div[contains(text(), '{text}')]",
                f"//input[@value='{text}']",
                f"//*[@aria-label='{text}']"
            ]
            
            for xpath in xpaths:
                try:
                    element = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    self.driver.execute_script("arguments[0].click();", element)
                    time.sleep(0.5)
                    return f"✅ Clicked on '{text}'"
                except:
                    continue
            
            return f"❌ Could not find '{text}' to click"
            
        except Exception as e:
            return f"❌ Error: {str(e)}"

    def detect_captcha(self):
        try:
            captcha_selectors = [
                "iframe[src*='recaptcha']",
                "iframe[src*='captcha']",
                ".g-recaptcha",
                "#recaptcha"
            ]
            for selector in captcha_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for el in elements:
                    if el.is_displayed():
                        return True
            return False
        except:
            return False
    
    def detect_otp_field(self, field):
        keywords = ["otp", "code", "verification", "pin"]
        name = (field.get("name") or "").lower()
        label = (field.get("label") or "").lower()
        return any(k in name or k in label for k in keywords)
    
    def detect_next_button(self):
        try:
            next_texts = ["next", "continue", "proceed", "下一步", "继续", "続ける"]
            for text in next_texts:
                xpaths = [f"//button[contains(text(), '{text}')]", f"//a[contains(text(), '{text}')]"]
                for xpath in xpaths:
                    try:
                        elements = self.driver.find_elements(By.XPATH, xpath)
                        for element in elements:
                            if element.is_displayed() and element.is_enabled():
                                return element
                    except:
                        pass
            return None
        except:
            return None

    def extract_all_form_fields(self):
        """100% AUTOMATIC FIELD DETECTION - NO HARDCODED LABELS"""
        if not self.driver:
            return []

        fields = []
        
        try:
            # Wait for page
            self.smart_wait(3)
            time.sleep(1)
            
            # Quick scroll to load content
            for scroll in range(3):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.2)
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(0.2)
            
            # Find all form elements
            all_elements = []
            all_elements.extend(self.driver.find_elements(By.CSS_SELECTOR, "input:not([type='hidden']):not([type='submit']):not([type='button'])"))
            all_elements.extend(self.driver.find_elements(By.TAG_NAME, "select"))
            all_elements.extend(self.driver.find_elements(By.TAG_NAME, "textarea"))
            
            for element in all_elements:
                try:
                    if not element.is_displayed():
                        continue
                    
                    tag = element.tag_name
                    elem_type = element.get_attribute("type") or tag
                    
                    if elem_type in ["submit", "reset", "button"]:
                        continue
                    
                    name = element.get_attribute("name") or ""
                    elem_id = element.get_attribute("id") or ""
                    placeholder = element.get_attribute("placeholder") or ""
                    
                    # 🔥 AUTOMATIC LABEL DETECTION - PURE DETECTION, NO HARDCODING
                    label = ""
                    
                    # Method 1: Label with for attribute
                    if elem_id:
                        label_elem = self.driver.find_elements(By.XPATH, f"//label[@for='{elem_id}']")
                        if label_elem:
                            label = label_elem[0].text.strip()
                    
                    # Method 2: Parent label
                    if not label:
                        parent_label = element.find_elements(By.XPATH, "./ancestor::label")
                        if parent_label:
                            label = parent_label[0].text.strip()
                    
                    # Method 3: Following sibling label
                    if not label:
                        following = element.find_elements(By.XPATH, "./following-sibling::label")
                        if following:
                            label = following[0].text.strip()
                    
                    # Method 4: Placeholder (use as is)
                    if not label and placeholder:
                        label = placeholder.strip()
                    
                    # Method 5: Name attribute (clean only underscores/dashes)
                    if not label and name:
                        label = name.replace("_", " ").replace("-", " ").strip()
                        # Capitalize first letter of each word
                        label = " ".join([w.capitalize() for w in label.split()])
                    
                    # Method 6: ID attribute
                    if not label and elem_id:
                        label = elem_id.replace("_", " ").replace("-", " ").strip()
                        label = " ".join([w.capitalize() for w in label.split()])
                    
                    # Method 7: aria-label
                    if not label:
                        aria_label = element.get_attribute("aria-label")
                        if aria_label:
                            label = aria_label.strip()
                    
                    # Method 8: Title attribute
                    if not label:
                        title = element.get_attribute("title")
                        if title:
                            label = title.strip()
                    
                    # Skip if no label found
                    if not label or len(label) < 2:
                        continue
                    
                    # 🔥 NO HARDCODED LABEL MAPPING - Keep original detected label
                    # Just clean up extra spaces
                    label = " ".join(label.split())
                    
                    # Get select options
                    select_options = None
                    if tag == "select":
                        options = element.find_elements(By.TAG_NAME, "option")
                        select_options = [{"value": opt.get_attribute("value"), "text": opt.text.strip()} 
                                        for opt in options if opt.text.strip()]
                    
                    # 🔥 ALL FIELDS ARE REQUIRED
                    field_info = {
                        "name": name,
                        "id": elem_id,
                        "type": elem_type,
                        "tag": tag,
                        "label": label,
                        "placeholder": placeholder,
                        "required": True,
                        "value": None,
                        "select_options": select_options,
                        "element": element,
                        "visible": True
                    }
                    
                    # Avoid duplicates by label
                    if not any(f["label"] == label for f in fields):
                        fields.append(field_info)
                    
                except Exception:
                    continue
            
            # Remove duplicates by label
            unique_fields = {}
            for f in fields:
                label = f["label"]
                if label and label not in unique_fields:
                    unique_fields[label] = f
            
            fields = list(unique_fields.values())
            
            # 🔥 NO HARDCODED SORTING - Keep fields in order they appear
            # Fields are already in HTML order
            
        except Exception as e:
            print(f"Error: {e}")
        
        return fields
    
    def detect_auth_page(self):
        try:
            buttons = self.driver.find_elements(By.XPATH, "//button|//a|//div")
            login_found = False
            signup_found = False
        
            for btn in buttons:
                try:
                    text = btn.text.lower()
                    if any(x in text for x in ["login", "log in", "sign in"]):
                        login_found = True
                    if any(x in text for x in ["sign up", "create", "register", "new account"]):
                        signup_found = True
                except:
                    continue
        
            if login_found and signup_found:
                return "both"
            elif login_found:
                return "login"
            elif signup_found:
                return "signup"
            return None
        except:
            return None

    def auto_click_signup(self):
        try:
            signup_keywords = ["create", "sign up", "register", "new account"]
            elements = self.driver.find_elements(By.XPATH, "//button|//a|//div")
        
            for el in elements:
                try:
                    text = el.text.lower()
                    if any(k in text for k in signup_keywords):
                        if el.is_displayed() and el.is_enabled():
                            self.driver.execute_script("arguments[0].click();", el)
                            time.sleep(2)
                            return True
                except:
                    continue
            return False
        except:
            return False
   
    def start_form_filling(self):
        try:
            # Detect login/signup
            auth_type = self.detect_auth_page()

            if auth_type == "both":
                return {
                    "success": True,
                    "auth_choice": True,
                    "message": "🔐 Do you want to Login or Create Account?",
                    "options": ["login", "signup"]
                }
            
            self.auto_click_signup()
            self.smart_wait(3)
            time.sleep(1)
            
            # Extract ALL fields
            fields = self.extract_all_form_fields()
            
            if not fields:
                return {
                    "success": False,
                    "message": "No form fields found.",
                    "fields": []
                }
            
            # 🔥 ALL FIELDS ARE REQUIRED
            required_fields = fields
            optional_fields = []
            
            # Create form session
            self.form_session = {
                "active": True,
                "all_fields": fields,
                "required_fields": required_fields,
                "optional_fields": optional_fields,
                "current_index": 0,
                "answers": {},
                "status": "required",
                "step": self.current_step,
                "step_completed": False
            }
            
            # Get first field question
            first_field = required_fields[0] if required_fields else None
            
            if first_field:
                if first_field.get("select_options"):
                    options = ", ".join([opt["text"] for opt in first_field["select_options"][:8]])
                    return {
                        "success": True,
                        "message": f"✅ Found {len(fields)} fields to fill",
                        "fields": fields,
                        "required_fields": required_fields,
                        "next_field": {
                            "field": first_field,
                            "type": "select",
                            "question": f"📝 {first_field['label']} (options: {options}):",
                            "field_type": first_field["type"],
                            "options": first_field.get("select_options")
                        },
                        "is_multi_step": self.total_steps > 0
                    }
                else:
                    return {
                        "success": True,
                        "message": f"✅ Found {len(fields)} fields to fill",
                        "fields": fields,
                        "required_fields": required_fields,
                        "next_field": {
                            "field": first_field,
                            "type": "text",
                            "question": f"📝 {first_field['label']}:",
                            "field_type": first_field["type"]
                        },
                        "is_multi_step": self.total_steps > 0
                    }
            
            return {
                "success": True,
                "message": f"✅ Found {len(fields)} fields to fill",
                "fields": fields,
                "required_fields": required_fields,
                "next_field": None,
                "is_multi_step": self.total_steps > 0
            }
        except Exception as e:
            print(f"Error in start_form_filling: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "fields": []
            }
    
    def smart_wait(self, timeout=3):
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except:
            pass
    
    def get_next_field(self):
        if not self.form_session or not self.form_session["active"]:
            return self.start_form_filling()
        
        try:
            if self.form_session["current_index"] < len(self.form_session["required_fields"]):
                field = self.form_session["required_fields"][self.form_session["current_index"]]
                
                if field.get("select_options"):
                    options = ", ".join([opt["text"] for opt in field["select_options"][:8]])
                    return {
                        "field": field,
                        "type": "select",
                        "question": f"📝 {field['label']} (options: {options}):",
                        "field_type": field["type"],
                        "options": field.get("select_options")
                    }
                else:
                    return {
                        "field": field,
                        "type": "text",
                        "question": f"📝 {field['label']}:",
                        "field_type": field["type"]
                    }
            
            # All fields filled - complete form
            return self.complete_form()
            
        except Exception as e:
            print(f"Error in get_next_field: {e}")
            return None
    
    def fill_field(self, value):
        # Handle auth choice
        if not self.form_session or not self.form_session["active"]:
            if value.lower() in ["signup", "create", "register"]:
                try:
                    signup_btns = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Create new account') or contains(text(), 'Sign up') or contains(text(), 'Register')]")
                    for btn in signup_btns:
                        if btn.is_displayed() and btn.is_enabled():
                            self.driver.execute_script("arguments[0].click();", btn)
                            time.sleep(2)
                            break
                    return self.start_form_filling()
                except:
                    return {"success": False, "message": "Failed to click signup"}
            elif value.lower() in ["login", "sign in"]:
                return self.start_form_filling()
            
            # Start new session
            return self.start_form_filling()
    
        try:
            # Get current field
            if self.form_session["current_index"] >= len(self.form_session["required_fields"]):
                return self.complete_form()
            
            current_field = self.form_session["required_fields"][self.form_session["current_index"]]
            
            if not current_field:
                return {"success": False, "message": "No field to fill"}
            
            # Fill the field
            success = self.fill_single_field_by_info(current_field, value)
        
            if success:
                field_key = current_field["id"] or current_field["name"] or current_field["label"]
                self.form_session["answers"][field_key] = value
                self.form_session["current_index"] += 1
                
                # Get next field
                next_field = self.get_next_field()
                
                return {
                    "success": True,
                    "filled": True,
                    "next_field": next_field
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to fill field: {current_field['label']}"
                }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }
    
    def fill_single_field_by_info(self, field_info: Dict, value: str):
        if not self.driver:
            return False
        
        try:
            element = field_info.get("element")
            if not element:
                if field_info.get("id"):
                    try:
                        element = self.driver.find_element(By.ID, field_info["id"])
                    except:
                        pass
                if not element and field_info.get("name"):
                    try:
                        element = self.driver.find_element(By.NAME, field_info["name"])
                    except:
                        pass
            
            if element:
                # Scroll into view
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                time.sleep(0.2)
                
                field_type = field_info.get("type", "text").lower()
                value_lower = str(value).lower()
                
                # Radio buttons
                if field_type in ["radio", "radio_group"]:
                    radio_name = field_info.get("name")
                    if radio_name:
                        radios = self.driver.find_elements(By.NAME, radio_name)
                    else:
                        radios = [element]
                    
                    for radio in radios:
                        if radio.is_displayed() and radio.is_enabled():
                            radio_val = (radio.get_attribute("value") or "").lower()
                            if value_lower in radio_val:
                                self.driver.execute_script("arguments[0].click();", radio)
                                time.sleep(0.2)
                                return True
                    
                    # Fallback: click first radio
                    for radio in radios:
                        if radio.is_displayed() and radio.is_enabled():
                            self.driver.execute_script("arguments[0].click();", radio)
                            time.sleep(0.2)
                            return True
                    return False
                
                # Checkboxes
                elif field_type in ["checkbox", "check_box"]:
                    is_checked = element.is_selected()
                    if value_lower in ["yes", "true", "1", "check", "tick"] and not is_checked:
                        self.driver.execute_script("arguments[0].click();", element)
                        time.sleep(0.2)
                        return True
                    return True
                
                # Select dropdown
                elif field_type in ["select", "dropdown", "select-one"]:
                    from selenium.webdriver.support.ui import Select
                    select = Select(element)
                    try:
                        select.select_by_visible_text(value)
                    except:
                        try:
                            select.select_by_value(str(value))
                        except:
                            for option in select.options:
                                if value_lower in option.text.lower():
                                    self.driver.execute_script("arguments[0].click();", option)
                                    break
                    time.sleep(0.2)
                    return True
                
                # Text inputs
                else:
                    try:
                        self.driver.execute_script("arguments[0].click();", element)
                    except:
                        try:
                            element.click()
                        except:
                            pass
                    
                    element.clear()
                    element.send_keys(str(value))
                    time.sleep(0.2)
                    return True
                
            return False
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    def complete_form(self):
        if not self.form_session:
            return {"success": False, "message": "No active form session"}
        
        self.form_session["active"] = False
        total_fields = len(self.form_session["answers"])
        
        # Auto submit
        submit_result = self.submit_form()
        
        return {
            "success": True,
            "complete": True,
            "message": f"✅ Form completed! {total_fields} fields filled.\n{submit_result}",
            "answers": self.form_session["answers"],
            "total_fields_filled": total_fields
        }
    
    def submit_form(self):
        if not self.driver:
            return "Browser not started"

        submit_selectors = [
            "button[type='submit']",
            "input[type='submit']",
            "#submit",
            ".submit",
            "button[id='submit']",
            "button"
        ]

        for selector in submit_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    text = element.text.lower()
                    if element.is_displayed() and element.is_enabled():
                        if "submit" in text or "register" in text or "sign" in text or "create" in text or element.get_attribute("type") == "submit":
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                            time.sleep(0.3)
                            self.driver.execute_script("arguments[0].click();", element)
                            time.sleep(2)
                            return "✅ Form submitted successfully!"
            except:
                continue
        
        # Try by text
        try:
            elements = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Submit') or contains(text(), 'submit') or contains(text(), 'Register') or contains(text(), 'Sign Up') or contains(text(), 'Create')]")
            for element in elements:
                if element.is_displayed() and element.is_enabled():
                    self.driver.execute_script("arguments[0].click();", element)
                    time.sleep(2)
                    return "✅ Form submitted successfully!"
        except:
            pass
        
        return "⚠️ Submit button not found, but form data saved"
    
    def close_browser(self):
        try:
            if self.driver:
                self.driver.quit()
            self.driver = None
            self.form_session = None
            self.multi_step_data = {}
            self.current_step = 0
            self.total_steps = 0
            return "Browser closed"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def get_page_title(self):
        if not self.driver:
            return None
        try:
            return self.driver.title
        except:
            return None
from playwright.sync_api import sync_playwright
import os
import time

class BrowserControlAgent:
    def __init__(self):
        self.play = None
        self.browser = None
        self.page = None

    # ────────────────────────────────────────────────
    # NEW: Chrome already open ho to attach ho jaaye
    # ────────────────────────────────────────────────
    def attach_to_running_chrome(self, debug_port=9222):
        """Agar OS se Chrome khola hai to usi ko control karo"""
        try:
            self.play = sync_playwright().start()
            self.browser = self.play.chromium.connect_over_cdp(f"http://localhost:{debug_port}")
            self.page = self.browser.contexts[0].pages[0] if self.browser.contexts[0].pages else self.browser.new_page()
            print("✅ Attached to existing Chrome successfully!")
            return True
        except:
            return False

    # ────────────────────────────────────────────────
    # UPDATED: open_url (reuse browser)
    # ────────────────────────────────────────────────
    def open_url(self, url: str):
        if not self.browser:
            # Pehli baar launch
            self.play = sync_playwright().start()
            self.browser = self.play.chromium.launch(headless=False, args=["--start-maximized"])
            self.page = self.browser.new_page()
        self.page.goto(url, wait_until="networkidle", timeout=30000)
        time.sleep(2)
        return f"✅ Site khol diya: {url}"

    # ────────────────────────────────────────────────
    # NEW: Natural click (sabse important)
    # ────────────────────────────────────────────────
    def click_element(self, text: str):
        if not self.page:
            return "Browser not started"

        text = text.strip().lower()

        # Try multiple smart ways
        selectors = [
            f'text="{text}"',                    # exact text
            f'text=/{text}/i',                   # partial ignore case
            f'[aria-label*="{text}" i]',
            f'[placeholder*="{text}" i]',
            f'button:has-text("{text}")',
            f'a:has-text("{text}")',
            f'[role="button"]:has-text("{text}")'
        ]

        for sel in selectors:
            try:
                locator = self.page.locator(sel)
                if locator.count() > 0:
                    locator.first.click()
                    return f"✅ Clicked on '{text}'"
            except:
                continue

        return f"❌ Could not find '{text}' to click"

    # ────────────────────────────────────────────────
    # IMPROVED: Rich form fields detection
    # ────────────────────────────────────────────────
    def extract_form_fields(self, only_required=False):
        if not self.page:
            return []

        fields = []
        elements = self.page.locator("input, textarea, select, button[type='submit']")

        for i in range(elements.count()):
            el = elements.nth(i)
            name = el.get_attribute("name") or el.get_attribute("id")
            field_type = el.get_attribute("type") or "text"
            placeholder = el.get_attribute("placeholder")
            required = el.get_attribute("required") is not None or el.get_attribute("aria-required") == "true"

            # Label dhundne ki koshish
            label = None
            try:
                label_id = el.get_attribute("id")
                if label_id:
                    label_el = self.page.locator(f'label[for="{label_id}"]')
                    if label_el.count() > 0:
                        label = label_el.first.inner_text().strip()
            except:
                pass

            if not label and placeholder:
                label = placeholder

            field = {
                "name": name,
                "id": el.get_attribute("id"),
                "type": field_type,
                "label": label,
                "placeholder": placeholder,
                "required": required,
                "visible_text": el.inner_text().strip() if el.inner_text() else ""
            }

            if not only_required or required:
                fields.append(field)

        return fields

    # ────────────────────────────────────────────────
    # IMPROVED: Smart single field fill (conversation ke liye best)
    # ────────────────────────────────────────────────
    def fill_single_field(self, field_identifier: str, value: str):
        if not self.page:
            return "Browser not started"

        # Try name, id, placeholder, label
        locators = [
            f'[name="{field_identifier}"]',
            f'[id="{field_identifier}"]',
            f'[placeholder*="{field_identifier}" i]',
            f'label:has-text("{field_identifier}") >> input, textarea, select'
        ]

        for loc in locators:
            try:
                locator = self.page.locator(loc)
                if locator.count() > 0:
                    locator.first.fill(str(value))
                    return f"✅ Filled '{field_identifier}'"
            except:
                continue

        return f"❌ Field '{field_identifier}' not found"

    # Baaki methods same rakh sakte ho (fill_form, submit_form, etc.)
    def fill_form(self, data: dict):
        for key, value in data.items():
            self.fill_single_field(key, value)
        return "Form filled"

    def submit_form(self):
        if not self.page: return "Browser not started"
        try:
            self.page.locator('button[type="submit"]').first.click()
        except:
            self.page.keyboard.press("Enter")
        return "Form submitted"

    def close_browser(self):
        if self.browser:
            self.browser.close()
            self.play.stop()
            self.browser = self.page = self.play = None
        return "Browser closed"
