#!/usr/bin/env python3
"""
Credential validation startup script for Docker containers
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from shared.config.env_loader import SecureEnvironmentLoader, EnvironmentValidationError
except ImportError:
    print("ERROR: Failed to import environment loader")
    sys.exit(1)


def validate_api_credentials():
    """Validate API credentials on container startup"""
    print("Validating API credentials...")
    
    loader = SecureEnvironmentLoader()
    
    # Load environment
    if not loader.load_environment():
        print("ERROR: Failed to load environment configuration")
        return False
    
    # Check if we're in a service that needs API credentials
    service_name = os.getenv('SERVICE_NAME', 'unknown')
    
    if service_name == 'data-collection-service':
        # Data collection service needs all API credentials
        required_groups = ['twitter', 'youtube', 'telegram']
    elif service_name == 'ai-analysis-service':
        # AI analysis service might need some credentials for processing
        required_groups = []  # No direct API access needed
    else:
        # Other services don't need API credentials
        required_groups = []
    
    if not required_groups:
        print("SUCCESS: No API credentials required for this service")
        return True
    
    # Validate required credentials
    if not loader.validate_required_variables(required_groups):
        print("ERROR: API credential validation failed:")
        loader.print_validation_errors()
        return False
    
    # Test credential access
    try:
        if 'twitter' in required_groups:
            twitter_creds = loader.get_twitter_credentials()
            print(f"SUCCESS: Twitter credentials validated (API Key: {twitter_creds.api_key[:10]}...)")
        
        if 'youtube' in required_groups:
            youtube_creds = loader.get_youtube_credentials()
            print(f"SUCCESS: YouTube credentials validated (API Key: {youtube_creds.api_key[:10]}...)")
        
        if 'telegram' in required_groups:
            telegram_creds = loader.get_telegram_credentials()
            print(f"SUCCESS: Telegram credentials validated (Bot Token: {telegram_creds.bot_token[:10]}...)")
        
    except EnvironmentValidationError as e:
        print(f"ERROR: Credential access failed: {e}")
        return False
    
    print("SUCCESS: All API credentials validated successfully")
    return True


def validate_docker_secrets():
    """Validate Docker secrets if they exist"""
    print("Checking for Docker secrets...")
    
    use_docker_secrets = os.getenv('USE_DOCKER_SECRETS', 'false').lower() == 'true'
    secrets_dir = Path('/run/secrets')
    
    if not use_docker_secrets:
        print("INFO: Docker secrets disabled, using environment variables")
        return True
    
    if not secrets_dir.exists():
        print("WARNING: Docker secrets enabled but /run/secrets directory not found")
        print("INFO: Falling back to environment variables")
        return True
    
    # Check for expected secret files based on service
    service_name = os.getenv('SERVICE_NAME', 'unknown')
    
    if service_name == 'data-collection-service':
        expected_secrets = [
            'twitter_api_key',
            'twitter_api_secret', 
            'twitter_bearer_token',
            'twitter_access_token',
            'twitter_access_token_secret',
            'youtube_api_key',
            'telegram_bot_token'
        ]
    elif service_name in ['api-gateway-service', 'ai-analysis-service', 'dashboard-service']:
        expected_secrets = [
            'jwt_secret_key',
            'encryption_key'
        ]
    else:
        expected_secrets = []
    
    if not expected_secrets:
        print(f"INFO: No secrets required for service: {service_name}")
        return True
    
    found_secrets = []
    missing_secrets = []
    
    for secret_name in expected_secrets:
        secret_file = secrets_dir / secret_name
        if secret_file.exists():
            found_secrets.append(secret_name)
            # Load secret into environment variable
            try:
                with open(secret_file, 'r') as f:
                    secret_value = f.read().strip()
                    env_var_name = secret_name.upper()
                    os.environ[env_var_name] = secret_value
                print(f"SUCCESS: Loaded secret: {secret_name}")
            except Exception as e:
                print(f"ERROR: Failed to load secret {secret_name}: {e}")
                return False
        else:
            missing_secrets.append(secret_name)
    
    if found_secrets:
        print(f"SUCCESS: Loaded {len(found_secrets)} Docker secrets")
    
    if missing_secrets:
        print(f"WARNING: Missing secrets: {', '.join(missing_secrets)}")
        print("INFO: Falling back to environment variables for missing secrets")
    
    return True


def main():
    """Main validation function"""
    print("Starting credential validation...")
    print("=" * 50)
    
    success = True
    
    # Validate Docker secrets first
    success &= validate_docker_secrets()
    
    # Validate API credentials
    success &= validate_api_credentials()
    
    print("=" * 50)
    if success:
        print("SUCCESS: Credential validation completed successfully")
        return 0
    else:
        print("ERROR: Credential validation failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())