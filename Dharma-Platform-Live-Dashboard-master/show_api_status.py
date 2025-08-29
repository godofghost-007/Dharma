#!/usr/bin/env python3
"""
Show API Configuration Status
"""

from api_config import get_api_config

def main():
    """Show current API configuration status"""
    print("🔑 Dharma Platform API Configuration")
    print("=" * 40)
    
    config = get_api_config()
    config.print_configuration_status()
    
    print("\n📋 API Key Details:")
    
    # YouTube
    if config.is_youtube_configured():
        print(f"✅ YouTube API Key: {config.youtube_api_key[:15]}...")
    else:
        print("❌ YouTube API Key: Not configured")
    
    # Twitter
    if config.is_twitter_configured():
        print(f"✅ Twitter Bearer Token: {config.twitter_bearer_token[:15]}...")
    else:
        print("❌ Twitter Bearer Token: Not configured")
    
    # Telegram
    if config.is_telegram_configured():
        if config.telegram_bot_token:
            print(f"✅ Telegram Bot Token: {config.telegram_bot_token[:15]}...")
        else:
            print(f"✅ Telegram API ID: {config.telegram_api_id}")
    else:
        print("❌ Telegram: Not configured")
    
    print("\n💡 To add more API keys:")
    print("1. Edit the .env file in this directory")
    print("2. Or run: python api_config.py")
    print("3. Or set environment variables directly")

if __name__ == "__main__":
    main()