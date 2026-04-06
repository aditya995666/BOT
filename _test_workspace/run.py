#!/usr/bin/env python3
"""
Main launcher for JARVIS Humanoid AI System
"""
import subprocess
import sys
import os
from threading import Thread

def start_streamlit():
    """Start Streamlit UI"""
    os.system("streamlit run app.py")

def start_learning_engine():
    """Start background learning engine"""
    from agents.self_improvement_engine import self_improvement_engine
    self_improvement_engine.continuous_learning_loop()

def main():
    print("🚀 Starting JARVIS Humanoid AI System...")
    print("=" * 50)
    
    # Check environment
    if not os.path.exists(".env"):
        print("⚠️  Warning: .env file not found")
        print("Please create .env file with GEMINI_API_KEY")
    
    # Start learning engine in background thread
    learning_thread = Thread(target=start_learning_engine, daemon=True)
    learning_thread.start()
    
    print("✅ Learning engine started in background")
    
    # Start Streamlit
    print("🌐 Starting Web UI...")
    start_streamlit()

if __name__ == "__main__":
    main()