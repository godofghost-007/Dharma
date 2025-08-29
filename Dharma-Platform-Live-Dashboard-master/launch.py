#!/usr/bin/env python3
"""
Project Dharma Launch Script
Simple script to launch the complete platform
"""

import os
import sys
import time
import subprocess
import webbrowser
from pathlib import Path


def print_banner():
    """Print Project Dharma banner"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                      PROJECT DHARMA                         ║
    ║              AI-Powered Social Media Intelligence            ║
    ║                                                              ║
    ║  🔍 Real-time Monitoring  🤖 AI Analysis  📊 Visualization  ║
    ║  🚨 Smart Alerting      🔒 Secure        🌐 Multi-platform  ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def check_docker():
    """Check if Docker is available"""
    try:
        result = subprocess.run(['docker', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✓ Docker is available")
            return True
        else:
            print("✗ Docker is not available")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("✗ Docker is not installed or not in PATH")
        return False


def check_docker_compose():
    """Check if Docker Compose is available"""
    try:
        # Try docker compose (newer syntax)
        result = subprocess.run(['docker', 'compose', 'version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✓ Docker Compose is available")
            return 'docker compose'
        
        # Try docker-compose (older syntax)
        result = subprocess.run(['docker-compose', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✓ Docker Compose (legacy) is available")
            return 'docker-compose'
        
        print("✗ Docker Compose is not available")
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("✗ Docker Compose is not installed")
        return None


def launch_platform(compose_cmd):
    """Launch the platform using Docker Compose"""
    print("\n🚀 Launching Project Dharma...")
    print("This may take a few minutes on first run (downloading images)...")
    
    try:
        # Change to project directory
        project_dir = Path(__file__).parent
        os.chdir(project_dir)
        
        # Start services
        cmd = compose_cmd.split() + ['up', '-d']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("✓ Platform launched successfully!")
            return True
        else:
            print(f"✗ Failed to launch platform: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("✗ Launch timed out (this may happen on first run)")
        print("  Try running manually: docker compose up -d")
        return False
    except Exception as e:
        print(f"✗ Error launching platform: {e}")
        return False


def wait_for_services():
    """Wait for services to be ready"""
    print("\n⏳ Waiting for services to start...")
    
    services = [
        ("API Gateway", "http://localhost:8080/health"),
        ("Dashboard", "http://localhost:8501"),
        ("Grafana", "http://localhost:3000")
    ]
    
    import urllib.request
    import urllib.error
    
    for service_name, url in services:
        print(f"  Checking {service_name}...", end="")
        
        for attempt in range(30):  # 30 attempts = 60 seconds max
            try:
                urllib.request.urlopen(url, timeout=2)
                print(" ✓")
                break
            except (urllib.error.URLError, urllib.error.HTTPError):
                time.sleep(2)
                print(".", end="", flush=True)
        else:
            print(" ⚠️ (may still be starting)")


def show_access_info():
    """Show how to access the platform"""
    print("\n" + "="*60)
    print("🎉 PROJECT DHARMA IS READY!")
    print("="*60)
    
    services = [
        ("📊 Main Dashboard", "http://localhost:8501", "Primary user interface"),
        ("🔧 API Gateway", "http://localhost:8080", "REST API endpoints"),
        ("📈 Grafana Monitoring", "http://localhost:3000", "System metrics (admin/admin)"),
        ("⚡ Temporal UI", "http://localhost:8088", "Workflow management"),
        ("🔍 Prometheus", "http://localhost:9090", "Metrics collection")
    ]
    
    for name, url, description in services:
        print(f"{name:20} {url:25} - {description}")
    
    print("\n" + "="*60)
    print("📚 Documentation: ./docs/README.md")
    print("🔧 Configuration: ./docker-compose.yml")
    print("🚨 Logs: docker compose logs -f")
    print("🛑 Stop: docker compose down")
    print("="*60)


def open_dashboard():
    """Open the main dashboard in browser"""
    try:
        dashboard_url = "http://localhost:8501"
        print(f"\n🌐 Opening dashboard in browser: {dashboard_url}")
        webbrowser.open(dashboard_url)
    except Exception as e:
        print(f"Could not open browser: {e}")
        print("Please manually navigate to: http://localhost:8501")


def main():
    """Main launch function"""
    print_banner()
    
    print("🔍 Checking system requirements...")
    
    # Check Docker
    if not check_docker():
        print("\n❌ Docker is required to run Project Dharma")
        print("Please install Docker Desktop from: https://www.docker.com/products/docker-desktop/")
        sys.exit(1)
    
    # Check Docker Compose
    compose_cmd = check_docker_compose()
    if not compose_cmd:
        print("\n❌ Docker Compose is required to run Project Dharma")
        print("Please install Docker Compose or update Docker Desktop")
        sys.exit(1)
    
    print("\n✅ All requirements satisfied!")
    
    # Launch platform
    if launch_platform(compose_cmd):
        wait_for_services()
        show_access_info()
        
        # Ask if user wants to open dashboard
        try:
            response = input("\n🌐 Open dashboard in browser? (y/N): ").strip().lower()
            if response in ['y', 'yes']:
                open_dashboard()
        except KeyboardInterrupt:
            print("\n")
        
        print("\n🎯 Project Dharma is now running!")
        print("   Use 'docker compose logs -f' to view logs")
        print("   Use 'docker compose down' to stop all services")
        
    else:
        print("\n❌ Failed to launch Project Dharma")
        print("   Check Docker is running and try again")
        print("   Or run manually: docker compose up -d")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Launch cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)