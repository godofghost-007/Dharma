#!/usr/bin/env python3
"""
Test Reddit API Integration
"""

import praw
import streamlit as st
from datetime import datetime

def test_reddit_api():
    """Test Reddit API connection and search"""
    
    # Get credentials from Streamlit secrets
    try:
        client_id = st.secrets.get("REDDIT_CLIENT_ID", "")
        client_secret = st.secrets.get("REDDIT_CLIENT_SECRET", "")
        user_agent = st.secrets.get("REDDIT_USER_AGENT", "DharmaDetector/1.0")
        
        if not client_id or not client_secret:
            print("❌ Reddit API credentials not found in secrets")
            return False
        
        print(f"🔑 Testing Reddit API with client ID: {client_id[:10]}...")
        
        # Initialize Reddit client
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )
        
        # Test connection
        print("🔄 Testing Reddit connection...")
        
        # Search for test content
        subreddit = reddit.subreddit('india')
        print(f"✅ Connected to r/india subreddit")
        
        # Get recent posts
        posts = list(subreddit.search('india', sort='new', time_filter='week', limit=5))
        print(f"✅ Found {len(posts)} recent posts")
        
        for i, post in enumerate(posts[:3]):
            print(f"📝 Post {i+1}: {post.title[:50]}...")
            print(f"   Score: {post.score}, Comments: {post.num_comments}")
            print(f"   URL: https://reddit.com{post.permalink}")
        
        print("✅ Reddit API integration test successful!")
        return True
        
    except Exception as e:
        print(f"❌ Reddit API test failed: {e}")
        return False

if __name__ == "__main__":
    test_reddit_api()