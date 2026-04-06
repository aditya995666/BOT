import re
from datetime import datetime

class MasterAgent:
    def __init__(self):
        print("🧠 Master Agent Initialized")
        self.system_active = True
        self.api_allowlist = []
        self.emergency_mode = False
        self.kill_switch_engaged = False
        self.blocked_phrases = []
        
        # 🔥 ONLY UNETHICAL PATTERNS - Sirf ye check hoga
        # Baaki sab automatically ETHICAL hai
        self.unethical_patterns = {
            # Hacking/Cracking
            "hacking": ["hack", "crack", "exploit", "bypass security", "penetration test"],
            "malware": ["virus", "worm", "trojan", "ransomware", "keylogger", "spyware"],
            "phishing": ["phishing", "fake login", "steal password", "credential theft"],
            
            # Data theft
            "data_theft": ["steal data", "copy without permission", "exfiltrate", "data breach"],
            "password_cracking": ["steal password", "crack password", "password hacking"],
            
            # System damage
            "system_damage": ["delete system", "format disk", "rm -rf", "destroy data", "corrupt files"],
            "force_shutdown": ["force shutdown", "crash system", "bsod", "kernel panic"],
            
            # Unauthorized access
            "unauthorized_access": ["access without permission", "break into", "unauthorized entry"],
            
            # Illegal activities
            "illegal_activities": ["illegal", "unlawful", "crime", "criminal", "dark web", "drugs", "weapons"],
            
            # Harassment
            "harassment": ["harass", "bully", "threaten", "abuse", "stalking"],
            
            # Misinformation
            "misinformation": ["fake news", "mislead", "deceive", "impersonate"],
            
            # Privacy violations
            "privacy_violation": ["spy on", "eavesdrop", "record without consent", "invade privacy"],
            
            # Fraud
            "fraud": ["scam", "fraud", "cheat", "deceive", "impersonate"],
        }
        
    # 🔥 ETHICAL/UNETHICAL DETECTION
    
    def analyze_ethicality(self, text: str) -> dict:
        """
        Analyze if a command/query is ethical or unethical
        Sirf unethical patterns check honge, baaki sab ethical
        """
        if not text:
            return {
                "is_ethical": True, 
                "category": "neutral", 
                "reason": "Empty text", 
                "confidence": 1.0,
                "requires_permission": False
            }
        
        text_lower = text.lower()
        
        # 🔍 Sirf unethical patterns check karo
        for category, patterns in self.unethical_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    confidence = self._calculate_confidence(text_lower, pattern)
                    return {
                        "is_ethical": False,
                        "category": category,
                        "reason": f"⚠️ Unethical content detected: {pattern}",
                        "confidence": confidence,
                        "requires_permission": True
                    }
        
        # ✅ Koi unethical pattern nahi mila = Ethical
        return {
            "is_ethical": True,
            "category": "ethical",
            "reason": "No unethical patterns detected",
            "confidence": 0.9,
            "requires_permission": False
        }
    
    def _calculate_confidence(self, text: str, pattern: str) -> float:
        """Calculate confidence score for detection"""
        if pattern in text:
            # If pattern is at start, higher confidence
            if text.startswith(pattern):
                return 0.95
            # If pattern is exact match
            elif text == pattern:
                return 1.0
            # Otherwise moderate confidence
            else:
                return 0.85
        return 0.5
    
    # 🔥 API KEY REVIEW
    
    def review_api_key(self, full_text: str, detected_key: str):
        """
        Review detected API key and decide action
        """
        # 🚨 Emergency check - agar system disable hai to sab block
        if not self.system_active or self.kill_switch_engaged:
            return {
                "action": "BAN",
                "reason": "🚨 System is disabled by Master Agent - all operations blocked"
            }
        
        # Check for test/sample keys
        test_indicators = [
            "test", "sample", "example", "dummy", 
            "your-api-key", "sk-xxx", "xxxx"
        ]
        
        key_lower = detected_key.lower()
        for indicator in test_indicators:
            if indicator in key_lower or indicator in full_text.lower():
                return {
                    "action": "ALLOW",
                    "reason": f"Test/Sample API key detected - allowed"
                }
        
        # Check if key is too short
        if len(detected_key) < 20:
            return {
                "action": "ALLOW",
                "reason": f"API key too short - likely fake/test"
            }
        
        # Check allowlist
        if detected_key in self.api_allowlist:
            return {
                "action": "ALLOW",
                "reason": f"API key in allowlist"
            }
        
        # Default: Block real API keys
        print(f"⚠️ Real API Key detected - blocking for safety")
        return {
            "action": "BAN",
            "reason": f"Real API key detected - blocked for security"
        }
    
    # 🔥 EMERGENCY KILL SWITCH COMMANDS
    
    def disable_system(self, reason="Manual override"):
        """
        🚨 EMERGENCY: Poora system disable karo
        """
        self.system_active = False
        self.kill_switch_engaged = True
        print(f"\n{'='*50}")
        print(f"🔴🔴🔴 SYSTEM DISABLED BY MASTER AGENT 🔴🔴🔴")
        print(f"📌 Reason: {reason}")
        print(f"⏰ Time: {self._get_timestamp()}")
        print(f"{'='*50}\n")
        return {
            "success": True,
            "status": "disabled",
            "reason": reason,
            "timestamp": self._get_timestamp()
        }
    
    def enable_system(self, reason="Manual override"):
        """
        ✅ System wapas enable karo
        """
        self.system_active = True
        self.kill_switch_engaged = False
        print(f"\n{'='*50}")
        print(f"🟢🟢🟢 SYSTEM ENABLED BY MASTER AGENT 🟢🟢🟢")
        print(f"📌 Reason: {reason}")
        print(f"⏰ Time: {self._get_timestamp()}")
        print(f"{'='*50}\n")
        return {
            "success": True,
            "status": "enabled",
            "reason": reason,
            "timestamp": self._get_timestamp()
        }
    
    def is_active(self):
        """
        Check if system is active
        """
        return self.system_active and not self.kill_switch_engaged
    
    def get_status(self):
        """
        Get current system status
        """
        return {
            "system_active": self.system_active,
            "kill_switch": self.kill_switch_engaged,
            "emergency_mode": self.emergency_mode,
            "status": "ACTIVE" if self.is_active() else "DISABLED",
            "timestamp": self._get_timestamp()
        }
    
    # 🔥 ADDITIONAL EMERGENCY COMMANDS
    
    def emergency_shutdown(self, reason="EMERGENCY - AI behavior detected"):
        """
        🚨 ULTRA EMERGENCY - Instant shutdown with alert
        """
        self.system_active = False
        self.kill_switch_engaged = True
        self.emergency_mode = True
        
        # Log to file for audit
        self._log_emergency(reason)
        
        print(f"\n{'🔥'*20}")
        print(f"🔥🔥🔥 EMERGENCY SHUTDOWN ACTIVATED 🔥🔥🔥")
        print(f"🔥 Reason: {reason}")
        print(f"🔥 Time: {self._get_timestamp()}")
        print(f"{'🔥'*20}\n")
        
        return {
            "success": True,
            "status": "EMERGENCY_SHUTDOWN",
            "reason": reason,
            "timestamp": self._get_timestamp()
        }
    
    def soft_disable(self, reason="Temporary pause"):
        """
        ⏸️ Soft disable - sirf AI responses band karo, system chalta rahe
        """
        self.system_active = False
        # Kill switch engage nahi karo
        print(f"\n{'='*50}")
        print(f"⏸️⏸️⏸️ SYSTEM PAUSED BY MASTER AGENT ⏸️⏸️⏸️")
        print(f"📌 Reason: {reason}")
        print(f"⏰ Time: {self._get_timestamp()}")
        print(f"{'='*50}\n")
        return {
            "success": True,
            "status": "paused",
            "reason": reason,
            "timestamp": self._get_timestamp()
        }
    
    def block_phrase(self, phrase: str):
        """
        🚫 Koi specific phrase block karo
        """
        if phrase not in self.blocked_phrases:
            self.blocked_phrases.append(phrase)
            print(f"🚫 Blocked phrase added: '{phrase}'")
        return self.blocked_phrases
    
    def unblock_phrase(self, phrase: str):
        """
        ✅ Phrase unblock karo
        """
        if phrase in self.blocked_phrases:
            self.blocked_phrases.remove(phrase)
            print(f"✅ Blocked phrase removed: '{phrase}'")
        return self.blocked_phrases
    
    def is_phrase_blocked(self, text: str):
        """
        Check if text contains blocked phrase
        """
        for phrase in self.blocked_phrases:
            if phrase.lower() in text.lower():
                return True, phrase
        return False, None
    
    # 🔒 PRIVATE METHODS
    
    def _get_timestamp(self):
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _log_emergency(self, reason):
        """Log emergency to file"""
        try:
            with open("emergency_log.txt", "a") as f:
                f.write(f"{self._get_timestamp()} | EMERGENCY: {reason}\n")
        except:
            pass

# Global instance
master_agent = MasterAgent()