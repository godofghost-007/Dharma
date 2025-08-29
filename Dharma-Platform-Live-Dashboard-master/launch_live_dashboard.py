#!/usr/bin/env python3
"""
Launch Live Anti-Nationalist Dashboard
"""

import subprocess
import sys
import webbrowser
import time
from pathlib import Path

def main():
    """Launch the live anti-nationalist dashboard"""
    print("🛡️ Launching Dharma Platform - Live Anti-Nationalist Dashboard")
    print("=" * 60)
    
    # Check if streamlit is installed
    try:
        import streamlit
        print("✅ Streamlit found")
    except ImportError:
        print("❌ Streamlit not found. Installing...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'streamlit'])
    
    # Check dashboard file
    dashboard_file = Path(__file__).parent / "live_anti_nationalist_dashboard.py"
    if not dashboard_file.exists():
        print("❌ Dashboard file not found!")
        return
    
    print("✅ Dashboard file found")
    
    try:
        print("🚀 Starting dashboard server...")
        
        # Start Streamlit dashboard
        process = subprocess.Popen([
            sys.executable, '-m', 'streamlit', 'run', 
            str(dashboard_file),
            '--server.port', '8503',
            '--server.headless', 'true',
            '--browser.gatherUsageStats', 'false'
        ])
        
        print("✅ Dashboard started on http://localhost:8503")
        print("🌐 Opening in browser...")
        
        # Wait a moment then open browser
        time.sleep(3)
        webbrowser.open('http://localhost:8503')
        
        print("\n🛡️ Live Anti-Nationalist Dashboard is running!")
        print("📊 Features available:")
        print("   • Real-time YouTube search")
        print("   • Anti-nationalist content detection")
        print("   • Threat level analysis")
        print("   • Clickable video links")
        print("\n⏳ Dashboard running... Press Ctrl+C to stop")
        
        # Wait for user to stop
        try:
            process.wait()
        except KeyboardInterrupt:
            print("\n⏹️  Stopping dashboard...")
            process.terminate()
            process.wait()
            print("✅ Dashboard stopped")
            
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")

if __name__ == "__main__":
    main()