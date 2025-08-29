#!/usr/bin/env python3
"""
Final test script for environment configuration validation
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from shared.config.env_loader import (
    SecureEnvironmentLoader,
    load_and_validate_environment,
    get_credentials_for_platform,
    EnvironmentValidationError
)


def test_environment_validation():
    """Test environment validation functionality"""
    print("🧪 Testing Environment Configuration Validation")
    print("=" * 50)
    
    # Initialize loader
    loader = SecureEnvironmentLoader()
    
    # Test loading environment
    print("\n1. Testing environment loading...")
    if loader.load_environment():
        print("✅ Environment loaded successfully")
    else:
        print("❌ Failed to load environment")
        return False
    
    # Test validation
    print("\n2. Testing validation...")
    if loader.validate_required_variables():
        print("✅ All validations passed")
    else:
        print("❌ Validation failed")
        loader.print_validation_errors()
        return False
    
    # Test individual platform credentials
    print("\n3. Testing platform credentials...")
    
    try:
        # Test Twitter credentials
        twitter_creds = loader.get_twitter_credentials()
        print(f"✅ Twitter credentials loaded:")
        print(f"   - API Key: {twitter_creds.api_key[:10]}...")
        print(f"   - Bearer Token: {twitter_creds.bearer_token[:20]}...")
        
        # Test YouTube credentials  
        youtube_creds = loader.get_youtube_credentials()
        print(f"✅ YouTube credentials loaded:")
        print(f"   - API Key: {youtube_creds.api_key[:10]}...")
        
        # Test Telegram credentials
        telegram_creds = loader.get_telegram_credentials()
        print(f"✅ Telegram credentials loaded:")
        print(f"   - Bot Token: {telegram_creds.bot_token[:10]}...")
        
    except EnvironmentValidationError as e:
        print(f"❌ Credential validation failed: {e}")
        return False
    
    # Test convenience functions
    print("\n4. Testing convenience functions...")
    
    try:
        twitter_creds = get_credentials_for_platform('twitter')
        print("✅ Twitter credentials via convenience function")
        
        youtube_creds = get_credentials_for_platform('youtube')
        print("✅ YouTube credentials via convenience function")
        
        telegram_creds = get_credentials_for_platform('telegram')
        print("✅ Telegram credentials via convenience function")
        
    except Exception as e:
        print(f"❌ Convenience function failed: {e}")
        return False
    
    return True


def test_partial_validation():
    """Test partial validation of specific variable groups"""
    print("\n🧪 Testing Partial Validation")
    print("=" * 30)
    
    loader = SecureEnvironmentLoader()
    loader.load_environment()
    
    # Test individual groups
    groups = ['twitter', 'youtube', 'telegram']
    
    for group in groups:
        if loader.validate_required_variables([group]):
            print(f"✅ {group.capitalize()} validation passed")
        else:
            print(f"❌ {group.capitalize()} validation failed")
            return False
    
    return True


def test_convenience_function():
    """Test the convenience function"""
    print("\n🧪 Testing Convenience Function")
    print("=" * 30)
    
    if load_and_validate_environment():
        print("✅ Convenience function load_and_validate_environment() passed")
        return True
    else:
        print("❌ Convenience function failed")
        return False


if __name__ == "__main__":
    print("🚀 Starting Environment Configuration Tests")
    print("=" * 60)
    
    success = True
    
    # Run all tests
    success &= test_environment_validation()
    success &= test_partial_validation()
    success &= test_convenience_function()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 All tests passed! Environment configuration is working correctly.")
        print("\n📋 Summary:")
        print("✅ Centralized environment configuration file created")
        print("✅ Secure environment loader implemented with validation")
        print("✅ Environment variable validation with clear error messages")
        print("✅ API credentials properly loaded and validated")
        print("✅ Convenience functions working correctly")
        sys.exit(0)
    else:
        print("💥 Some tests failed! Please check the configuration.")
        sys.exit(1)