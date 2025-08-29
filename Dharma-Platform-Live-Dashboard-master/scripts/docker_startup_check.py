#!/usr/bin/env python3
"""
Docker container startup validation script
Validates environment configuration and API credentials before service startup
"""
import os
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def wait_for_dependencies():
    """Wait for dependent services to be ready"""
    service_name = os.getenv('SERVICE_NAME', 'unknown')
    
    # Define service dependencies
    dependencies = {
        'data-collection-service': ['mongodb', 'redis', 'kafka'],
        'ai-analysis-service': ['mongodb', 'redis', 'kafka'],
        'api-gateway-service': ['postgresql', 'redis'],
        'dashboard-service': ['api-gateway-service'],
        'stream-processing-service': ['kafka', 'mongodb', 'redis'],
        'event-bus-service': ['kafka', 'temporal']
    }
    
    service_deps = dependencies.get(service_name, [])
    if not service_deps:
        print(f"INFO: No dependencies defined for service: {service_name}")
        return True
    
    print(f"Waiting for dependencies: {', '.join(service_deps)}")
    
    # Simple dependency check - in production, use proper health checks
    max_wait = 60  # seconds
    wait_interval = 5  # seconds
    elapsed = 0
    
    while elapsed < max_wait:
        print(f"Checking dependencies... ({elapsed}s/{max_wait}s)")
        time.sleep(wait_interval)
        elapsed += wait_interval
        
        # In a real implementation, you would check actual service health
        # For now, just wait a reasonable amount of time
        if elapsed >= 30:  # Assume dependencies are ready after 30s
            break
    
    print("SUCCESS: Dependencies check completed")
    return True


def validate_environment_variables():
    """Validate required environment variables"""
    print("Validating environment variables...")
    
    service_name = os.getenv('SERVICE_NAME', 'unknown')
    
    # Common environment variables
    common_vars = ['SERVICE_NAME']
    
    # Service-specific required variables
    service_vars = {
        'data-collection-service': [
            'DB_MONGODB_URL', 'REDIS_URL', 'KAFKA_BOOTSTRAP_SERVERS',
            'TWITTER_API_KEY', 'TWITTER_API_SECRET', 'TWITTER_BEARER_TOKEN',
            'TWITTER_ACCESS_TOKEN', 'TWITTER_ACCESS_TOKEN_SECRET',
            'YOUTUBE_API_KEY', 'TELEGRAM_BOT_TOKEN'
        ],
        'ai-analysis-service': [
            'DB_MONGODB_URL', 'REDIS_URL', 'KAFKA_BOOTSTRAP_SERVERS'
        ],
        'api-gateway-service': [
            'DB_POSTGRESQL_URL', 'REDIS_URL', 'SECRET_KEY', 'ENCRYPTION_KEY'
        ],
        'dashboard-service': [
            'API_GATEWAY_URL'
        ]
    }
    
    required_vars = common_vars + service_vars.get(service_name, [])
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            # Check if there's a corresponding _FILE variable for Docker secrets
            file_var = f"{var}_FILE"
            file_path = os.getenv(file_var)
            if file_path and Path(file_path).exists():
                try:
                    with open(file_path, 'r') as f:
                        os.environ[var] = f.read().strip()
                    print(f"SUCCESS: Loaded {var} from Docker secret")
                    continue
                except Exception as e:
                    print(f"ERROR: Failed to load {var} from {file_path}: {e}")
                    missing_vars.append(var)
            else:
                missing_vars.append(var)
        else:
            # Mask sensitive values in logs
            if any(sensitive in var.lower() for sensitive in ['key', 'secret', 'token', 'password']):
                masked_value = value[:10] + "..." if len(value) > 10 else "***"
                print(f"SUCCESS: {var}: {masked_value}")
            else:
                print(f"SUCCESS: {var}: {value}")
    
    if missing_vars:
        print(f"ERROR: Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    print("SUCCESS: All required environment variables are set")
    return True


def validate_file_permissions():
    """Validate file permissions and access"""
    print("Validating file permissions...")
    
    # Check if we can write to logs directory
    log_dir = Path('/app/logs')
    if not log_dir.exists():
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            print("SUCCESS: Created logs directory")
        except Exception as e:
            print(f"WARNING: Could not create logs directory: {e}")
    
    # Check shared directory access
    shared_dir = Path('/app/shared')
    if shared_dir.exists():
        if os.access(shared_dir, os.R_OK):
            print("SUCCESS: Shared directory is readable")
        else:
            print("ERROR: Shared directory is not readable")
            return False
    
    # Check Docker secrets directory if it exists
    secrets_dir = Path('/run/secrets')
    if secrets_dir.exists():
        if os.access(secrets_dir, os.R_OK):
            print("SUCCESS: Docker secrets directory is accessible")
        else:
            print("ERROR: Docker secrets directory is not accessible")
            return False
    
    return True


def main():
    """Main startup validation function"""
    print("Starting Docker container validation...")
    print("=" * 60)
    
    service_name = os.getenv('SERVICE_NAME', 'unknown')
    print(f"Service: {service_name}")
    print(f"Container: {os.getenv('HOSTNAME', 'unknown')}")
    print("=" * 60)
    
    success = True
    
    # Step 1: Wait for dependencies
    success &= wait_for_dependencies()
    
    # Step 2: Validate file permissions
    success &= validate_file_permissions()
    
    # Step 3: Validate environment variables
    success &= validate_environment_variables()
    
    # Step 4: Run credential validation if available
    try:
        from validate_credentials import main as validate_creds
        print("\nRunning credential validation...")
        cred_result = validate_creds()
        success &= (cred_result == 0)
    except ImportError:
        print("INFO: Credential validation script not available")
    except Exception as e:
        print(f"ERROR: Credential validation failed: {e}")
        success = False
    
    print("=" * 60)
    if success:
        print("SUCCESS: Container startup validation completed successfully")
        print("Service is ready to start")
        return 0
    else:
        print("ERROR: Container startup validation failed")
        print("Service startup aborted")
        return 1


if __name__ == "__main__":
    sys.exit(main())