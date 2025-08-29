#!/usr/bin/env python3
"""
Project Dharma - Port Debugging Script
Diagnose and fix port 8080 issues in Codespaces
"""

import subprocess
import socket
import time
import requests
import os
from pathlib import Path


def print_header(title):
    """Print formatted header"""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print(f"{'='*60}")


def check_port_listening(port):
    """Check if a port is listening"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result == 0
    except Exception:
        return False


def check_docker_services():
    """Check Docker services status"""
    print_header("DOCKER SERVICES STATUS")
    
    try:
        # Check if Docker is running
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Docker is available")
            print(f"   Version: {result.stdout.strip()}")
        else:
            print("❌ Docker is not available")
            return False
        
        # Check Docker Compose
        result = subprocess.run(['docker', 'compose', 'version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Docker Compose is available")
        else:
            print("❌ Docker Compose is not available")
        
        # Check running containers
        result = subprocess.run(['docker', 'compose', 'ps'], capture_output=True, text=True)
        if result.returncode == 0:
            print("\n📋 Running Services:")
            print(result.stdout)
        else:
            print("❌ Could not get service status")
        
        return True
        
    except Exception as e:
        print(f"❌ Docker check failed: {e}")
        return False


def check_ports():
    """Check port status"""
    print_header("PORT STATUS CHECK")
    
    ports_to_check = [
        (8080, "API Gateway"),
        (8501, "Dashboard"),
        (3000, "Grafana"),
        (9090, "Prometheus"),
        (8088, "Temporal UI"),
        (5432, "PostgreSQL"),
        (27017, "MongoDB"),
        (6379, "Redis"),
        (9200, "Elasticsearch")
    ]
    
    for port, service in ports_to_check:
        is_listening = check_port_listening(port)
        status = "✅ LISTENING" if is_listening else "❌ NOT LISTENING"
        print(f"Port {port:5d} ({service:15s}): {status}")
        
        if port == 8080 and is_listening:
            # Try to make a request to the API Gateway
            try:
                response = requests.get(f'http://localhost:{port}/health', timeout=5)
                print(f"         Health check: {response.status_code}")
            except Exception as e:
                print(f"         Health check failed: {e}")


def check_api_gateway_logs():
    """Check API Gateway container logs"""
    print_header("API GATEWAY LOGS")
    
    try:
        # Get API Gateway container logs
        result = subprocess.run(['docker', 'compose', 'logs', 'api-gateway-service'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("📋 Recent API Gateway logs:")
            print(result.stdout[-1000:])  # Last 1000 characters
        else:
            print("❌ Could not get API Gateway logs")
            print(result.stderr)
    except Exception as e:
        print(f"❌ Log check failed: {e}")


def start_api_gateway_standalone():
    """Try to start API Gateway standalone"""
    print_header("STARTING API GATEWAY STANDALONE")
    
    try:
        # Change to API Gateway directory
        api_gateway_dir = Path("services/api-gateway-service")
        if not api_gateway_dir.exists():
            print("❌ API Gateway directory not found")
            return False
        
        print("🚀 Starting API Gateway standalone...")
        print("📁 Directory:", api_gateway_dir.absolute())
        
        # Try to start with uvicorn directly
        cmd = [
            'python', '-m', 'uvicorn', 'main:app',
            '--host', '0.0.0.0',
            '--port', '8080',
            '--reload'
        ]
        
        print(f"🔧 Command: {' '.join(cmd)}")
        print("⏱️  Starting in 3 seconds...")
        time.sleep(3)
        
        # Start the process
        process = subprocess.Popen(cmd, cwd=api_gateway_dir)
        
        # Wait a bit and check if it's running
        time.sleep(5)
        
        if check_port_listening(8080):
            print("✅ API Gateway started successfully on port 8080!")
            return True
        else:
            print("❌ API Gateway failed to start on port 8080")
            process.terminate()
            return False
            
    except Exception as e:
        print(f"❌ Failed to start API Gateway: {e}")
        return False


def fix_port_forwarding():
    """Instructions for fixing port forwarding in Codespaces"""
    print_header("PORT FORWARDING FIX")
    
    print("🔧 To fix port forwarding in GitHub Codespaces:")
    print()
    print("1. 📋 Go to the 'PORTS' tab in VS Code")
    print("2. ➕ Click 'Forward a Port'")
    print("3. 🔢 Enter port number: 8080")
    print("4. 🏷️  Set label: 'API Gateway'")
    print("5. 🌐 Set visibility: 'Public' (for demo)")
    print()
    print("Or use the command palette:")
    print("1. 🎯 Press Ctrl+Shift+P (Cmd+Shift+P on Mac)")
    print("2. 🔍 Type: 'Ports: Forward a Port'")
    print("3. 🔢 Enter: 8080")
    print()
    print("Alternative - Manual forwarding:")
    print("1. 🖱️  Right-click on port 8080 in PORTS tab")
    print("2. ⚙️  Select 'Port Visibility' → 'Public'")


def create_simple_api_server():
    """Create a simple API server for testing"""
    print_header("CREATING SIMPLE TEST SERVER")
    
    simple_server_code = '''#!/usr/bin/env python3
"""
Simple API server for testing port 8080
"""
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Project Dharma - Test API", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "Project Dharma API Gateway - Test Server", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "port": 8080}

@app.get("/test")
async def test():
    return {"test": "success", "message": "Port 8080 is working!"}

if __name__ == "__main__":
    print("🚀 Starting test API server on port 8080...")
    uvicorn.run(app, host="0.0.0.0", port=8080)
'''
    
    # Write the simple server
    with open('test_api_server.py', 'w') as f:
        f.write(simple_server_code)
    
    print("✅ Created test_api_server.py")
    print("🚀 To run: python test_api_server.py")
    print("🌐 Then access: http://localhost:8080")


def main():
    """Main diagnostic function"""
    print("🛡️  PROJECT DHARMA - PORT 8080 DIAGNOSTIC")
    print("="*60)
    
    # Check Docker services
    docker_ok = check_docker_services()
    
    # Check ports
    check_ports()
    
    # Check API Gateway logs if Docker is running
    if docker_ok:
        check_api_gateway_logs()
    
    # Provide solutions
    print_header("SOLUTIONS")
    
    print("🔧 Try these solutions in order:")
    print()
    print("1. 🐳 Restart Docker services:")
    print("   docker compose down")
    print("   docker compose up -d")
    print()
    print("2. 🚀 Start API Gateway standalone:")
    print("   cd services/api-gateway-service")
    print("   python -m uvicorn main:app --host 0.0.0.0 --port 8080")
    print()
    print("3. 🧪 Use test server:")
    print("   python test_api_server.py")
    print()
    
    # Create test server
    create_simple_api_server()
    
    # Port forwarding instructions
    fix_port_forwarding()
    
    # Ask user what to do
    print_header("QUICK ACTIONS")
    
    try:
        action = input("\n🎯 Choose action:\n1. Start test server\n2. Try standalone API Gateway\n3. Just show diagnostics\nChoice (1-3): ").strip()
        
        if action == "1":
            print("\n🚀 Starting test server...")
            subprocess.run(['python', 'test_api_server.py'])
        elif action == "2":
            start_api_gateway_standalone()
        else:
            print("\n✅ Diagnostics complete!")
            
    except KeyboardInterrupt:
        print("\n\n👋 Diagnostic cancelled")


if __name__ == "__main__":
    main()