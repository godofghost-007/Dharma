"""Unit tests for authentication and authorization components."""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from fastapi import HTTPException
from jose import jwt

# Import authentication components
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../services/api-gateway-service'))

from app.auth.service import AuthenticationService
from app.auth.models import LoginResponse, UserInfo, CurrentUser
from app.core.security import SecurityManager, Token, TokenData
from app.core.database import UserRepository


class TestSecurityManager:
    """Test security manager functionality."""
    
    @pytest.fixture
    def security_manager(self):
        """Create security manager for testing."""
        manager = SecurityManager()
        # Use test settings
        manager.secret_key = "test_secret_key_for_testing_only"
        manager.algorithm = "HS256"
        manager.access_token_expire_minutes = 30
        manager.refresh_token_expire_days = 7
        return manager
    
    def test_password_hashing_and_verification(self, security_manager):
        """Test password hashing and verification."""
        password = "test_password_123"
        
        # Hash password
        hashed = security_manager.get_password_hash(password)
        
        # Verify correct password
        assert security_manager.verify_password(password, hashed) == True
        
        # Verify incorrect password
        assert security_manager.verify_password("wrong_password", hashed) == False
    
    def test_create_access_token(self, security_manager):
        """Test access token creation."""
        user_data = {
            "sub": "testuser",
            "user_id": 1,
            "role": "analyst",
            "permissions": ["read", "write"]
        }
        
        token = security_manager.create_access_token(user_data)
        
        # Verify token is a string
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode and verify token contents
        payload = jwt.decode(token, security_manager.secret_key, algorithms=[security_manager.algorithm])
        assert payload["sub"] == "testuser"
        assert payload["user_id"] == 1
        assert payload["role"] == "analyst"
        assert payload["type"] == "access"
        assert "exp" in payload
    
    def test_create_refresh_token(self, security_manager):
        """Test refresh token creation."""
        user_data = {
            "sub": "testuser",
            "user_id": 1,
            "role": "analyst"
        }
        
        token = security_manager.create_refresh_token(user_data)
        
        # Verify token is a string
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode and verify token contents
        payload = jwt.decode(token, security_manager.secret_key, algorithms=[security_manager.algorithm])
        assert payload["sub"] == "testuser"
        assert payload["user_id"] == 1
        assert payload["type"] == "refresh"
        assert "exp" in payload
    
    def test_verify_access_token(self, security_manager):
        """Test access token verification."""
        user_data = {
            "sub": "testuser",
            "user_id": 1,
            "role": "analyst",
            "permissions": ["read", "write"]
        }
        
        # Create token
        token = security_manager.create_access_token(user_data)
        
        # Verify token
        token_data = security_manager.verify_token(token, "access")
        
        assert isinstance(token_data, TokenData)
        assert token_data.username == "testuser"
        assert token_data.user_id == 1
        assert token_data.role == "analyst"
        assert token_data.permissions == ["read", "write"]
    
    def test_verify_refresh_token(self, security_manager):
        """Test refresh token verification."""
        user_data = {
            "sub": "testuser",
            "user_id": 1,
            "role": "analyst"
        }
        
        # Create token
        token = security_manager.create_refresh_token(user_data)
        
        # Verify token
        token_data = security_manager.verify_token(token, "refresh")
        
        assert isinstance(token_data, TokenData)
        assert token_data.username == "testuser"
        assert token_data.user_id == 1
        assert token_data.role == "analyst"
    
    def test_verify_invalid_token(self, security_manager):
        """Test verification of invalid token."""
        invalid_token = "invalid.token.here"
        
        with pytest.raises(HTTPException) as exc_info:
            security_manager.verify_token(invalid_token, "access")
        
        assert exc_info.value.status_code == 401
    
    def test_verify_wrong_token_type(self, security_manager):
        """Test verification of token with wrong type."""
        user_data = {"sub": "testuser", "user_id": 1}
        
        # Create access token but try to verify as refresh token
        access_token = security_manager.create_access_token(user_data)
        
        with pytest.raises(HTTPException) as exc_info:
            security_manager.verify_token(access_token, "refresh")
        
        assert exc_info.value.status_code == 401
    
    def test_create_token_pair(self, security_manager):
        """Test creating access and refresh token pair."""
        user_data = {
            "sub": "testuser",
            "user_id": 1,
            "role": "analyst",
            "permissions": ["read", "write"]
        }
        
        token_pair = security_manager.create_token_pair(user_data)
        
        assert isinstance(token_pair, Token)
        assert token_pair.token_type == "bearer"
        assert token_pair.expires_in == 30 * 60  # 30 minutes in seconds
        assert len(token_pair.access_token) > 0
        assert len(token_pair.refresh_token) > 0
        
        # Verify both tokens are valid
        access_data = security_manager.verify_token(token_pair.access_token, "access")
        refresh_data = security_manager.verify_token(token_pair.refresh_token, "refresh")
        
        assert access_data.username == "testuser"
        assert refresh_data.username == "testuser"
    
    def test_token_expiration(self, security_manager):
        """Test token expiration handling."""
        user_data = {"sub": "testuser", "user_id": 1}
        
        # Create token with very short expiration
        short_expiration = timedelta(seconds=-1)  # Already expired
        expired_token = security_manager.create_access_token(user_data, short_expiration)
        
        # Should raise exception for expired token
        with pytest.raises(HTTPException) as exc_info:
            security_manager.verify_token(expired_token, "access")
        
        assert exc_info.value.status_code == 401


class TestAuthenticationService:
    """Test authentication service functionality."""
    
    @pytest.fixture
    def mock_user_repo(self):
        """Mock user repository for testing."""
        repo = Mock(spec=UserRepository)
        
        # Mock user data
        test_user = {
            "id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "hashed_password": "$2b$12$test_hash",
            "role": "analyst",
            "full_name": "Test User",
            "department": "Intelligence",
            "is_active": True,
            "last_login": datetime.utcnow()
        }
        
        # Mock async methods
        repo.get_user_by_username = AsyncMock(return_value=test_user)
        repo.get_user_by_id = AsyncMock(return_value=test_user)
        repo.get_user_permissions = AsyncMock(return_value=["read", "write", "analyze"])
        repo.create_user = AsyncMock(return_value=1)
        repo.update_last_login = AsyncMock(return_value=None)
        
        return repo
    
    @pytest.fixture
    def mock_security_manager(self):
        """Mock security manager for testing."""
        manager = Mock(spec=SecurityManager)
        
        # Mock methods
        manager.verify_password.return_value = True
        manager.get_password_hash.return_value = "$2b$12$test_hash"
        manager.create_token_pair.return_value = Token(
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            token_type="bearer",
            expires_in=1800
        )
        manager.verify_token.return_value = TokenData(
            username="testuser",
            user_id=1,
            role="analyst",
            permissions=["read", "write"]
        )
        
        return manager
    
    @pytest.fixture
    def auth_service(self, mock_user_repo, mock_security_manager):
        """Create authentication service with mocked dependencies."""
        service = AuthenticationService()
        service.user_repo = mock_user_repo
        
        # Patch the global security manager
        with patch('app.auth.service.security_manager', mock_security_manager):
            yield service
    
    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, auth_service, mock_user_repo, mock_security_manager):
        """Test successful user authentication."""
        result = await auth_service.authenticate_user("testuser", "correct_password")
        
        assert result is not None
        assert result["username"] == "testuser"
        assert result["email"] == "test@example.com"
        
        # Verify repository and security manager were called
        mock_user_repo.get_user_by_username.assert_called_once_with("testuser")
        mock_security_manager.verify_password.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, auth_service, mock_user_repo):
        """Test authentication with non-existent user."""
        mock_user_repo.get_user_by_username.return_value = None
        
        result = await auth_service.authenticate_user("nonexistent", "password")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, auth_service, mock_security_manager):
        """Test authentication with wrong password."""
        mock_security_manager.verify_password.return_value = False
        
        result = await auth_service.authenticate_user("testuser", "wrong_password")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_login_success(self, auth_service, mock_user_repo, mock_security_manager):
        """Test successful login."""
        with patch('app.auth.service.security_manager', mock_security_manager):
            result = await auth_service.login("testuser", "correct_password")
        
        assert isinstance(result, LoginResponse)
        assert result.access_token == "test_access_token"
        assert result.refresh_token == "test_refresh_token"
        assert result.token_type == "bearer"
        assert result.expires_in == 1800
        
        # Verify user info
        assert result.user.username == "testuser"
        assert result.user.email == "test@example.com"
        assert result.user.role == "analyst"
        assert "read" in result.user.permissions
        
        # Verify last login was updated
        mock_user_repo.update_last_login.assert_called_once_with(1)
    
    @pytest.mark.asyncio
    async def test_login_failure(self, auth_service, mock_user_repo):
        """Test login failure."""
        mock_user_repo.get_user_by_username.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.login("nonexistent", "password")
        
        assert exc_info.value.status_code == 401
        assert "Incorrect username or password" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_refresh_token_success(self, auth_service, mock_user_repo, mock_security_manager):
        """Test successful token refresh."""
        with patch('app.auth.service.security_manager', mock_security_manager):
            result = await auth_service.refresh_token("valid_refresh_token")
        
        assert isinstance(result, LoginResponse)
        assert result.access_token == "test_access_token"
        assert result.refresh_token == "test_refresh_token"
        
        # Verify security manager was called to verify token
        mock_security_manager.verify_token.assert_called_with("valid_refresh_token", "refresh")
    
    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, auth_service, mock_security_manager):
        """Test token refresh with invalid token."""
        mock_security_manager.verify_token.side_effect = HTTPException(
            status_code=401, detail="Invalid token"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.refresh_token("invalid_refresh_token")
        
        assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_current_user(self, auth_service, mock_user_repo, mock_security_manager):
        """Test getting current user from token."""
        with patch('app.auth.service.security_manager', mock_security_manager):
            result = await auth_service.get_current_user("valid_access_token")
        
        assert isinstance(result, CurrentUser)
        assert result.username == "testuser"
        assert result.email == "test@example.com"
        assert result.role == "analyst"
        assert "read" in result.permissions
        
        # Verify token was verified
        mock_security_manager.verify_token.assert_called_with("valid_access_token", "access")
    
    @pytest.mark.asyncio
    async def test_get_current_user_not_found(self, auth_service, mock_user_repo, mock_security_manager):
        """Test getting current user when user not found in database."""
        mock_user_repo.get_user_by_id.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.get_current_user("valid_access_token")
        
        assert exc_info.value.status_code == 401
        assert "User not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_register_user_success(self, auth_service, mock_user_repo, mock_security_manager):
        """Test successful user registration."""
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "SecurePass123",
            "role": "analyst",
            "full_name": "New User",
            "department": "Intelligence"
        }
        
        with patch('app.auth.service.security_manager', mock_security_manager):
            result = await auth_service.register_user(user_data)
        
        assert isinstance(result, UserInfo)
        assert result.username == "newuser"
        assert result.email == "newuser@example.com"
        assert result.role == "analyst"
        
        # Verify password was hashed
        mock_security_manager.get_password_hash.assert_called_once_with("SecurePass123")
        
        # Verify user was created in database
        mock_user_repo.create_user.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_register_user_failure(self, auth_service, mock_user_repo, mock_security_manager):
        """Test user registration failure."""
        mock_user_repo.create_user.side_effect = Exception("Database error")
        
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "SecurePass123",
            "role": "analyst"
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.register_user(user_data)
        
        assert exc_info.value.status_code == 400
        assert "Failed to create user" in str(exc_info.value.detail)


class TestUserRepository:
    """Test user repository functionality."""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Mock database manager for testing."""
        db_manager = Mock()
        
        # Mock database connection
        mock_connection = AsyncMock()
        db_manager.get_connection.return_value.__aenter__.return_value = mock_connection
        
        return db_manager, mock_connection
    
    @pytest.fixture
    def user_repo(self, mock_db_manager):
        """Create user repository with mocked database."""
        db_manager, mock_connection = mock_db_manager
        repo = UserRepository(db_manager)
        return repo, mock_connection
    
    @pytest.mark.asyncio
    async def test_get_user_by_username(self, user_repo):
        """Test getting user by username."""
        repo, mock_connection = user_repo
        
        # Mock database response
        mock_connection.fetchrow.return_value = {
            "id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "hashed_password": "$2b$12$test_hash",
            "role": "analyst",
            "is_active": True
        }
        
        result = await repo.get_user_by_username("testuser")
        
        assert result is not None
        assert result["username"] == "testuser"
        assert result["email"] == "test@example.com"
        
        # Verify SQL query was executed
        mock_connection.fetchrow.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_by_id(self, user_repo):
        """Test getting user by ID."""
        repo, mock_connection = user_repo
        
        # Mock database response
        mock_connection.fetchrow.return_value = {
            "id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "role": "analyst"
        }
        
        result = await repo.get_user_by_id(1)
        
        assert result is not None
        assert result["id"] == 1
        assert result["username"] == "testuser"
    
    @pytest.mark.asyncio
    async def test_get_user_permissions(self, user_repo):
        """Test getting user permissions."""
        repo, mock_connection = user_repo
        
        # Mock database response
        mock_connection.fetch.return_value = [
            {"permission": "read"},
            {"permission": "write"},
            {"permission": "analyze"}
        ]
        
        result = await repo.get_user_permissions(1)
        
        assert result == ["read", "write", "analyze"]
    
    @pytest.mark.asyncio
    async def test_create_user(self, user_repo):
        """Test creating new user."""
        repo, mock_connection = user_repo
        
        # Mock database response
        mock_connection.fetchval.return_value = 1
        
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "hashed_password": "$2b$12$test_hash",
            "role": "analyst",
            "is_active": True
        }
        
        result = await repo.create_user(user_data)
        
        assert result == 1
        
        # Verify INSERT query was executed
        mock_connection.fetchval.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_last_login(self, user_repo):
        """Test updating user's last login timestamp."""
        repo, mock_connection = user_repo
        
        await repo.update_last_login(1)
        
        # Verify UPDATE query was executed
        mock_connection.execute.assert_called_once()


class TestAuthenticationIntegration:
    """Test integration between authentication components."""
    
    @pytest.mark.asyncio
    async def test_complete_authentication_flow(self):
        """Test complete authentication flow from login to API access."""
        # Create real security manager for integration test
        security_manager = SecurityManager()
        security_manager.secret_key = "test_secret_key_for_integration_test"
        
        # Mock user repository
        mock_user_repo = Mock(spec=UserRepository)
        mock_user_repo.get_user_by_username = AsyncMock(return_value={
            "id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "hashed_password": security_manager.get_password_hash("correct_password"),
            "role": "analyst",
            "full_name": "Test User",
            "is_active": True
        })
        mock_user_repo.get_user_by_id = AsyncMock(return_value={
            "id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "role": "analyst",
            "full_name": "Test User"
        })
        mock_user_repo.get_user_permissions = AsyncMock(return_value=["read", "write"])
        mock_user_repo.update_last_login = AsyncMock()
        
        # Create authentication service
        auth_service = AuthenticationService()
        auth_service.user_repo = mock_user_repo
        
        # Patch security manager
        with patch('app.auth.service.security_manager', security_manager):
            # Step 1: Login
            login_response = await auth_service.login("testuser", "correct_password")
            
            assert isinstance(login_response, LoginResponse)
            assert login_response.user.username == "testuser"
            assert len(login_response.access_token) > 0
            assert len(login_response.refresh_token) > 0
            
            # Step 2: Use access token to get current user
            current_user = await auth_service.get_current_user(login_response.access_token)
            
            assert isinstance(current_user, CurrentUser)
            assert current_user.username == "testuser"
            assert current_user.role == "analyst"
            
            # Step 3: Refresh token
            new_login_response = await auth_service.refresh_token(login_response.refresh_token)
            
            assert isinstance(new_login_response, LoginResponse)
            assert new_login_response.user.username == "testuser"
            assert new_login_response.access_token != login_response.access_token  # Should be different
    
    @pytest.mark.asyncio
    async def test_authentication_error_scenarios(self):
        """Test various authentication error scenarios."""
        # Create authentication service with mocked dependencies
        auth_service = AuthenticationService()
        
        # Mock user repository to return None (user not found)
        mock_user_repo = Mock(spec=UserRepository)
        mock_user_repo.get_user_by_username = AsyncMock(return_value=None)
        auth_service.user_repo = mock_user_repo
        
        # Test 1: Login with non-existent user
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.login("nonexistent", "password")
        
        assert exc_info.value.status_code == 401
        
        # Test 2: Invalid token verification
        mock_security_manager = Mock(spec=SecurityManager)
        mock_security_manager.verify_token.side_effect = HTTPException(
            status_code=401, detail="Invalid token"
        )
        
        with patch('app.auth.service.security_manager', mock_security_manager):
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.get_current_user("invalid_token")
            
            assert exc_info.value.status_code == 401
    
    def test_password_security_requirements(self):
        """Test password security requirements."""
        security_manager = SecurityManager()
        
        # Test password hashing produces different hashes for same password
        password = "test_password_123"
        hash1 = security_manager.get_password_hash(password)
        hash2 = security_manager.get_password_hash(password)
        
        # Hashes should be different (due to salt)
        assert hash1 != hash2
        
        # But both should verify correctly
        assert security_manager.verify_password(password, hash1) == True
        assert security_manager.verify_password(password, hash2) == True
        
        # Wrong password should not verify
        assert security_manager.verify_password("wrong_password", hash1) == False