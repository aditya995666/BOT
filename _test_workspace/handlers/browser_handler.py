class BrowserHandler:
    def __init__(self, browser_agent=None):
        self.browser_agent = browser_agent
        self.form_filling_active = False
        self.waiting_for_response = False
        self.current_question = None

    def handle(self, q: str, extract_url_fn):
        if self.browser_agent is None:
            return {"content": "❌ Browser agent available nahi hai"}

        ql = q.lower().strip()

        # Check for form filling commands
        if any(x in ql for x in ["form bharo", "form fill karo", "fill form", "ye form bhar do"]):
            return self._handle_form_filling_start()
        
        # Handle form filling responses (when waiting for field input)
        if self.form_filling_active and self.waiting_for_response:
            return self._handle_form_response(ql)
        
        # If form filling is active but not waiting, still treat as response
        if self.form_filling_active:
            return self._handle_form_response(ql)
        
        # Check for browser opening commands
        if any(x in ql for x in ["chrome open", "browser khol", "chrome kholo", "google chrome open"]):
            result = self.browser_agent.open_url("https://google.com")
            return {"content": result}
        
        # Extract URL
        url = extract_url_fn(q)
        if url:
            result = self.browser_agent.open_url(url)
            return {"content": result}
        
        # Check for click commands
        if "click" in ql:
            target = q.replace("click", "").strip()
            if target:
                result = self.browser_agent.click_element(target)
                return {"content": result}
            else:
                return {"content": "Click kis cheez pe karun? Target batao"}
        
        # Check for close command
        if any(x in ql for x in ["browser close", "close browser", "band kar do"]):
            result = self.browser_agent.close_browser()
            self.form_filling_active = False
            self.waiting_for_response = False
            return {"content": result}
        
        return {"content": "Browser command samajh nahi aaya 😕"}
    
    def _handle_form_filling_start(self):
        """Start the form filling process"""
        try:
            result = self.browser_agent.start_form_filling()
            
            if not result["success"]:
                self.form_filling_active = False
                return {"content": result["message"]}
            
            self.form_filling_active = True
            
            # Get the first field question
            next_field = result.get("next_field")
            
            if next_field and isinstance(next_field, dict):
                question = next_field.get("question", "Enter value:")
                self.waiting_for_response = True
                self.current_question = question
                return {"content": question}
            elif next_field and isinstance(next_field, str):
                self.waiting_for_response = True
                self.current_question = next_field
                return {"content": next_field}
            else:
                # No fields found - maybe form already filled
                self.form_filling_active = False
                return {"content": result.get("message", "Form filling started but no fields found")}
            
        except Exception as e:
            self.form_filling_active = False
            self.waiting_for_response = False
            return {"content": f"Form filling error: {str(e)}"}
    
    def _handle_form_response(self, user_input):
        """Handle user's response during form filling"""
        try:
            # Call fill_field with user input
            result = self.browser_agent.fill_field(user_input)
            
            if not result["success"]:
                self.form_filling_active = False
                self.waiting_for_response = False
                return {"content": result["message"]}
            
            # Check if form is complete
            if result.get("complete"):
                self.form_filling_active = False
                self.waiting_for_response = False
                return {"content": result.get("message", "Form completed!")}
            
            # Get next field
            next_field = result.get("next_field")
            
            if next_field and isinstance(next_field, dict):
                question = next_field.get("question", "Enter value:")
                self.current_question = question
                return {"content": question}
            elif next_field and isinstance(next_field, str):
                self.current_question = next_field
                return {"content": next_field}
            elif next_field is None:
                # No next field, form completed
                complete_result = self.browser_agent.complete_form()
                self.form_filling_active = False
                self.waiting_for_response = False
                return {"content": complete_result.get("message", "Form completed!")}
            else:
                # Still in progress
                return {"content": "Form filling in progress..."}
            
        except Exception as e:
            self.form_filling_active = False
            self.waiting_for_response = False
            return {"content": f"Form filling error: {str(e)}"}