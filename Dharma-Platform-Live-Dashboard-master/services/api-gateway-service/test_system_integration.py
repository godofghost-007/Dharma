"""Comprehensive system integration test for API Gateway."""

import sys
import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.core.config import settings
from app.core.security import security_manager
from app.auth.models import CurrentUser
from app.rbac.models import Role, Permission
from main import app


class SystemIntegrationTest:
    """Comprehensive system integration test suite."""
    
    def __init__(self):
        self.client = TestClient(app)
        self.test_users = self._create_test_users()
        self.test_tokens = {}
    
    def _create_test_users(self):
        """Create test users for different roles."""
        return {
            "admin": {
                "id": 1,
                "username": "admin_user",
                "email": "admin@dharma.local",
                "hashed_password": security_manager.get_password_hash("admin123"),
                "role": "admin",
                "permissions": [],
                "is_active": True
            },
            "analyst": {
                "id": 2,
                "username": "analyst_user", 
                "email": "analyst@dharma.local",
                "hashed_password": security_manager.get_password_hash("analyst123"),
                "role": "analyst",
                "permissions": ["alerts:read", "campaigns:read", "analytics:read"],
                "is_active": True
            },
            "viewer": {
                "id": 3,
                "username": "viewer_user",
                "email": "viewer@dharma.local", 
                "hashed_password": security_manager.get_password_hash("viewer123"),
                "role": "viewer",
                "permissions": ["alerts:read", "campaigns:read"],
                "is_active": True
            }
        }
    
    def _create_test_token(self, user_role: str) -> str:
        """Create JWT token for test user."""
        user = self.test_users[user_role]
        token_data = {
            "sub": user["username"],
            "user_id": user["id"],
            "role": user["role"],
            "permissions": user["permissions"]
        }
        return security_manager.create_access_token(token_data)