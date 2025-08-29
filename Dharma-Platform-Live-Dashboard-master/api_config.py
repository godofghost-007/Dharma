#!/usr/bin/env python3
"""
API Configuration for Dharma Platform
Configure your social media API keys here
"""

import os
from typing import Dict, Optional
from pathlib import Path

# Try to load from .env file
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass

class APIConfig:
    """Configuration class for social media APIs"""
    
    def __init__(self):
        self.load_from_env()
    
    def load_from_env(self):
        """Load API keys from environment variables"""
        # Twitter API Configuration
        self.twitter_bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        self.twitter_api_key = os.getenv('TWITTER_API_KEY')
        self.twitter_api_secret = os.getenv('TWITTER_API_SECRET')
        self.twitter_access_token = os.getenv('TWITTER_ACCESS_TOKEN')
        self.twitter_access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
        
        # YouTube API Configuration - set the key directly if not in env
        self.youtube_api_key = os.getenv('YOUTUBE_API_KEY', 'AIzaSyAsiBWQPODfeRYuU2iKvh8CdpTvLGCUG50')
        
        # Telegram API Configuration
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_api_id = os.getenv('TELEGRAM_API_ID')
        self.telegram_api_hash = os.getenv('TELEGRAM_API_HASH')
        
        # Reddit API Configuration (optional)
        self.reddit_client_id = os.getenv('REDDIT_CLIENT_ID')
        self.reddit_client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        self.reddit_user_agent = os.getenv('REDDIT_USER_AGENT', 'DharmaPlatform/1.0')
    
    def get_twitter_config(self) -> Dict[str, Optional[str]]:
        """Get Twitter API configuration"""
        return {
            'bearer_token': self.twitter_bearer_token,
            'api_key': self.twitter_api_key,
            'api_secret': self.twitter_api_secret,
            'access_token': self.twitter_access_token,
            'access_token_secret': self.twitter_access_token_secret
        }
    
    def get_youtube_config(self) -> Dict[str, Optional[str]]:
        """Get YouTube API configuration"""
        return {
            'api_key': self.youtube_api_key
        }
    
    def get_telegram_config(self) -> Dict[str, Optional[str]]:
        """Get Telegram API configuration"""
        return {
            'bot_token': self.telegram_bot_token,
            'api_id': self.telegram_api_id,
            'api_hash': self.telegram_api_hash
        }
    
    def get_reddit_config(self) -> Dict[str, Optional[str]]:
        """Get Reddit API configuration"""
        return {
            'client_id': self.reddit_client_id,
            'client_secret': self.reddit_client_secret,
            'user_agent': self.reddit_user_agent
        }
    
    def is_twitter_configured(self) -> bool:
        """Check if Twitter API is configured"""
        return bool(self.twitter_bearer_token or (self.twitter_api_key and self.twitter_api_secret))
    
    def is_youtube_configured(self) -> bool:
        """Check if YouTube API is configured"""
        return bool(self.youtube_api_key)
    
    def is_telegram_configured(self) -> bool:
        """Check if Telegram API is configured"""
        return bool(self.telegram_bot_token or (self.telegram_api_id and self.telegram_api_hash))
    
    def is_reddit_configured(self) -> bool:
        """Check if Reddit API is configured"""
        return bool(self.reddit_client_id and self.reddit_client_secret)
    
    def get_configured_platforms(self) -> list:
        """Get list of configured platforms"""
        platforms = []
        
        if self.is_twitter_configured():
            platforms.append('Twitter')
        
        if self.is_youtube_configured():
            platforms.append('YouTube')
        
        if self.is_telegram_configured():
            platforms.append('Telegram')
        
        if self.is_reddit_configured():
            platforms.append('Reddit')
        
        # Reddit is always available via public API
        if 'Reddit' not in platforms:
            platforms.append('Reddit')
        
        return platforms
    
    def print_configuration_status(self):
        """Print current configuration status"""
        print("🔑 API Configuration Status:")
        print("=" * 30)
        
        print(f"Twitter: {'✅ Configured' if self.is_twitter_configured() else '❌ Not configured'}")
        print(f"YouTube: {'✅ Configured' if self.is_youtube_configured() else '❌ Not configured'}")
        print(f"Telegram: {'✅ Configured' if self.is_telegram_configured() else '❌ Not configured'}")
        print(f"Reddit: {'✅ Configured' if self.is_reddit_configured() else '✅ Public API (no auth needed)'}")
        
        print(f"\nConfigured platforms: {', '.join(self.get_configured_platforms())}")
        
        if not any([self.is_twitter_configured(), self.is_youtube_configured(), self.is_telegram_configured()]):
            print("\n⚠️  No API keys configured. The system will use:")
            print("   • Reddit public API (no authentication required)")
            print("   • Demo data for other platforms")
            print("\n💡 To collect real data, add your API keys to environment variables:")
            print("   • TWITTER_BEARER_TOKEN=your_twitter_bearer_token")
            print("   • YOUTUBE_API_KEY=your_youtube_api_key")
            print("   • TELEGRAM_BOT_TOKEN=your_telegram_bot_token")

# Global configuration instance
api_config = APIConfig()

# Helper functions
def get_api_config() -> APIConfig:
    """Get the global API configuration instance"""
    return api_config

def setup_environment_variables():
    """Setup environment variables from user input"""
    print("🔧 API Configuration Setup")
    print("=" * 30)
    print("Enter your API keys (press Enter to skip):")
    
    # Twitter setup
    print("\n📱 Twitter API:")
    twitter_bearer = input("Twitter Bearer Token: ").strip()
    if twitter_bearer:
        os.environ['TWITTER_BEARER_TOKEN'] = twitter_bearer
    
    # YouTube setup
    print("\n📺 YouTube API:")
    youtube_key = input("YouTube API Key: ").strip()
    if youtube_key:
        os.environ['YOUTUBE_API_KEY'] = youtube_key
    
    # Telegram setup
    print("\n💬 Telegram API:")
    telegram_token = input("Telegram Bot Token: ").strip()
    if telegram_token:
        os.environ['TELEGRAM_BOT_TOKEN'] = telegram_token
    
    # Reload configuration
    global api_config
    api_config = APIConfig()
    
    print("\n✅ Configuration updated!")
    api_config.print_configuration_status()

if __name__ == "__main__":
    # Interactive setup
    setup_environment_variables()