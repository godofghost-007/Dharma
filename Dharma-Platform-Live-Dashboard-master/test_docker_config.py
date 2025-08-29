#!/usr/bin/env python3
"""
Test script for Docker configuration with environment files
"""
import os
import sys
import subprocess
from pathlib import Path


def test_docker_compose_validation():
    """Test Docker Compose configuration validation"""
    print("🧪 Testing Docker Compose Configuration")
    print("=" * 40)
    
    # Test docker-compose.yml validation
    print("\n1. Validating docker-compose.yml...")
    try:
        result = subprocess.run(
            ["docker-compose", "config"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ docker-compose.yml is valid")
        else:
            print(f"❌ docker-compose.yml validation failed: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("⚠️  docker-compose not found, skipping validation")
    except Exception as e:
        print(f"❌ Error validating docker-compose.yml: {e}")
        return False
    
    # Test production configuration
    print("\n2. Validating production configuration...")
    try:
        result = subprocess.run(
            ["docker-compose", "-f", "docker-compose.yml", "-f", "docker-compose.prod.yml", "config"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ Production configuration is valid")
        else:
            print(f"❌ Production configuration validation failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error validating production configuration: {e}")
        return False
    
    # Test secrets configuration
    print("\n3. Validating secrets configuration...")
    try:
        result = subprocess.run(
            ["docker-compose", "-f", "docker-compose.yml", "-f", "docker-compose.secrets.yml", "config"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ Secrets configuration is valid")
        else:
            print(f"❌ Secrets configuration validation failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error validating secrets configuration: {e}")
        return False
    
    return True


def test_environment_file_integration():
    """Test environment file integration"""
    print("\n🧪 Testing Environment File Integration")
    print("=" * 40)
    
    # Check if .env file exists
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found")
        return False
    
    print("✅ .env file found")
    
    # Check if required API credentials are in .env file
    required_vars = [
        'TWITTER_API_KEY',
        'TWITTER_API_SECRET',
        'TWITTER_BEARER_TOKEN',
        'TWITTER_ACCESS_TOKEN',
        'TWITTER_ACCESS_TOKEN_SECRET',
        'YOUTUBE_API_KEY',
        'TELEGRAM_BOT_TOKEN',
        'JWT_SECRET_KEY',
        'ENCRYPTION_KEY'
    ]
    
    missing_vars = []
    
    with open(env_file, 'r') as f:
        env_content = f.read()
    
    for var in required_vars:
        if f"{var}=" not in env_content:
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing variables in .env file: {', '.join(missing_vars)}")
        return False
    
    print("✅ All required variables found in .env file")
    return True


def test_credential_validation_script():
    """Test credential validation script"""
    print("\n🧪 Testing Credential Validation Script")
    print("=" * 40)
    
    # Check if validation script exists
    script_path = Path("scripts/validate_credentials.py")
    if not script_path.exists():
        print("❌ Credential validation script not found")
        return False
    
    print("✅ Credential validation script found")
    
    # Test the script
    try:
        result = subprocess.run(
            [sys.executable, "scripts/validate_credentials.py"],
            capture_output=True,
            text=True,
            env={**os.environ, "SERVICE_NAME": "data-collection-service"}
        )
        
        if result.returncode == 0:
            print("✅ Credential validation script executed successfully")
            print("Script output:")
            print(result.stdout)
        else:
            print(f"❌ Credential validation script failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error running credential validation script: {e}")
        return False
    
    return True


def test_docker_secrets_setup():
    """Test Docker secrets setup script"""
    print("\n🧪 Testing Docker Secrets Setup")
    print("=" * 30)
    
    # Check if setup script exists
    script_path = Path("scripts/setup_docker_secrets.sh")
    if not script_path.exists():
        print("❌ Docker secrets setup script not found")
        return False
    
    print("✅ Docker secrets setup script found")
    
    # Check script content for required functionality
    with open(script_path, 'r') as f:
        script_content = f.read()
    
    required_functions = [
        'create_secret_from_env',
        'docker secret create',
        'TWITTER_API_KEY',
        'YOUTUBE_API_KEY',
        'TELEGRAM_BOT_TOKEN'
    ]
    
    missing_functions = []
    for func in required_functions:
        if func not in script_content:
            missing_functions.append(func)
    
    if missing_functions:
        print(f"❌ Missing functionality in setup script: {', '.join(missing_functions)}")
        return False
    
    print("✅ Docker secrets setup script contains required functionality")
    return True


def main():
    """Main test function"""
    print("🚀 Starting Docker Configuration Tests")
    print("=" * 60)
    
    success = True
    
    # Run all tests
    success &= test_environment_file_integration()
    success &= test_credential_validation_script()
    success &= test_docker_secrets_setup()
    success &= test_docker_compose_validation()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 All Docker configuration tests passed!")
        print("\n📋 Summary:")
        print("✅ Docker Compose files are valid")
        print("✅ Environment file integration working")
        print("✅ Credential validation script functional")
        print("✅ Docker secrets setup script ready")
        print("✅ Production deployment configuration ready")
        
        print("\n🚀 Deployment Commands:")
        print("Development: docker-compose up -d")
        print("Production:  docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d")
        print("With Secrets: docker stack deploy -c docker-compose.yml -c docker-compose.secrets.yml dharma")
        
        return 0
    else:
        print("💥 Some Docker configuration tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())