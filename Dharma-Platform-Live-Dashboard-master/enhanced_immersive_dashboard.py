"""
🛡️ Dharma Platform - Enhanced Immersive Anti-Nationalist Detection Dashboard
Advanced real-time monitoring with YouTube and Reddit integration
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import asyncio
import aiohttp
import json
import time
from datetime import datetime, timedelta
import re
from textblob import TextBlob
import numpy as np
import praw
from typing import List, Dict, Any, Optional

# Page Configuration
st.set_page_config(
    page_title="🛡️ Dharma Platform - Anti-Nationalist Detection",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for immersive design
st.markdown("""
<style>
    /* Dark theme with gradient background */
    .stApp {
        background: linear-gradient(135deg, #0c1427 0%, #1a1a2e 50%, #16213e 100%);
        color: #ffffff;
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(90deg, #ff6b6b, #ee5a24, #ff9ff3, #54a0ff);
        background-size: 400% 400%;
        animation: gradient 15s ease infinite;
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(255, 107, 107, 0.3);
    }
    
    @keyframes gradient {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    /* Metric cards */
    .metric-card {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        transition: transform 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
    }
    
    /* Threat level indicators */
    .threat-critical {
        background: linear-gradient(45deg, #ff4757, #ff3838);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 25px;
        font-weight: bold;
        animation: pulse 2s infinite;
    }
    
    .threat-high {
        background: linear-gradient(45deg, #ff6348, #ff7675);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 25px;
        font-weight: bold;
    }
    
    .threat-medium {
        background: linear-gradient(45deg, #ffa502, #ff6348);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 25px;
        font-weight: bold;
    }
    
    .threat-low {
        background: linear-gradient(45deg, #2ed573, #7bed9f);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 25px;
        font-weight: bold;
    }
    
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.7; }
        100% { opacity: 1; }
    }
    
    /* Search box styling */
    .search-container {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 2rem;
        margin: 2rem 0;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    /* Results container */
    .results-container {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Platform badges */
    .platform-youtube {
        background: linear-gradient(45deg, #ff0000, #cc0000);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    
    .platform-reddit {
        background: linear-gradient(45deg, #ff4500, #ff6500);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(10px);
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(45deg, #667eea, #764ba2);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 0.5rem 2rem;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
    }
</style>
""", unsafe_allow_html=True)

class EnhancedThreatDetector:
    def __init__(self):
        self.youtube_api_key = st.secrets.get("YOUTUBE_API_KEY", "")
        self.reddit_client_id = st.secrets.get("REDDIT_CLIENT_ID", "")
        self.reddit_client_secret = st.secrets.get("REDDIT_CLIENT_SECRET", "")
        self.reddit_user_agent = st.secrets.get("REDDIT_USER_AGENT", "DharmaDetector/1.0")
        
        # Initialize Reddit client
        self.reddit = None
        if self.reddit_client_id and self.reddit_client_secret:
            try:
                self.reddit = praw.Reddit(
                    client_id=self.reddit_client_id,
                    client_secret=self.reddit_client_secret,
                    user_agent=self.reddit_user_agent
                )
            except Exception as e:
                st.error(f"Reddit API initialization failed: {e}")
        
        # Enhanced threat keywords
        self.threat_keywords = {
            'critical': [
                'anti india', 'anti-india', 'destroy india', 'break india',
                'india terrorist', 'hindu terrorist', 'modi terrorist',
                'kashmir independence', 'khalistan', 'separate kashmir',
                'india occupation', 'indian army crimes', 'genocide india'
            ],
            'high': [
                'india bad', 'india evil', 'india problem', 'hate india',
                'india fascist', 'india nazi', 'bjp terrorist', 'rss terrorist',
                'india fake', 'india lies', 'boycott india', 'stop india'
            ],
            'medium': [
                'india issues', 'india problems', 'india criticism',
                'india negative', 'india wrong', 'india mistake',
                'india controversy', 'india dispute', 'india conflict'
            ]
        }
        
        # Sentiment analysis patterns
        self.negative_patterns = [
            r'\b(hate|destroy|kill|bomb|attack|terror)\b.*\b(india|indian|hindu|modi)\b',
            r'\b(india|indian|hindu|modi)\b.*\b(bad|evil|worst|terrible|awful)\b',
            r'\b(fake|false|lie|propaganda)\b.*\b(india|indian)\b'
        ]

    def calculate_threat_score(self, text: str) -> tuple:
        """Calculate threat score and level"""
        text_lower = text.lower()
        score = 0
        matched_keywords = []
        
        # Check critical keywords
        for keyword in self.threat_keywords['critical']:
            if keyword in text_lower:
                score += 10
                matched_keywords.append(f"CRITICAL: {keyword}")
        
        # Check high keywords
        for keyword in self.threat_keywords['high']:
            if keyword in text_lower:
                score += 7
                matched_keywords.append(f"HIGH: {keyword}")
        
        # Check medium keywords
        for keyword in self.threat_keywords['medium']:
            if keyword in text_lower:
                score += 4
                matched_keywords.append(f"MEDIUM: {keyword}")
        
        # Check negative patterns
        for pattern in self.negative_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                score += 5
                matched_keywords.append("PATTERN: Negative sentiment detected")
        
        # Sentiment analysis
        try:
            blob = TextBlob(text)
            sentiment = blob.sentiment.polarity
            if sentiment < -0.5:
                score += 3
                matched_keywords.append("SENTIMENT: Highly negative")
            elif sentiment < -0.2:
                score += 1
                matched_keywords.append("SENTIMENT: Negative")
        except:
            pass
        
        # Determine threat level
        if score >= 15:
            level = "CRITICAL"
        elif score >= 10:
            level = "HIGH"
        elif score >= 5:
            level = "MEDIUM"
        else:
            level = "LOW"
        
        return score, level, matched_keywords

    async def search_youtube(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search YouTube for videos"""
        if not self.youtube_api_key:
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
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = []
                        
                        for item in data.get('items', []):
                            snippet = item['snippet']
                            title = snippet['title']
                            description = snippet['description']
                            combined_text = f"{title} {description}"
                            
                            score, level, keywords = self.calculate_threat_score(combined_text)
                            
                            results.append({
                                'platform': 'YouTube',
                                'title': title,
                                'description': description[:200] + "..." if len(description) > 200 else description,
                                'url': f"https://www.youtube.com/watch?v={item['id']['videoId']}",
                                'thumbnail': snippet['thumbnails']['medium']['url'],
                                'channel': snippet['channelTitle'],
                                'published': snippet['publishedAt'],
                                'threat_score': score,
                                'threat_level': level,
                                'matched_keywords': keywords
                            })
                        
                        return sorted(results, key=lambda x: x['threat_score'], reverse=True)
            
        except Exception as e:
            st.error(f"YouTube search error: {e}")
            return []

    def search_reddit(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search Reddit for posts"""
        if not self.reddit:
            return []
        
        try:
            results = []
            
            # Search across multiple subreddits
            subreddits = ['india', 'worldnews', 'news', 'politics', 'IndiaSpeaks', 'unitedstatesofindia']
            
            for subreddit_name in subreddits:
                try:
                    subreddit = self.reddit.subreddit(subreddit_name)
                    
                    # Search recent posts
                    for submission in subreddit.search(query, sort='new', time_filter='month', limit=max_results//len(subreddits)):
                        combined_text = f"{submission.title} {submission.selftext}"
                        score, level, keywords = self.calculate_threat_score(combined_text)
                        
                        results.append({
                            'platform': 'Reddit',
                            'title': submission.title,
                            'description': submission.selftext[:200] + "..." if len(submission.selftext) > 200 else submission.selftext,
                            'url': f"https://reddit.com{submission.permalink}",
                            'subreddit': submission.subreddit.display_name,
                            'author': str(submission.author) if submission.author else '[deleted]',
                            'score': submission.score,
                            'comments': submission.num_comments,
                            'created': datetime.fromtimestamp(submission.created_utc).isoformat(),
                            'threat_score': score,
                            'threat_level': level,
                            'matched_keywords': keywords
                        })
                        
                except Exception as e:
                    continue
            
            return sorted(results, key=lambda x: x['threat_score'], reverse=True)[:max_results]
            
        except Exception as e:
            st.error(f"Reddit search error: {e}")
            return []

def create_threat_level_chart(results: List[Dict]) -> go.Figure:
    """Create threat level distribution chart"""
    threat_counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
    
    for result in results:
        threat_counts[result['threat_level']] += 1
    
    fig = go.Figure(data=[
        go.Bar(
            x=list(threat_counts.keys()),
            y=list(threat_counts.values()),
            marker_color=['#ff4757', '#ff6348', '#ffa502', '#2ed573'],
            text=list(threat_counts.values()),
            textposition='auto',
        )
    ])
    
    fig.update_layout(
        title="Threat Level Distribution",
        xaxis_title="Threat Level",
        yaxis_title="Count",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='white'
    )
    
    return fig

def create_platform_comparison_chart(results: List[Dict]) -> go.Figure:
    """Create platform comparison chart"""
    platform_data = {}
    
    for result in results:
        platform = result['platform']
        if platform not in platform_data:
            platform_data[platform] = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        platform_data[platform][result['threat_level']] += 1
    
    fig = make_subplots(
        rows=1, cols=len(platform_data),
        subplot_titles=list(platform_data.keys()),
        specs=[[{"type": "pie"}] * len(platform_data)]
    )
    
    colors = ['#ff4757', '#ff6348', '#ffa502', '#2ed573']
    
    for i, (platform, data) in enumerate(platform_data.items()):
        fig.add_trace(
            go.Pie(
                labels=list(data.keys()),
                values=list(data.values()),
                marker_colors=colors,
                name=platform
            ),
            row=1, col=i+1
        )
    
    fig.update_layout(
        title="Threat Distribution by Platform",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='white'
    )
    
    return fig

def create_timeline_chart(results: List[Dict]) -> go.Figure:
    """Create timeline chart of threats"""
    timeline_data = []
    
    for result in results:
        if result['platform'] == 'YouTube':
            date = result['published']
        else:  # Reddit
            date = result['created']
        
        timeline_data.append({
            'date': pd.to_datetime(date),
            'threat_score': result['threat_score'],
            'platform': result['platform'],
            'title': result['title'][:50] + "..."
        })
    
    df = pd.DataFrame(timeline_data)
    
    if not df.empty:
        fig = px.scatter(
            df, 
            x='date', 
            y='threat_score',
            color='platform',
            hover_data=['title'],
            title="Threat Timeline Analysis"
        )
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='white'
        )
        
        return fig
    
    return go.Figure()

def display_result_card(result: Dict, index: int):
    """Display enhanced result card"""
    threat_class = f"threat-{result['threat_level'].lower()}"
    platform_class = f"platform-{result['platform'].lower()}"
    
    with st.container():
        st.markdown(f"""
        <div class="results-container">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                <span class="{platform_class}">{result['platform']}</span>
                <span class="{threat_class}">{result['threat_level']} ({result['threat_score']})</span>
            </div>
            
            <h4 style="margin: 0.5rem 0; color: #ffffff;">{result['title']}</h4>
            <p style="color: #cccccc; margin: 0.5rem 0;">{result['description']}</p>
            
            <div style="margin-top: 1rem;">
                <a href="{result['url']}" target="_blank" style="
                    background: linear-gradient(45deg, #667eea, #764ba2);
                    color: white;
                    padding: 0.5rem 1rem;
                    border-radius: 20px;
                    text-decoration: none;
                    font-weight: bold;
                    display: inline-block;
                    margin-right: 1rem;
                ">🔗 View Content</a>
        """, unsafe_allow_html=True)
        
        # Show matched keywords in expander
        if result['matched_keywords']:
            with st.expander("🔍 Analysis Details"):
                st.write("**Matched Threat Indicators:**")
                for keyword in result['matched_keywords']:
                    st.write(f"• {keyword}")
                
                if result['platform'] == 'YouTube':
                    st.write(f"**Channel:** {result['channel']}")
                    st.write(f"**Published:** {result['published']}")
                else:  # Reddit
                    st.write(f"**Subreddit:** r/{result['subreddit']}")
                    st.write(f"**Author:** {result['author']}")
                    st.write(f"**Score:** {result['score']} | **Comments:** {result['comments']}")
        
        st.markdown("</div></div>", unsafe_allow_html=True)

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🛡️ DHARMA PLATFORM</h1>
        <h2>Advanced Anti-Nationalist Content Detection System</h2>
        <p>Real-time monitoring across YouTube & Reddit platforms</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize detector
    detector = EnhancedThreatDetector()
    
    # Sidebar controls
    with st.sidebar:
        st.markdown("## 🎛️ Control Panel")
        
        # Search configuration
        st.markdown("### 🔍 Search Configuration")
        search_query = st.text_input(
            "Search Query",
            value="anti india propaganda",
            help="Enter keywords to search for potential threats"
        )
        
        max_results = st.slider("Max Results per Platform", 5, 50, 20)
        
        # Platform selection
        st.markdown("### 📱 Platforms")
        search_youtube = st.checkbox("YouTube", value=True)
        search_reddit = st.checkbox("Reddit", value=True)
        
        # Auto-refresh
        auto_refresh = st.checkbox("Auto Refresh (30s)", value=False)
        
        # Threat level filter
        st.markdown("### ⚠️ Threat Level Filter")
        show_critical = st.checkbox("Critical", value=True)
        show_high = st.checkbox("High", value=True)
        show_medium = st.checkbox("Medium", value=True)
        show_low = st.checkbox("Low", value=False)
    
    # Main search interface
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        if st.button("🔍 Start Detection Scan", type="primary"):
            st.session_state.search_triggered = True
    
    with col2:
        if st.button("🎯 Auto Detect"):
            st.session_state.auto_detect = True
    
    with col3:
        if st.button("🔄 Clear Results"):
            st.session_state.results = []
    
    # Auto-detect functionality
    if st.session_state.get('auto_detect', False):
        search_query = "anti india propaganda terrorism"
        st.session_state.search_triggered = True
        st.session_state.auto_detect = False
    
    # Search execution
    if st.session_state.get('search_triggered', False) or auto_refresh:
        with st.spinner("🔍 Scanning platforms for threats..."):
            all_results = []
            
            # Search YouTube
            if search_youtube and detector.youtube_api_key:
                with st.status("Searching YouTube...") as status:
                    youtube_results = asyncio.run(detector.search_youtube(search_query, max_results))
                    all_results.extend(youtube_results)
                    status.update(label=f"Found {len(youtube_results)} YouTube results", state="complete")
            
            # Search Reddit
            if search_reddit and detector.reddit:
                with st.status("Searching Reddit...") as status:
                    reddit_results = detector.search_reddit(search_query, max_results)
                    all_results.extend(reddit_results)
                    status.update(label=f"Found {len(reddit_results)} Reddit results", state="complete")
            
            # Filter results by threat level
            filtered_results = []
            for result in all_results:
                level = result['threat_level']
                if ((level == 'CRITICAL' and show_critical) or
                    (level == 'HIGH' and show_high) or
                    (level == 'MEDIUM' and show_medium) or
                    (level == 'LOW' and show_low)):
                    filtered_results.append(result)
            
            st.session_state.results = filtered_results
            st.session_state.search_triggered = False
    
    # Display results
    results = st.session_state.get('results', [])
    
    if results:
        # Summary metrics
        st.markdown("## 📊 Detection Summary")
        
        col1, col2, col3, col4 = st.columns(4)
        
        threat_counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        platform_counts = {}
        
        for result in results:
            threat_counts[result['threat_level']] += 1
            platform = result['platform']
            platform_counts[platform] = platform_counts.get(platform, 0) + 1
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h3 style="color: #ff4757;">🚨 Critical Threats</h3>
                <h2 style="color: #ff4757;">{threat_counts['CRITICAL']}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <h3 style="color: #ff6348;">⚠️ High Threats</h3>
                <h2 style="color: #ff6348;">{threat_counts['HIGH']}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <h3 style="color: #ffa502;">🔶 Medium Threats</h3>
                <h2 style="color: #ffa502;">{threat_counts['MEDIUM']}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <h3 style="color: #2ed573;">✅ Low Threats</h3>
                <h2 style="color: #2ed573;">{threat_counts['LOW']}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        # Charts
        st.markdown("## 📈 Analytics Dashboard")
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig1 = create_threat_level_chart(results)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            fig2 = create_platform_comparison_chart(results)
            st.plotly_chart(fig2, use_container_width=True)
        
        # Timeline chart
        fig3 = create_timeline_chart(results)
        if fig3.data:
            st.plotly_chart(fig3, use_container_width=True)
        
        # Results display
        st.markdown("## 🎯 Detection Results")
        
        # Sort options
        col1, col2 = st.columns([1, 3])
        with col1:
            sort_by = st.selectbox("Sort by", ["Threat Score", "Platform", "Date"])
        
        if sort_by == "Threat Score":
            results = sorted(results, key=lambda x: x['threat_score'], reverse=True)
        elif sort_by == "Platform":
            results = sorted(results, key=lambda x: x['platform'])
        
        # Display results
        for i, result in enumerate(results):
            display_result_card(result, i)
    
    else:
        st.markdown("""
        <div class="search-container">
            <h3>🔍 Ready to Scan</h3>
            <p>Click "Start Detection Scan" to begin monitoring for anti-nationalist content across platforms.</p>
            <p><strong>Platforms Available:</strong></p>
            <ul>
                <li>🎥 YouTube - Video content analysis</li>
                <li>🔴 Reddit - Discussion and post monitoring</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # Auto-refresh
    if auto_refresh:
        time.sleep(30)
        st.rerun()

if __name__ == "__main__":
    # Initialize session state
    if 'results' not in st.session_state:
        st.session_state.results = []
    
    main()