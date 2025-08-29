"""
🛡️ Dharma Platform - Enhanced Threat Dashboard
Fixed version with proper video links and threat analysis reports
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import json
import time
from datetime import datetime, timedelta
import re
from textblob import TextBlob
import numpy as np
from typing import List, Dict, Any, Optional

# Page Configuration
st.set_page_config(
    page_title="🛡️ Dharma Platform - Enhanced Threat Detection",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS for proper display
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0a0a0a 0%, #1a0033 25%, #000428 50%, #004e92 75%, #000428 100%);
        background-size: 400% 400%;
        animation: gradientShift 20s ease infinite;
        color: #ffffff;
        font-family: 'Arial', sans-serif;
    }
    
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    .threat-card {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.05));
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        transition: all 0.3s ease;
    }
    
    .threat-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
    }
</style>
""", unsafe_allow_html=True)

class EnhancedThreatDetector:
    def __init__(self):
        self.youtube_api_key = st.secrets.get("YOUTUBE_API_KEY", "")
        
        self.threat_keywords = {
            'critical': [
                'anti india', 'anti-india', 'destroy india', 'break india',
                'india terrorist', 'hindu terrorist', 'modi terrorist',
                'kashmir independence', 'khalistan', 'separate kashmir'
            ],
            'high': [
                'india bad', 'india evil', 'india problem', 'hate india',
                'india fascist', 'india nazi', 'bjp terrorist', 'rss terrorist'
            ],
            'medium': [
                'india issues', 'india problems', 'india criticism',
                'india negative', 'india wrong', 'india mistake'
            ]
        }

    def calculate_threat_score(self, text: str) -> tuple:
        """Calculate comprehensive threat score"""
        text_lower = text.lower()
        score = 0
        matched_keywords = []
        threat_details = []
        
        # Critical keywords
        for keyword in self.threat_keywords['critical']:
            if keyword in text_lower:
                score += 15
                matched_keywords.append(f"🚨 CRITICAL: {keyword}")
                threat_details.append(f"Direct threat language detected: '{keyword}'")
        
        # High keywords  
        for keyword in self.threat_keywords['high']:
            if keyword in text_lower:
                score += 10
                matched_keywords.append(f"⚠️ HIGH: {keyword}")
                threat_details.append(f"Hostile language detected: '{keyword}'")
        
        # Medium keywords
        for keyword in self.threat_keywords['medium']:
            if keyword in text_lower:
                score += 6
                matched_keywords.append(f"🔶 MEDIUM: {keyword}")
                threat_details.append(f"Negative sentiment detected: '{keyword}'")
        
        # Sentiment analysis
        try:
            blob = TextBlob(text)
            sentiment = blob.sentiment.polarity
            if sentiment < -0.5:
                score += 5
                matched_keywords.append("😡 SENTIMENT: Extremely negative")
                threat_details.append(f"Sentiment analysis: Extremely negative ({sentiment:.2f})")
            elif sentiment < -0.2:
                score += 3
                matched_keywords.append("😠 SENTIMENT: Negative")
                threat_details.append(f"Sentiment analysis: Negative ({sentiment:.2f})")
        except:
            pass
        
        # Determine threat level
        if score >= 25:
            level = "CRITICAL"
        elif score >= 18:
            level = "HIGH"
        elif score >= 10:
            level = "MEDIUM"
        elif score >= 5:
            level = "LOW"
        else:
            level = "MINIMAL"
        
        return score, level, matched_keywords, threat_details

    def search_youtube(self, query: str, max_results: int = 15) -> List[Dict]:
        """Enhanced YouTube search with proper video information"""
        if not self.youtube_api_key:
            st.error("YouTube API key not configured")
            return []
        
        try:
            url = "https://www.googleapis.com/youtube/v3/search"
            params = {
                'part': 'snippet',
                'q': query,
                'type': 'video',
                'maxResults': max_results,
                'key': self.youtube_api_key,
                'order': 'relevance',
                'publishedAfter': (datetime.now() - timedelta(days=30)).isoformat() + 'Z'
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                results = []
                
                for item in data.get('items', []):
                    snippet = item['snippet']
                    video_id = item['id']['videoId']
                    title = snippet['title']
                    description = snippet['description']
                    combined_text = f"{title} {description}"
                    
                    score, level, keywords, details = self.calculate_threat_score(combined_text)
                    
                    # Get video statistics
                    stats = self.get_video_stats(video_id)
                    
                    results.append({
                        'platform': 'YouTube',
                        'video_id': video_id,
                        'title': title,
                        'description': description,
                        'url': f"https://www.youtube.com/watch?v={video_id}",
                        'thumbnail': snippet['thumbnails']['medium']['url'],
                        'channel': snippet['channelTitle'],
                        'published': snippet['publishedAt'],
                        'threat_score': score,
                        'threat_level': level,
                        'matched_keywords': keywords,
                        'threat_details': details,
                        'stats': stats
                    })
                
                return sorted(results, key=lambda x: x['threat_score'], reverse=True)
            else:
                st.error(f"YouTube API error: {response.status_code}")
                return []
            
        except Exception as e:
            st.error(f"YouTube search error: {e}")
            return []

    def get_video_stats(self, video_id: str) -> Dict:
        """Get detailed video statistics"""
        try:
            url = "https://www.googleapis.com/youtube/v3/videos"
            params = {
                'part': 'statistics,contentDetails',
                'id': video_id,
                'key': self.youtube_api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('items'):
                    stats = data['items'][0]['statistics']
                    content = data['items'][0]['contentDetails']
                    return {
                        'views': int(stats.get('viewCount', 0)),
                        'likes': int(stats.get('likeCount', 0)),
                        'comments': int(stats.get('commentCount', 0)),
                        'duration': content.get('duration', 'N/A')
                    }
        except Exception:
            pass
        
        return {'views': 0, 'likes': 0, 'comments': 0, 'duration': 'N/A'}

    def search_reddit(self, query: str, max_results: int = 15) -> List[Dict]:
        """Enhanced Reddit search with proper post information"""
        try:
            results = []
            subreddits = ['india', 'worldnews', 'news', 'politics']
            
            for subreddit in subreddits:
                try:
                    url = f"https://www.reddit.com/r/{subreddit}/search.json"
                    params = {
                        'q': query,
                        'sort': 'new',
                        't': 'month',
                        'limit': max_results // len(subreddits)
                    }
                    
                    headers = {'User-Agent': 'DharmaDetector/2.0'}
                    response = requests.get(url, params=params, headers=headers, timeout=15)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        for post in data.get('data', {}).get('children', []):
                            post_data = post['data']
                            combined_text = f"{post_data['title']} {post_data.get('selftext', '')}"
                            score, level, keywords, details = self.calculate_threat_score(combined_text)
                            
                            results.append({
                                'platform': 'Reddit',
                                'title': post_data['title'],
                                'description': post_data.get('selftext', ''),
                                'url': f"https://reddit.com{post_data['permalink']}",
                                'subreddit': post_data['subreddit'],
                                'author': post_data.get('author', '[deleted]'),
                                'score': post_data.get('score', 0),
                                'comments': post_data.get('num_comments', 0),
                                'created': datetime.fromtimestamp(post_data['created_utc']).isoformat(),
                                'threat_score': score,
                                'threat_level': level,
                                'matched_keywords': keywords,
                                'threat_details': details,
                                'upvote_ratio': post_data.get('upvote_ratio', 0.5)
                            })
                
                except Exception:
                    continue
            
            return sorted(results, key=lambda x: x['threat_score'], reverse=True)[:max_results]
            
        except Exception as e:
            st.error(f"Reddit search error: {e}")
            return []

def display_enhanced_result_card(result: Dict, index: int):
    """Display enhanced result card with proper links and analysis"""
    
    # Threat level colors and emojis
    threat_config = {
        'CRITICAL': {'color': '#ff0040', 'emoji': '🚨', 'bg': 'rgba(255, 0, 64, 0.1)'},
        'HIGH': {'color': '#ff6348', 'emoji': '⚠️', 'bg': 'rgba(255, 99, 72, 0.1)'},
        'MEDIUM': {'color': '#ffa502', 'emoji': '🔶', 'bg': 'rgba(255, 165, 2, 0.1)'},
        'LOW': {'color': '#4caf50', 'emoji': '✅', 'bg': 'rgba(76, 175, 80, 0.1)'},
        'MINIMAL': {'color': '#2196f3', 'emoji': 'ℹ️', 'bg': 'rgba(33, 150, 243, 0.1)'}
    }
    
    config = threat_config.get(result['threat_level'], threat_config['MINIMAL'])
    
    # Create container with proper styling
    with st.container():
        # Header with platform and threat level
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if result['platform'] == 'YouTube':
                st.markdown(f"### 🎥 **{result['title']}**")
            else:
                st.markdown(f"### 🔴 **{result['title']}**")
        
        with col2:
            st.markdown(f"""
            <div style="
                background: {config['bg']};
                border: 2px solid {config['color']};
                border-radius: 10px;
                padding: 0.5rem;
                text-align: center;
                color: {config['color']};
                font-weight: bold;
            ">
                {config['emoji']} {result['threat_level']}<br>
                Score: {result['threat_score']}
            </div>
            """, unsafe_allow_html=True)
        
        # Content description
        if result['description']:
            with st.expander("📄 **Content Description**", expanded=False):
                st.write(result['description'][:500] + "..." if len(result['description']) > 500 else result['description'])
        
        # Platform-specific information
        if result['platform'] == 'YouTube':
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("👁️ Views", f"{result['stats']['views']:,}" if result['stats']['views'] > 0 else "N/A")
            with col2:
                st.metric("👍 Likes", f"{result['stats']['likes']:,}" if result['stats']['likes'] > 0 else "N/A")
            with col3:
                st.metric("💬 Comments", f"{result['stats']['comments']:,}" if result['stats']['comments'] > 0 else "N/A")
            with col4:
                st.metric("📺 Channel", result['channel'])
            
            # Video thumbnail and link
            col1, col2 = st.columns([1, 2])
            with col1:
                if 'thumbnail' in result:
                    st.image(result['thumbnail'], width=200)
            with col2:
                st.markdown(f"""
                **📅 Published:** {result['published'][:10]}  
                **⏱️ Duration:** {result['stats']['duration']}  
                **🔗 Video ID:** {result.get('video_id', 'N/A')}
                """)
                
                # Direct video link
                st.markdown(f"""
                <a href="{result['url']}" target="_blank" style="
                    background: linear-gradient(45deg, #ff0000, #cc0000);
                    color: white;
                    padding: 10px 20px;
                    border-radius: 25px;
                    text-decoration: none;
                    font-weight: bold;
                    display: inline-block;
                    margin: 10px 0;
                ">🎥 Watch on YouTube</a>
                """, unsafe_allow_html=True)
        
        else:  # Reddit
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("⬆️ Score", result['score'])
            with col2:
                st.metric("💬 Comments", result['comments'])
            with col3:
                st.metric("📊 Upvote Ratio", f"{result['upvote_ratio']:.1%}")
            with col4:
                st.metric("📍 Subreddit", f"r/{result['subreddit']}")
            
            st.markdown(f"""
            **👤 Author:** {result['author']}  
            **📅 Posted:** {result['created'][:10]}
            """)
            
            # Direct Reddit link
            st.markdown(f"""
            <a href="{result['url']}" target="_blank" style="
                background: linear-gradient(45deg, #ff4500, #ff6500);
                color: white;
                padding: 10px 20px;
                border-radius: 25px;
                text-decoration: none;
                font-weight: bold;
                display: inline-block;
                margin: 10px 0;
            ">🔴 View on Reddit</a>
            """, unsafe_allow_html=True)
        
        # Detailed Threat Analysis Report
        if result['matched_keywords'] or result['threat_details']:
            with st.expander("🛡️ **Detailed Threat Analysis Report**", expanded=False):
                
                # Threat Summary
                st.markdown("#### 📊 **Threat Assessment Summary**")
                st.markdown(f"""
                - **Threat Level:** {config['emoji']} **{result['threat_level']}**
                - **Threat Score:** **{result['threat_score']}/50**
                - **Risk Category:** {result['threat_level'].title()} Risk Content
                - **Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                """)
                
                # Detected Indicators
                if result['matched_keywords']:
                    st.markdown("#### 🎯 **Detected Threat Indicators**")
                    for keyword in result['matched_keywords']:
                        st.markdown(f"• {keyword}")
                
                # Detailed Analysis
                if result['threat_details']:
                    st.markdown("#### 🔬 **Detailed Analysis**")
                    for detail in result['threat_details']:
                        st.markdown(f"• {detail}")
                
                # Recommendations
                st.markdown("#### 💡 **Recommendations**")
                if result['threat_level'] == 'CRITICAL':
                    st.error("🚨 **IMMEDIATE ACTION REQUIRED** - This content contains direct threats or extremely harmful language.")
                elif result['threat_level'] == 'HIGH':
                    st.warning("⚠️ **HIGH PRIORITY** - This content shows significant hostile sentiment and requires attention.")
                elif result['threat_level'] == 'MEDIUM':
                    st.info("🔶 **MODERATE CONCERN** - This content contains negative sentiment that should be monitored.")
                else:
                    st.success("✅ **LOW RISK** - This content shows minimal threat indicators.")
        
        # Separator
        st.markdown("---")

def main():
    # Initialize session state
    if 'results' not in st.session_state:
        st.session_state.results = []
    if 'search_performed' not in st.session_state:
        st.session_state.search_performed = False
    
    # Header
    st.markdown("""
    <div style="
        background: linear-gradient(45deg, #ff0080, #ff8c00, #40e0d0, #ff0080);
        background-size: 400% 400%;
        animation: holographic 8s ease infinite;
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 2rem;
        color: white;
    ">
        <h1>🛡️ DHARMA PLATFORM</h1>
        <h2>Enhanced Threat Detection & Analysis System</h2>
        <p>Real-time monitoring with comprehensive threat analysis reports</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize detector
    detector = EnhancedThreatDetector()
    
    # Sidebar
    with st.sidebar:
        st.markdown("## 🎛️ Control Panel")
        
        # API Status
        st.markdown("### 🔌 System Status")
        youtube_status = "🟢 ONLINE" if detector.youtube_api_key else "🔴 OFFLINE"
        st.markdown(f"**YouTube API:** {youtube_status}")
        st.markdown(f"**Reddit API:** 🟢 ONLINE")
        
        # Search Configuration
        st.markdown("### 🔍 Search Parameters")
        search_query = st.text_input(
            "Search Query",
            value="anti india propaganda",
            help="Enter keywords for threat detection"
        )
        
        max_results = st.slider("Results Per Platform", 5, 25, 15)
        
        # Platform Selection
        st.markdown("### 📡 Platforms")
        search_youtube = st.checkbox("🎥 YouTube", value=True)
        search_reddit = st.checkbox("🔴 Reddit", value=True)
        
        # Threat Filters
        st.markdown("### ⚠️ Threat Filters")
        show_critical = st.checkbox("🚨 Critical", value=True)
        show_high = st.checkbox("⚠️ High", value=True)
        show_medium = st.checkbox("🔶 Medium", value=True)
        show_low = st.checkbox("✅ Low", value=True)
        show_minimal = st.checkbox("ℹ️ Minimal", value=False)
    
    # Main Interface
    col1, col2, col3 = st.columns([3, 2, 2])
    
    with col1:
        if st.button("🚀 **START THREAT ANALYSIS**", type="primary"):
            with st.spinner("🔍 **Analyzing threats across platforms...**"):
                all_results = []
                
                # Search YouTube
                if search_youtube and detector.youtube_api_key:
                    with st.status("🎥 **Scanning YouTube...**") as status:
                        youtube_results = detector.search_youtube(search_query, max_results)
                        all_results.extend(youtube_results)
                        status.update(label=f"✅ **YouTube: {len(youtube_results)} results analyzed**", state="complete")
                
                # Search Reddit
                if search_reddit:
                    with st.status("🔴 **Scanning Reddit...**") as status:
                        reddit_results = detector.search_reddit(search_query, max_results)
                        all_results.extend(reddit_results)
                        status.update(label=f"✅ **Reddit: {len(reddit_results)} results analyzed**", state="complete")
                
                # Filter results
                filtered_results = []
                for result in all_results:
                    level = result['threat_level']
                    if ((level == 'CRITICAL' and show_critical) or
                        (level == 'HIGH' and show_high) or
                        (level == 'MEDIUM' and show_medium) or
                        (level == 'LOW' and show_low) or
                        (level == 'MINIMAL' and show_minimal)):
                        filtered_results.append(result)
                
                st.session_state.results = filtered_results
                st.session_state.search_performed = True
                
                st.success(f"✅ **Analysis Complete!** Found {len(filtered_results)} results with threat analysis.")
    
    with col2:
        if st.button("🎯 **Auto Detect**"):
            with st.spinner("🎯 **Running auto-detection...**"):
                auto_query = "anti india propaganda terrorism"
                all_results = []
                
                if detector.youtube_api_key:
                    youtube_results = detector.search_youtube(auto_query, max_results)
                    all_results.extend(youtube_results)
                
                reddit_results = detector.search_reddit(auto_query, max_results)
                all_results.extend(reddit_results)
                
                # Filter results
                filtered_results = []
                for result in all_results:
                    level = result['threat_level']
                    if ((level == 'CRITICAL' and show_critical) or
                        (level == 'HIGH' and show_high) or
                        (level == 'MEDIUM' and show_medium) or
                        (level == 'LOW' and show_low) or
                        (level == 'MINIMAL' and show_minimal)):
                        filtered_results.append(result)
                
                st.session_state.results = filtered_results
                st.session_state.search_performed = True
                
                st.success(f"🎯 **Auto-detection complete!** {len(filtered_results)} threats identified.")
    
    with col3:
        if st.button("🔄 **Clear Results**"):
            st.session_state.results = []
            st.session_state.search_performed = False
            st.success("✅ **Results cleared!**")
    
    # Display Results
    results = st.session_state.results
    
    if results and st.session_state.search_performed:
        # Summary
        st.markdown("## 📊 **Analysis Summary**")
        
        threat_counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0, 'MINIMAL': 0}
        for result in results:
            threat_counts[result['threat_level']] += 1
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("🚨 Critical", threat_counts['CRITICAL'])
        with col2:
            st.metric("⚠️ High", threat_counts['HIGH'])
        with col3:
            st.metric("🔶 Medium", threat_counts['MEDIUM'])
        with col4:
            st.metric("✅ Low", threat_counts['LOW'])
        with col5:
            st.metric("ℹ️ Minimal", threat_counts['MINIMAL'])
        
        # Results
        st.markdown("## 🎯 **Detailed Analysis Results**")
        
        # Sort options
        sort_by = st.selectbox("🔄 Sort by", ["Threat Score", "Platform", "Date"])
        
        if sort_by == "Threat Score":
            results = sorted(results, key=lambda x: x['threat_score'], reverse=True)
        elif sort_by == "Platform":
            results = sorted(results, key=lambda x: x['platform'])
        elif sort_by == "Date":
            results = sorted(results, key=lambda x: x.get('published', x.get('created', '')), reverse=True)
        
        # Display results
        for i, result in enumerate(results):
            display_enhanced_result_card(result, i)
    
    elif st.session_state.search_performed and not results:
        st.info("🔍 No threats detected with current filters. Try adjusting your search criteria.")
    
    else:
        # Welcome message
        st.markdown("""
        ## 🛡️ **Welcome to Enhanced Threat Detection**
        
        This system provides comprehensive analysis of potential threats across YouTube and Reddit platforms.
        
        ### 🎯 **Features:**
        - **Real-time threat detection** with advanced scoring algorithms
        - **Detailed analysis reports** with specific threat indicators
        - **Direct content links** for immediate verification
        - **Multi-platform monitoring** across YouTube and Reddit
        - **Interactive filtering** by threat levels
        
        ### 🚀 **Get Started:**
        1. Configure your search terms in the sidebar
        2. Select platforms to monitor
        3. Click "START THREAT ANALYSIS" to begin
        4. Review detailed reports for each detected threat
        
        **Ready to protect against digital threats!** 🛡️
        """)

if __name__ == "__main__":
    main()