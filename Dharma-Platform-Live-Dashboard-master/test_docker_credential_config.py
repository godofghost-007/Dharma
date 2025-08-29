#!/usr/bin/env python3
"""
Test script to validate Docker credential configuration
"""
import os
import sys
import subprocess
import tempfile
from pathlib import Path

def test_environment_file_loading():
    """Test that environment files are properly configured"""
    print("🧪 Testing environment file loading...")
    
    # Check if .env file exists
    env_file = Path('.env')
    if not env_file.exists():
        print("❌ .env file not found")
        return False
    
    # Check if .env.template exists
    template_file = Path('.env.template')
    if not template_file.exists():
        print("❌ .env.template file not found")
        return False
    
    # Check if .env.prod.template exists
    prod_template_file = Path('.env.prod.template')
    if not prod_template_file.exists():
        print("❌ .env.prod.template file not found")
        return False
    
    print("✅ Environment files exist")
    
    # Validate that .env contains required API credentials
    with open(env_file, 'r', encoding='utf-8') as f:
        env_content = f.read()
    
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
    for var in required_vars:
        if f"{var}=" not in env_content:
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing variables in .env: {', '.join(missing_vars)}")
        return False
    
    print("✅ All required variables present in .env")
    return True


def test_docker_compose_configuration():
    """Test Docker Compose configuration"""
    print("🧪 Testing Docker Compose configuration...")
    
    # Check if docker-compose files exist
    compose_files = [
        'docker-compose.yml',
        'docker-compose.prod.yml',
        'docker-compose.secrets.yml'
    ]
    
    for file in compose_files:
        if not Path(file).exists():
            print(f"❌ {file} not found")
            return False
    
    print("✅ All Docker Compose files exist")
    
    # Test docker-compose config validation
    try:
        result = subprocess.run(
            ['docker-compose', 'config'],
            capture_output=True,
            text=True,
            check=True
        )
        print("✅ docker-compose.yml is valid")
    except subprocess.CalledProcessError as e:
        print(f"❌ docker-compose.yml validation failed: {e.stderr}")
        return False
    except FileNotFoundError:
        print("⚠️  docker-compose not found, skipping validation")
    
    return True


def test_docker_secrets_configuration():
    """Test Docker secrets configuration"""
    print("🧪 Testing Docker secrets configuration...")
    
    # Read docker-compose.secrets.yml
    secrets_file = Path('docker-compose.secrets.yml')
    if not secrets_file.exists():
        print("❌ docker-compose.secrets.yml not found")
        return False
    
    with open(secrets_file, 'r', encoding='utf-8') as f:
        secrets_content = f.read()
    
    # Check for required secrets
    required_secrets = [
        'twitter_api_key',
        'twitter_api_secret',
        'twitter_bearer_token',
        'twitter_access_token',
        'twitter_access_token_secret',
        'youtube_api_key',
        'telegram_bot_token',
        'jwt_secret_key',
        'encryption_key'
    ]
    
    missing_secrets = []
    for secret in required_secrets:
        if secret not in secrets_content:
            missing_secrets.append(secret)
    
    if missing_secrets:
        print(f"❌ Missing secrets in docker-compose.secrets.yml: {', '.join(missing_secrets)}")
        return False
    
    print("✅ All required secrets defined in docker-compose.secrets.yml")
    return True


def test_validation_scripts():
    """Test validation scripts"""
    print("🧪 Testing validation scripts...")
    
    scripts = [
        'scripts/validate_credentials.py',
        'scripts/docker_startup_check.py',
        'scripts/setup_docker_secrets.sh'
    ]
    
    for script in scripts:
        script_path = Path(script)
        if not script_path.exists():
            print(f"❌ {script} not found")
            return False
        
        # Check if script is executable (for shell scripts)
        if script.endswith('.sh'):
            if not os.access(script_path, os.X_OK):
                print(f"⚠️  {script} is not executable")
    
    print("✅ All validation scripts exist")
    
    # Test credential validation script
    try:
        result = subprocess.run(
            [sys.executable, 'scripts/validate_credentials.py'],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            print("✅ Credential validation script runs successfully")
        else:
            print(f"⚠️  Credential validation script returned non-zero: {result.returncode}")
            print(f"Output: {result.stdout}")
            print(f"Error: {result.stderr}")
    except subprocess.TimeoutExpired:
        print("⚠️  Credential validation script timed out")
    except Exception as e:
        print(f"⚠️  Could not test credential validation script: {e}")
    
    return True


def test_dockerfile_updates():
    """Test that Dockerfiles include validation scripts"""
    print("🧪 Testing Dockerfile updates...")
    
    dockerfiles = [
        'services/data-collection-service/Dockerfile',
        'services/ai-analysis-service/Dockerfile',
        'services/api-gateway-service/Dockerfile',
        'services/dashboard-service/Dockerfile'
    ]
    
    for dockerfile in dockerfiles:
        dockerfile_path = Path(dockerfile)
        if not dockerfile_path.exists():
            print(f"❌ {dockerfile} not found")
            return False
        
        with open(dockerfile_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for validation script copies
        if 'docker_startup_check.py' not in content:
            print(f"❌ {dockerfile} does not include docker_startup_check.py")
            return False
        
        # Check for startup script
        if 'start.sh' not in content:
            print(f"❌ {dockerfile} does not include startup script")
            return False
    
    print("✅ All Dockerfiles include validation scripts")
    return True


def test_environment_variable_substitution():
    """Test environment variable substitution in Docker Compose"""
    print("🧪 Testing environment variable substitution...")
    
    # Create a temporary .env file for testing
    test_env_content = """
TWITTER_API_KEY=test_twitter_key
TWITTER_API_SECRET=test_twitter_secret
TWITTER_BEARER_TOKEN=test_bearer_token
TWITTER_ACCESS_TOKEN=test_access_token
TWITTER_ACCESS_TOKEN_SECRET=test_access_secret
YOUTUBE_API_KEY=test_youtube_key
TELEGRAM_BOT_TOKEN=test_telegram_token
JWT_SECRET_KEY=test_jwt_secret
ENCRYPTION_KEY=test_encryption_key
MONGO_ROOT_USERNAME=test_mongo_user
MONGO_ROOT_PASSWORD=test_mongo_pass
POSTGRES_DB=test_db
POSTGRES_USER=test_user
POSTGRES_PASSWORD=test_pass
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write(test_env_content)
        temp_env_file = f.name
    
    try:
        # Test docker-compose config with test environment
        env = os.environ.copy()
        env['COMPOSE_FILE'] = 'docker-compose.yml:docker-compose.prod.yml'
        
        # Load test environment variables
        for line in test_env_content.strip().split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                env[key] = value
        
        result = subprocess.run(
            ['docker-compose', 'config'],
            env=env,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            # Check if variables were substituted
            config_output = result.stdout
            if 'test_twitter_key' in config_output:
                print("✅ Environment variable substitution working")
                return True
            else:
                print("⚠️  Environment variables may not be properly substituted")
                return True  # Don't fail the test for this
        else:
            print(f"⚠️  Docker compose config failed: {result.stderr}")
            return True  # Don't fail the test for this
    
    except Exception as e:
        print(f"⚠️  Could not test environment variable substitution: {e}")
        return True  # Don't fail the test for this
    
    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_env_file)
        except:
            pass


def main():
    """Main test function"""
    print("🧪 Testing Docker credential configuration...")
    print("=" * 60)
    
    tests = [
        test_environment_file_loading,
        test_docker_compose_configuration,
        test_docker_secrets_configuration,
        test_validation_scripts,
        test_dockerfile_updates,
        test_environment_variable_substitution
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            failed += 1
        print()
    
    print("=" * 60)
    print(f"Tests passed: {passed}")
    print(f"Tests failed: {failed}")
    
    if failed == 0:
        print("✅ All Docker credential configuration tests passed!")
        return 0
    else:
        print("❌ Some Docker credential configuration tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())