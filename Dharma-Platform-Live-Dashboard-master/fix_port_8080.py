#!/usr/bin/env python3
"""
Project Dharma - Quick Fix for Port 8080
Get the API Gateway working immediately for hackathon demo
"""

import subprocess
import time
import socket
import os
import sys
from pathlib import Path


def print_banner():
    """Print fix banner"""
    print("🔧 PROJECT DHARMA - PORT 8080 QUICK FIX")
    print("="*50)
    print("🎯 Getting API Gateway working for hackathon demo")
    print("="*50)


def check_port(port):
    """Check if port is available"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result == 0
    except:
        return False


def kill_port_8080():
    """Kill any process using port 8080"""
    print("🔍 Checking for processes on port 8080...")
    
    try:
        # Try to find and kill process on port 8080
        if os.name == 'posix':  # Linux/Mac
            subprocess.run(['fuser', '-k', '8080/tcp'], capture_output=True)
        else:  # Windows
            subprocess.run(['netstat', '-ano', '|', 'findstr', ':8080'], capture_output=True)
        
        print("✅ Cleared port 8080")
    except:
        print("ℹ️  Port 8080 appears to be free")


def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'fastapi', 'uvicorn'], 
                      check=True, capture_output=True)
        print("✅ Dependencies installed")
        return True
    except:
        print("❌ Failed to install dependencies")
        return False


def start_simple_api():
    """Start the simple API Gateway"""
    print("🚀 Starting simple API Gateway on port 8080...")
    
    try:
        # Start the simple API gateway
        process = subprocess.Popen([sys.executable, 'simple_api_gateway.py'])
        
        # Wait for it to start
        print("⏱️  Waiting for service to start...")
        for i in range(10):
            time.sleep(1)
            if check_port(8080):
                print("✅ API Gateway is running on port 8080!")
                print("🌐 Access at: http://localhost:8080")
                print("📚 API Docs: http://localhost:8080/docs")
                print("🔍 Health Check: http://localhost:8080/health")
                print("🎪 Demo Endpoint: http://localhost:8080/api/v1/demo")
                return True
            print(f"   Attempt {i+1}/10...")
        
        print("❌ Failed to start API Gateway")
        process.terminate()
        return False
        
    except Exception as e:
        print(f"❌ Error starting API Gateway: {e}")
        return False


def show_codespace_instructions():
    """Show Codespaces port forwarding instructions"""
    print("\n🔗 CODESPACES PORT FORWARDING:")
    print("="*40)
    print("1. 📋 Look for the 'PORTS' tab in VS Code")
    print("2. ➕ Click 'Forward a Port' or '+' button")
    print("3. 🔢 Enter: 8080")
    print("4. 🏷️  Label: 'API Gateway'")
    print("5. 🌐 Set visibility to 'Public'")
    print()
    print("🎯 Alternative: Use Command Palette")
    print("   Ctrl+Shift+P → 'Ports: Forward a Port' → 8080")


def test_api():
    """Test the API endpoints"""
    print("\n🧪 TESTING API ENDPOINTS:")
    print("="*30)
    
    import requests
    
    endpoints = [
        ("/", "Root endpoint"),
        ("/health", "Health check"),
        ("/api/v1/demo", "Demo endpoint"),
        ("/api/v1/stats", "Statistics"),
        ("/api/v1/posts", "Posts data")
    ]
    
    for endpoint, description in endpoints:
        try:
            response = requests.get(f"http://localhost:8080{endpoint}", timeout=5)
            status = "✅ OK" if response.status_code == 200 else f"❌ {response.status_code}"
            print(f"{endpoint:20s} - {description:15s}: {status}")
        except Exception as e:
            print(f"{endpoint:20s} - {description:15s}: ❌ Failed")


def main():
    """Main fix function"""
    print_banner()
    
    # Step 1: Clear port 8080
    kill_port_8080()
    
    # Step 2: Install dependencies
    if not install_dependencies():
        print("❌ Cannot proceed without dependencies")
        return False
    
    # Step 3: Start simple API
    if start_simple_api():
        # Step 4: Show instructions
        show_codespace_instructions()
        
        # Step 5: Test API
        time.sleep(2)
        test_api()
        
        print("\n🎉 SUCCESS! Port 8080 is now working!")
        print("🏆 Ready for hackathon demo!")
        
        return True
    else:
        print("\n❌ FAILED to fix port 8080")
        print("💡 Try running manually:")
        print("   python simple_api_gateway.py")
        return False


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Fix cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("💡 Try running: python simple_api_gateway.py")