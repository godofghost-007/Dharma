#!/usr/bin/env python3
"""
Simple script to check which Project Dharma services are accessible
"""

import requests
import time
from urllib.parse import urljoin

def check_service(name, url, timeout=5):
    """Check if a service is accessible"""
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            return f"✅ {name}: {url} - OK"
        else:
            return f"⚠️  {name}: {url} - HTTP {response.status_code}"
    except requests.exceptions.RequestException as e:
        return f"❌ {name}: {url} - {str(e)}"

def main():
    """Check all services"""
    print("🔍 Checking Project Dharma Services...")
    print("=" * 50)
    
    services = [
        ("Dashboard", "http://localhost:8501"),
        ("API Gateway", "http://localhost:8080"),
        ("Data Collection", "http://localhost:8000"),
        ("AI Analysis", "http://localhost:8001"),
        ("Event Bus", "http://localhost:8005"),
        ("Stream Processing", "http://localhost:8002"),
        ("Grafana", "http://localhost:3000"),
        ("Prometheus", "http://localhost:9090"),
        ("Temporal UI", "http://localhost:8088"),
        ("MongoDB", "http://localhost:27017"),
        ("PostgreSQL", "http://localhost:5432"),
        ("Redis", "http://localhost:6379"),
        ("Elasticsearch", "http://localhost:9200"),
    ]
    
    results = []
    for name, url in services:
        result = check_service(name, url)
        results.append(result)
        print(result)
    
    print("\n" + "=" * 50)
    
    # Count successful services
    successful = len([r for r in results if r.startswith("✅")])
    total = len(results)
    
    print(f"📊 Summary: {successful}/{total} services accessible")
    
    if successful >= total * 0.7:  # 70% success rate
        print("🎉 Project Dharma is mostly operational!")
        print("\n🌐 Main Access Points:")
        print("   Dashboard: http://localhost:8501")
        print("   API Gateway: http://localhost:8080")
        print("   Grafana: http://localhost:3000 (admin/admin)")
        print("   Temporal UI: http://localhost:8088")
    else:
        print("⚠️  Some services may need attention")
        print("   Run 'docker compose logs <service-name>' to check logs")

if __name__ == "__main__":
    main()