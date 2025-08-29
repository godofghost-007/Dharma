"""Test authentication system for API Gateway."""

import asyncio
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import json

# Import the main app
from main import app
from app.core.security import security_manager
from app.core.database import db_manager, UserRepository

# Create test client
client = TestClient(app)


class TestAuthentication:
    """Test authentication functionality."""
    
    def setup_method(self):
        """Setup test method."""
        self.test_user_data = {
            "id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "hashed_password": security_manager.get_password_hash("testpass123"),
            "role": "analyst",
            "full_name": "Test User",
            "department": "Testing",
            "is_active": True,
            "permissions": ["alerts:read", "campaigns:read"]
        }
    
    @patch('app.core.database.db_manager.initialize')
    @patch('app.core.database.UserRepository.get_user_by_username')
    @patch('app.core.database.UserRepository.get_user_permissions')
    @patch('app.core.database.UserRepository.update_last_login')
    def test_login_success(self, mock_update_login, mock_get_permissions, 
                          mock_get_user, mock_db_init):
        """Test successful login."""
        # Mock database responses
        mock_get_user.return_value = self.test_user_data
        mock_get_permissions.return_value = ["alerts:read", "campaigns:read"]
        mock_update_login.return_value = None
        
        # Test login
        response = client.post("/auth/login", json={
            "username": "testuser",
            "password": "testpass123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == "testuser"
        assert data["user"]["role"] == "analyst"
    
    @patch('app.core.database.db_manager.initialize')
    @patch('app.core.database.UserRepository.get_user_by_username')
    def test_login_invalid_credentials(self, mock_get_user, mock_db_init):
        """Test login with invalid credentials."""
        mock_get_user.return_value = None
        
        response = client.post("/auth/login", json={
            "username": "testuser",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]
    
    def test_password_hashing(self):
        """Test password hashing functionality."""
        password = "testpassword123"
        hashed = security_manager.get_password_hash(password)
        
        assert hashed != password
        assert security_manager.verify_password(password, hashed)
        assert not security_manager.verify_password("wrongpassword", hashed)
    
    def test_jwt_token_creation_and_verification(self):
        """Test JWT token creation and verification."""
        user_data = {
            "sub": "testuser",
            "user_id": 1,
            "role": "analyst",
            "permissions": ["alerts:read"]
        }
        
        # Create access token
        access_token = security_manager.create_access_token(user_data)
        assert access_token is not None
        
        # Verify token
        token_data = security_manager.verify_token(access_token, "access")
        assert token_data.username == "testuser"
        assert token_data.user_id == 1
        assert token_data.role == "analyst"
        assert token_data.permissions == ["alerts:read"]
        
        # Create refresh token
        refresh_token = security_manager.create_refresh_token(user_data)
        assert refresh_token is not None
        
        # Verify refresh token
        refresh_data = security_manager.verify_token(refresh_token, "refresh")
        assert refresh_data.username == "testuser"
    
    @patch('app.core.database.db_manager.initialize')
    def test_health_check(self, mock_db_init):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "api-gateway"
    
    @patch('app.core.database.db_manager.initialize')
    @patch('app.core.database.UserRepository.get_user_by_id')
    @patch('app.core.database.UserRepository.get_user_permissions')
    def test_get_current_user(self, mock_get_permissions, mock_get_user, mock_db_init):
        """Test getting current user info."""
        # Create a valid token
        user_data = {
            "sub": "testuser",
            "user_id": 1,
            "role": "analyst",
            "permissions": ["alerts:read"]
        }
        token = security_manager.create_access_token(user_data)
        
        # Mock database responses
        mock_get_user.return_value = self.test_user_data
        mock_get_permissions.return_value = ["alerts:read", "campaigns:read"]
        
        # Test endpoint
        response = client.get("/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["role"] == "analyst"
    
    @patch('app.core.database.db_manager.initialize')
    def test_unauthorized_access(self, mock_db_init):
        """Test unauthorized access to protected endpoint."""
        response = client.get("/auth/me")
        assert response.status_code == 403  # No authorization header
        
        # Test with invalid token
        response = client.get("/auth/me", headers={
            "Authorization": "Bearer invalid_token"
        })
        assert response.status_code == 401


def test_security_manager_initialization():
    """Test security manager initialization."""
    assert security_manager.pwd_context is not None
    assert security_manager.secret_key is not None
    assert security_manager.algorithm == "HS256"
    assert security_manager.access_token_expire_minutes > 0


def test_token_data_model():
    """Test token data model."""
    from app.core.security import TokenData
    
    token_data = TokenData(
        username="testuser",
        user_id=1,
        role="analyst",
        permissions=["alerts:read"]
    )
    
    assert token_data.username == "testuser"
    assert token_data.user_id == 1
    assert token_data.role == "analyst"
    assert token_data.permissions == ["alerts:read"]


if __name__ == "__main__":
    # Run basic tests
    print("Testing password hashing...")
    test_security_manager_initialization()
    
    print("Testing JWT tokens...")
    test = TestAuthentication()
    test.setup_method()
    test.test_jwt_token_creation_and_verification()
    
    print("Testing token data model...")
    test_token_data_model()
    
    print("All basic tests passed!")
    
    # Run with pytest for full test suite
    print("\nRun 'pytest test_authentication.py -v' for full test suite")