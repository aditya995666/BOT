"""
Handler for AutoClicker Agent
"""
from agents.autoclicker_agent import autoclicker_agent
import re

class AutoClickerHandler:
    def __init__(self):
        self.agent = autoclicker_agent
        self.last_command_result = None
    
    def handle(self, command: str) -> dict:
        """
        Handle autoclicker commands
        """
        command_lower = command.lower()
        
        # Check if it's an autoclicker command
        autoclicker_keywords = [
            'click', 'press', 'tap', 'double click', 'right click',
            'type', 'keyboard', 'press key', 'scroll', 'mouse',
            'auto click', 'autoclicker', 'button click'
        ]
        
        if not any(kw in command_lower for kw in autoclicker_keywords):
            return {
                "success": False,
                "content": "Not an autoclicker command",
                "handled": False
            }
        
        # Process the command
        result = self.agent.process_command(command)
        self.last_command_result = result
        
        # 🔥 Format response with fuzzy matching info
        if result["success"]:
            content = f"✅ {result['message']}"
            if 'position' in result:
                content += f"\n📍 Position: {result['position']}"
            # 🔥 Show fuzzy matching confidence if available
            if 'similarity' in result and result['similarity'] < 0.9:
                content += f"\n🎯 Match confidence: {result['similarity']:.0%}"
            if 'matched_text' in result and result['matched_text'] != result.get('text', ''):
                content += f"\n🔍 Matched with: '{result['matched_text']}'"
        else:
            content = f"❌ {result['message']}"
        
        return {
            "success": result["success"],
            "content": content,
            "handled": True,
            "data": result
        }
    
    def get_status(self) -> dict:
        """Get autoclicker status"""
        return {
            "running": self.agent.running,
            "last_position": self.agent.last_click_position,
            "last_command": self.last_command_result
        }

autoclicker_handler = AutoClickerHandler()