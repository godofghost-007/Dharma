"""
Secure environment configuration loader with validation
"""
import os
from typing import Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass


@dataclass
class TwitterCredentials:
    """Twitter API credentials"""
    api_key: str
    api_secret: str
    bearer_token: str
    access_token: str
    access_token_secret: str


@dataclass
class YouTubeCredentials:
    """YouTube API credentials"""
    api_key: str


@dataclass
class TelegramCredentials:
    """Telegram Bot API credentials"""
    bot_token: str


class EnvironmentValidationError(Exception):
    """Raised when environment validation fails"""
    pass


class SecureEnvironmentLoader:
    """
    Secure environment configuration loader with comprehensive validation
    """
    
    # Required environment variables for API credentials
    REQUIRED_TWITTER_VARS = [
        'TWITTER_API_KEY',
        'TWITTER_API_SECRET', 
        'TWITTER_BEARER_TOKEN',
        'TWITTER_ACCESS_TOKEN',
        'TWITTER_ACCESS_TOKEN_SECRET'
    ]
    
    REQUIRED_YOUTUBE_VARS = [
        'YOUTUBE_API_KEY'
    ]
    
    REQUIRED_TELEGRAM_VARS = [
        'TELEGRAM_BOT_TOKEN'
    ]
    
    def __init__(self, env_file_path: Optional[str] = None):
        """Initialize the environment loader"""
        self.env_file_path = env_file_path or self._find_env_file()
        self.missing_vars: List[str] = []
        self.invalid_vars: Dict[str, str] = {}
        
    def _find_env_file(self) -> Optional[str]:
        """Find .env file in project structure"""
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent
        env_file = project_root / '.env'
        
        if env_file.exists():
            return str(env_file)
        return None
    
    def _load_env_file(self, env_file_path: str) -> Dict[str, str]:
        """Simple .env file loader"""
        env_vars = {}
        try:
            with open(env_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        env_vars[key] = value
        except Exception as e:
            print(f"Error loading .env file: {e}")
        return env_vars
    
    def load_environment(self) -> bool:
        """Load environment variables from .env file"""
        try:
            if self.env_file_path and Path(self.env_file_path).exists():
                env_vars = self._load_env_file(self.env_file_path)
                for key, value in env_vars.items():
                    if key not in os.environ:  # Don't override existing env vars
                        os.environ[key] = value
                print(f"Loaded {len(env_vars)} variables from {self.env_file_path}")
                return True
            else:
                print("No .env file found, using system environment variables only")
                return True
        except Exception as e:
            print(f"Error loading environment: {e}")
            return False
    
    def validate_required_variables(self, variable_groups: Optional[List[str]] = None) -> bool:
        """Validate that all required environment variables are present"""
        self.missing_vars = []
        
        # Default to all groups if none specified
        if variable_groups is None:
            variable_groups = ['twitter', 'youtube', 'telegram']
        
        # Validate each requested group
        for group in variable_groups:
            if group == 'twitter':
                self._validate_variable_group(self.REQUIRED_TWITTER_VARS)
            elif group == 'youtube':
                self._validate_variable_group(self.REQUIRED_YOUTUBE_VARS)
            elif group == 'telegram':
                self._validate_variable_group(self.REQUIRED_TELEGRAM_VARS)
        
        return len(self.missing_vars) == 0
    
    def _validate_variable_group(self, variables: List[str]) -> None:
        """Validate a group of environment variables"""
        for var in variables:
            value = os.getenv(var)
            if not value or not value.strip():
                self.missing_vars.append(var)
    
    def get_twitter_credentials(self) -> TwitterCredentials:
        """Get Twitter API credentials"""
        if not self.validate_required_variables(['twitter']):
            raise EnvironmentValidationError(f"Twitter credentials validation failed. Missing: {self.missing_vars}")
        
        return TwitterCredentials(
            api_key=os.getenv('TWITTER_API_KEY'),
            api_secret=os.getenv('TWITTER_API_SECRET'),
            bearer_token=os.getenv('TWITTER_BEARER_TOKEN'),
            access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
            access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
        )
    
    def get_youtube_credentials(self) -> YouTubeCredentials:
        """Get YouTube API credentials"""
        if not self.validate_required_variables(['youtube']):
            raise EnvironmentValidationError(f"YouTube credentials validation failed. Missing: {self.missing_vars}")
        
        return YouTubeCredentials(
            api_key=os.getenv('YOUTUBE_API_KEY')
        )
    
    def get_telegram_credentials(self) -> TelegramCredentials:
        """Get Telegram Bot API credentials"""
        if not self.validate_required_variables(['telegram']):
            raise EnvironmentValidationError(f"Telegram credentials validation failed. Missing: {self.missing_vars}")
        
        return TelegramCredentials(
            bot_token=os.getenv('TELEGRAM_BOT_TOKEN')
        )
    
    def print_validation_errors(self) -> None:
        """Print detailed validation errors to console"""
        if self.missing_vars:
            print("\n❌ Missing Required Environment Variables:")
            for var in self.missing_vars:
                print(f"  - {var}")
        else:
            print("\n✅ All environment variables are valid!")


# Global instance for easy access
env_loader = SecureEnvironmentLoader()


def load_and_validate_environment(variable_groups: Optional[List[str]] = None) -> bool:
    """Convenience function to load and validate environment"""
    if not env_loader.load_environment():
        return False
    
    if not env_loader.validate_required_variables(variable_groups):
        env_loader.print_validation_errors()
        return False
    
    return True


def get_credentials_for_platform(platform: str):
    """Get credentials for a specific platform"""
    platform = platform.lower()
    
    if platform == 'twitter':
        return env_loader.get_twitter_credentials()
    elif platform == 'youtube':
        return env_loader.get_youtube_credentials()
    elif platform == 'telegram':
        return env_loader.get_telegram_credentials()
    else:
        raise ValueError(f"Unsupported platform: {platform}")


if __name__ == "__main__":
    print("🔍 Environment Loader CLI")
    loader = SecureEnvironmentLoader()
    
    if loader.load_environment():
        print("✅ Environment loaded successfully")
        
        if loader.validate_required_variables():
            print("✅ All validations passed")
            
            # Test getting credentials
            try:
                twitter_creds = loader.get_twitter_credentials()
                print(f"✅ Twitter API Key: {twitter_creds.api_key[:10]}...")
                
                youtube_creds = loader.get_youtube_credentials()
                print(f"✅ YouTube API Key: {youtube_creds.api_key[:10]}...")
                
                telegram_creds = loader.get_telegram_credentials()
                print(f"✅ Telegram Bot Token: {telegram_creds.bot_token[:10]}...")
                
            except Exception as e:
                print(f"❌ Error getting credentials: {e}")
        else:
            print("❌ Validation failed")
            loader.print_validation_errors()
    else:
        print("❌ Failed to load environment")