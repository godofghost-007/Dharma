#!/usr/bin/env python3
"""
Test collaboration API endpoints
"""

import asyncio
import sys
import os
import requests
import json
import time
from subprocess import Popen, PIPE

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

def test_collaboration_api():
    """Test collaboration service API"""
    print("🚀 Testing Collaboration Service API")
    
    # Start the service
    print("Starting collaboration service...")
    service_process = Popen([
        sys.executable, "services/collaboration-service/main.py"
    ], stdout=PIPE, stderr=PIPE)
    
    # Wait for service to start
    time.sleep(3)
    
    base_url = "http://localhost:8005"
    
    try:
        # Test health check
        response = requests.get(f"{base_url}/api/v1/health")
        assert response.status_code == 200
        print("✓ Health check passed")
        
        # Test workspace creation
        workspace_data = {
            "name": "API Test Workspace",
            "description": "Test workspace via API",
            "workspace_type": "investigation",
            "owner_username": "api_user",
            "owner_email": "api@test.com"
        }
        
        response = requests.post(
            f"{base_url}/api/v1/workspaces",
            json=workspace_data,
            params={"user_id": "test_user"}
        )
        assert response.status_code == 200
        workspace_result = response.json()
        workspace_id = workspace_result["workspace_id"]
        print(f"✓ Created workspace: {workspace_id}")
        
        # Test get workspaces
        response = requests.get(
            f"{base_url}/api/v1/workspaces",
            params={"user_id": "test_user"}
        )
        assert response.status_code == 200
        workspaces = response.json()
        assert len(workspaces) > 0
        print(f"✓ Retrieved {len(workspaces)} workspaces")
        
        # Test annotation creation
        annotation_data = {
            "content_id": "test_content_123",
            "workspace_id": workspace_id,
            "annotation_type": "comment",
            "value": "This is a test annotation"
        }
        
        response = requests.post(
            f"{base_url}/api/v1/annotations",
            json=annotation_data,
            params={"user_id": "test_user"}
        )
        assert response.status_code == 200
        annotation_result = response.json()
        print(f"✓ Created annotation: {annotation_result['annotation_id']}")
        
        # Test get annotations
        response = requests.get(
            f"{base_url}/api/v1/annotations/test_content_123",
            params={"user_id": "test_user"}
        )
        assert response.status_code == 200
        annotations = response.json()
        assert len(annotations) > 0
        print(f"✓ Retrieved {len(annotations)} annotations")
        
        # Test case creation
        case_data = {
            "title": "API Test Case",
            "description": "Test case created via API",
            "case_type": "disinformation",
            "priority": "high",
            "workspace_id": workspace_id
        }
        
        response = requests.post(
            f"{base_url}/api/v1/cases",
            json=case_data,
            params={"user_id": "test_user"}
        )
        assert response.status_code == 200
        case_result = response.json()
        print(f"✓ Created case: {case_result['case_id']}")
        
        # Test get cases
        response = requests.get(
            f"{base_url}/api/v1/cases",
            params={"user_id": "test_user"}
        )
        assert response.status_code == 200
        cases = response.json()
        assert len(cases) > 0
        print(f"✓ Retrieved {len(cases)} cases")
        
        # Test document creation
        response = requests.post(
            f"{base_url}/api/v1/documents",
            params={
                "title": "API Test Document",
                "content": "This is a test document created via API",
                "document_type": "guide",
                "user_id": "test_user"
            }
        )
        assert response.status_code == 200
        doc_result = response.json()
        print(f"✓ Created document: {doc_result['document_id']}")
        
        # Test document search
        response = requests.get(
            f"{base_url}/api/v1/documents/search",
            params={"query": "test", "user_id": "test_user"}
        )
        assert response.status_code == 200
        documents = response.json()
        assert len(documents) > 0
        print(f"✓ Found {len(documents)} documents in search")
        
        # Test statistics endpoints
        response = requests.get(f"{base_url}/api/v1/stats/workspaces")
        assert response.status_code == 200
        workspace_stats = response.json()
        print(f"✓ Workspace stats: {workspace_stats['total_workspaces']} workspaces")
        
        response = requests.get(f"{base_url}/api/v1/stats/annotations")
        assert response.status_code == 200
        annotation_stats = response.json()
        print(f"✓ Annotation stats: {annotation_stats['total_annotations']} annotations")
        
        response = requests.get(f"{base_url}/api/v1/stats/cases")
        assert response.status_code == 200
        case_stats = response.json()
        print(f"✓ Case stats: {case_stats['total_cases']} cases")
        
        print("\n🎉 All API tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ API test failed: {e}")
        return False
        
    finally:
        # Stop the service
        service_process.terminate()
        service_process.wait()
        print("Stopped collaboration service")

if __name__ == "__main__":
    success = test_collaboration_api()
    sys.exit(0 if success else 1)