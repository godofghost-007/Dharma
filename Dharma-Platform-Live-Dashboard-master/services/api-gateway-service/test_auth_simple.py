"""Simple authentication tests without database dependency."""

import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.core.security import security_manager, Token, TokenData
from app.auth.models import LoginRequest, UserInfo, CurrentUser


def test_password_hashing():
    """Test password hashing and verification."""
    print("Testing password hashing...")
    
    password = "TestPassword123!"
    hashed = security_manager.get_password_hash(password)
    
    print(f"Original password: {password}")
    print(f"Hashed password: {hashed[:50]}...")
    
    # Verify correct password
    assert security_manager.verify_password(password, hashed), "Password verification failed"
    print("✓ Correct password verified successfully")
    
    # Verify incorrect password
    assert not security_manager.verify_password("WrongPassword", hashed), "Wrong password should not verify"
    print("✓ Incorrect password correctly rejected")
    
    print("Password hashing tests passed!\n")


def test_jwt_tokens():
    """Test JWT token creation and verification."""
    print("Testing JWT tokens...")
    
    user_data = {
        "sub": "testuser",
        "user_id": 123,
        "role": "analyst",
        "permissions": ["alerts:read", "campaigns:read"]
    }
    
    # Test access token
    access_token = security_manager.create_access_token(user_data)
    print(f"Access token created: {access_token[:50]}...")
    
    # Verify access token
    token_data = security_manager.verify_token(access_token, "access")
    assert token_data.username == "testuser", "Username mismatch"
    assert token_data.user_id == 123, "User ID mismatch"
    assert token_data.role == "analyst", "Role mismatch"
    assert token_data.permissions == ["alerts:read", "campaigns:read"], "Permissions mismatch"
    print("✓ Access token verified successfully")
    
    # Test refresh token
    refresh_token = security_manager.create_refresh_token(user_data)
    print(f"Refresh token created: {refresh_token[:50]}...")
    
    # Verify refresh token
    refresh_data = security_manager.verify_token(refresh_token, "refresh")
    assert refresh_data.username == "testuser", "Refresh token username mismatch"
    print("✓ Refresh token verified successfully")
    
    # Test token pair creation
    token_pair = security_manager.create_token_pair(user_data)
    assert isinstance(token_pair, Token), "Token pair should be Token instance"
    assert token_pair.token_type == "bearer", "Token type should be bearer"
    assert token_pair.expires_in > 0, "Expires in should be positive"
    print("✓ Token pair created successfully")
    
    print("JWT token tests passed!\n")


def test_models():
    """Test Pydantic models."""
    print("Testing Pydantic models...")
    
    # Test LoginRequest
    login_req = LoginRequest(username="testuser", password="password123")
    assert login_req.username == "testuser"
    assert login_req.password == "password123"
    print("✓ LoginRequest model works")
    
    # Test UserInfo
    user_info = UserInfo(
        id=1,
        username="testuser",
        email="test@example.com",
        role="analyst",
        full_name="Test User",
        permissions=["alerts:read"]
    )
    assert user_info.id == 1
    assert user_info.role == "analyst"
    assert "alerts:read" in user_info.permissions
    print("✓ UserInfo model works")
    
    # Test CurrentUser
    current_user = CurrentUser(
        id=1,
        username="testuser",
        email="test@example.com",
        role="analyst",
        permissions=["alerts:read", "campaigns:read"]
    )
    assert current_user.id == 1
    assert len(current_user.permissions) == 2
    print("✓ CurrentUser model works")
    
    print("Model tests passed!\n")


def test_configuration():
    """Test configuration loading."""
    print("Testing configuration...")
    
    from app.core.config import settings
    
    assert settings.app_name is not None, "App name should be set"
    assert settings.version is not None, "Version should be set"
    assert settings.security_secret_key is not None, "Secret key should be set"
    assert settings.security_algorithm == "HS256", "Algorithm should be HS256"
    
    print(f"App name: {settings.app_name}")
    print(f"Version: {settings.version}")
    print(f"Algorithm: {settings.security_algorithm}")
    print("✓ Configuration loaded successfully")
    
    print("Configuration tests passed!\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("API Gateway Authentication System Tests")
    print("=" * 60)
    print()
    
    try:
        test_configuration()
        test_password_hashing()
        test_jwt_tokens()
        test_models()
        
        print("=" * 60)
        print("🎉 ALL TESTS PASSED! 🎉")
        print("=" * 60)
        print()
        print("The authentication system is working correctly!")
        print("Key features verified:")
        print("  ✓ Password hashing with bcrypt")
        print("  ✓ JWT token creation and verification")
        print("  ✓ Access and refresh tokens")
        print("  ✓ Pydantic model validation")
        print("  ✓ Configuration loading")
        
        return True
        
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)