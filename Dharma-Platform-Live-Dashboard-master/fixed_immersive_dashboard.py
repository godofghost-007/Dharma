"""
🛡️ Dharma Platform - Fixed Ultra Immersive Dashboard
Plotly-compatible version with resolved property issues
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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
    page_title="🛡️ Dharma Platform - Ultra Immersive Detection",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Ultra Immersive CSS (same as before)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;400;500;600;700&display=swap');
    
    .stApp {
        background: linear-gradient(135deg, #0a0a0a 0%, #1a0033 25%, #000428 50%, #004e92 75%, #000428 100%);
        background-size: 400% 400%;
        animation: gradientShift 20s ease infinite;
        color: #ffffff;
        font-family: 'Rajdhani', sans-serif;
    }
    
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    .cyber-header {
        background: linear-gradient(45deg, #ff0080, #ff8c00, #40e0d0, #ff0080);
        background-size: 400% 400%;
        animation: holographic 8s ease infinite;
        padding: 3rem 2rem;
        border-radius: 20px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 
            0 0 30px rgba(255, 0, 128, 0.5),
            0 0 60px rgba(64, 224, 208, 0.3),
            inset 0 0 30px rgba(255, 255, 255, 0.1);
        border: 2px solid rgba(255, 255, 255, 0.2);
        position: relative;
        overflow: hidden;
    }
    
    @keyframes holographic {
        0%, 100% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
    }
    
    .cyber-title {
        font-family: 'Orbitron', monospace;
        font-size: 3.5rem;
        font-weight: 900;
        text-shadow: 
            0 0 10px #ff0080,
            0 0 20px #ff0080,
            0 0 30px #ff0080;
        margin: 0;
        letter-spacing: 3px;
    }
    
    .holo-card {
        background: linear-gradient(135deg, 
            rgba(255, 255, 255, 0.1) 0%,
            rgba(255, 255, 255, 0.05) 50%,
            rgba(255, 255, 255, 0.1) 100%);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 20px;
        padding: 2rem;
        margin: 1rem 0;
        box-shadow: 
            0 8px 32px rgba(0, 0, 0, 0.3),
            0 0 20px rgba(64, 224, 208, 0.2);
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }
    
    .holo-card:hover {
        transform: translateY(-10px) scale(1.02);
        box-shadow: 
            0 20px 40px rgba(0, 0, 0, 0.4),
            0 0 30px rgba(64, 224, 208, 0.4);
        border-color: rgba(64, 224, 208, 0.6);
    }
    
    .threat-critical {
        background: linear-gradient(45deg, #ff0040, #ff4081);
        color: white;
        padding: 0.8rem 1.5rem;
        border-radius: 30px;
        font-weight: bold;
        font-family: 'Orbitron', monospace;
        text-transform: uppercase;
        letter-spacing: 1px;
        box-shadow: 
            0 0 20px rgba(255, 0, 64, 0.6),
            inset 0 0 20px rgba(255, 255, 255, 0.1);
        animation: criticalPulse 1.5s ease-in-out infinite;
        border: 2px solid rgba(255, 0, 64, 0.8);
    }
    
    @keyframes criticalPulse {
        0%, 100% { 
            box-shadow: 0 0 20px rgba(255, 0, 64, 0.6);
            transform: scale(1);
        }
        50% { 
            box-shadow: 0 0 30px rgba(255, 0, 64, 0.9);
            transform: scale(1.05);
        }
    }
    
    .threat-high {
        background: linear-gradient(45deg, #ff6b35, #f7931e);
        color: white;
        padding: 0.8rem 1.5rem;
        border-radius: 30px;
        font-weight: bold;
        font-family: 'Orbitron', monospace;
        text-transform: uppercase;
        letter-spacing: 1px;
        box-shadow: 0 0 15px rgba(255, 107, 53, 0.5);
        border: 2px solid rgba(255, 107, 53, 0.6);
    }
    
    .threat-medium {
        background: linear-gradient(45deg, #ffa726, #ffcc02);
        color: #000;
        padding: 0.8rem 1.5rem;
        border-radius: 30px;
        font-weight: bold;
        font-family: 'Orbitron', monospace;
        text-transform: uppercase;
        letter-spacing: 1px;
        box-shadow: 0 0 15px rgba(255, 167, 38, 0.5);
        border: 2px solid rgba(255, 167, 38, 0.6);
    }
    
    .threat-low {
        background: linear-gradient(45deg, #4caf50, #8bc34a);
        color: white;
        padding: 0.8rem 1.5rem;
        border-radius: 30px;
        font-weight: bold;
        font-family: 'Orbitron', monospace;
        text-transform: uppercase;
        letter-spacing: 1px;
        box-shadow: 0 0 15px rgba(76, 175, 80, 0.5);
        border: 2px solid rgba(76, 175, 80, 0.6);
    }
    
    .platform-youtube {
        background: linear-gradient(45deg, #ff0000, #cc0000);
        color: white;
        padding: 0.5rem 1.2rem;
        border-radius: 25px;
        font-size: 0.9rem;
        font-weight: bold;
        font-family: 'Orbitron', monospace;
        text-transform: uppercase;
        letter-spacing: 1px;
        box-shadow: 0 0 15px rgba(255, 0, 0, 0.5);
        border: 2px solid rgba(255, 0, 0, 0.6);
    }
    
    .platform-reddit {
        background: linear-gradient(45deg, #ff4500, #ff6500);
        color: white;
        padding: 0.5rem 1.2rem;
        border-radius: 25px;
        font-size: 0.9rem;
        font-weight: bold;
        font-family: 'Orbitron', monospace;
        text-transform: uppercase;
        letter-spacing: 1px;
        box-shadow: 0 0 15px rgba(255, 69, 0, 0.5);
        border: 2px solid rgba(255, 69, 0, 0.6);
    }
    
    .stButton > button {
        background: linear-gradient(45deg, #00d4ff, #0099cc);
        color: white;
        border: 2px solid rgba(0, 212, 255, 0.6);
        border-radius: 30px;
        padding: 0.8rem 2rem;
        font-weight: bold;
        font-family: 'Orbitron', monospace;
        text-transform: uppercase;
        letter-spacing: 1px;
        transition: all 0.3s ease;
        box-shadow: 0 0 20px rgba(0, 212, 255, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 25px rgba(0, 212, 255, 0.5);
        background: linear-gradient(45deg, #0099cc, #00d4ff);
    }
    
    .metric-holo {
        background: linear-gradient(135deg, 
            rgba(255, 255, 255, 0.1) 0%,
            rgba(64, 224, 208, 0.1) 50%,
            rgba(255, 255, 255, 0.1) 100%);
        backdrop-filter: blur(15px);
        border: 2px solid rgba(64, 224, 208, 0.3);
        border-radius: 20px;
        padding: 2rem;
        text-align: center;
        transition: all 0.4s ease;
    }
    
    .metric-holo:hover {
        transform: scale(1.05);
        border-color: rgba(64, 224, 208, 0.6);
        box-shadow: 0 0 30px rgba(64, 224, 208, 0.4);
    }
    
    .metric-value {
        font-family: 'Orbitron', monospace;
        font-size: 3rem;
        font-weight: 900;
        margin: 1rem 0;
        text-shadow: 0 0 10px currentColor;
    }
    
    .metric-label {
        font-family: 'Orbitron', monospace;
        font-size: 1.2rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 2px;
        opacity: 0.9;
    }
    
    .results-container {
        background: linear-gradient(135deg, 
            rgba(0, 0, 0, 0.6) 0%,
            rgba(20, 20, 40, 0.6) 100%);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 2rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

class FixedThreatDetector:
    def __init__(self):
        self.youtube_api_key = st.secrets.get("YOUTUBE_API_KEY", "")
        
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

    def calculate_threat_score(self, text: str) -> tuple:
        """Calculate threat score and level"""
        text_lower = text.lower()
        score = 0
        matched_keywords = []
        
        # Check critical keywords
        for keyword in self.threat_keywords['critical']:
            if keyword in text_lower:
                score += 15
                matched_keywords.append(f"🚨 CRITICAL: {keyword}")
        
        # Check high keywords
        for keyword in self.threat_keywords['high']:
            if keyword in text_lower:
                score += 10
                matched_keywords.append(f"⚠️ HIGH: {keyword}")
        
        # Check medium keywords
        for keyword in self.threat_keywords['medium']:
            if keyword in text_lower:
                score += 6
                matched_keywords.append(f"🔶 MEDIUM: {keyword}")
        
        # Sentiment analysis
        try:
            blob = TextBlob(text)
            sentiment = blob.sentiment.polarity
            if sentiment < -0.5:
                score += 5
                matched_keywords.append("😡 SENTIMENT: Extremely negative")
            elif sentiment < -0.2:
                score += 3
                matched_keywords.append("😠 SENTIMENT: Negative")
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
        
        return score, level, matched_keywords

    def search_youtube(self, query: str, max_results: int = 15) -> List[Dict]:
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
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
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
                        'description': description[:300] + "..." if len(description) > 300 else description,
                        'url': f"https://www.youtube.com/watch?v={item['id']['videoId']}",
                        'thumbnail': snippet['thumbnails']['medium']['url'],
                        'channel': snippet['channelTitle'],
                        'published': snippet['publishedAt'],
                        'threat_score': score,
                        'threat_level': level,
                        'matched_keywords': keywords
                    })
                
                return sorted(results, key=lambda x: x['threat_score'], reverse=True)
            else:
                st.error(f"YouTube API error: {response.status_code}")
                return []
            
        except Exception as e:
            st.error(f"YouTube search error: {e}")
            return []

    def search_reddit(self, query: str, max_results: int = 15) -> List[Dict]:
        """Search Reddit using public JSON API"""
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
                            score, level, keywords = self.calculate_threat_score(combined_text)
                            
                            results.append({
                                'platform': 'Reddit',
                                'title': post_data['title'],
                                'description': post_data.get('selftext', '')[:300] + "..." if len(post_data.get('selftext', '')) > 300 else post_data.get('selftext', ''),
                                'url': f"https://reddit.com{post_data['permalink']}",
                                'subreddit': post_data['subreddit'],
                                'author': post_data.get('author', '[deleted]'),
                                'score': post_data.get('score', 0),
                                'comments': post_data.get('num_comments', 0),
                                'created': datetime.fromtimestamp(post_data['created_utc']).isoformat(),
                                'threat_score': score,
                                'threat_level': level,
                                'matched_keywords': keywords
                            })
                
                except Exception:
                    continue
            
            return sorted(results, key=lambda x: x['threat_score'], reverse=True)[:max_results]
            
        except Exception as e:
            st.error(f"Reddit search error: {e}")
            return []

def create_fixed_threat_chart(results: List[Dict]) -> go.Figure:
    """Create fixed threat visualization chart"""
    threat_counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0, 'MINIMAL': 0}
    
    for result in results:
        threat_counts[result['threat_level']] += 1
    
    fig = go.Figure()
    
    colors = ['#ff0040', '#ff6348', '#ffa502', '#4caf50', '#2196f3']
    
    fig.add_trace(go.Bar(
        x=list(threat_counts.keys()),
        y=list(threat_counts.values()),
        marker=dict(
            color=colors,
            line=dict(color='rgba(255,255,255,0.8)', width=2)
        ),
        text=list(threat_counts.values()),
        textposition='auto',
        textfont=dict(size=14, color='white', family='Orbitron'),
        hovertemplate='<b>%{x}</b><br>Count: %{y}<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(
            text="🛡️ Threat Level Distribution",
            font=dict(size=24, color='white', family='Orbitron'),
            x=0.5
        ),
        xaxis=dict(
            title=dict(text="Threat Level", font=dict(size=16, color='white', family='Orbitron')),
            tickfont=dict(size=14, color='white', family='Orbitron'),
            gridcolor='rgba(255,255,255,0.2)'
        ),
        yaxis=dict(
            title=dict(text="Count", font=dict(size=16, color='white', family='Orbitron')),
            tickfont=dict(size=14, color='white', family='Orbitron'),
            gridcolor='rgba(255,255,255,0.2)'
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='white'
    )
    
    return fig

def create_platform_comparison(results: List[Dict]) -> go.Figure:
    """Create platform comparison chart"""
    youtube_data = [r for r in results if r['platform'] == 'YouTube']
    reddit_data = [r for r in results if r['platform'] == 'Reddit']
    
    categories = ['Critical', 'High', 'Medium', 'Low', 'Total']
    
    youtube_values = [
        len([r for r in youtube_data if r['threat_level'] == 'CRITICAL']),
        len([r for r in youtube_data if r['threat_level'] == 'HIGH']),
        len([r for r in youtube_data if r['threat_level'] == 'MEDIUM']),
        len([r for r in youtube_data if r['threat_level'] == 'LOW']),
        len(youtube_data)
    ]
    
    reddit_values = [
        len([r for r in reddit_data if r['threat_level'] == 'CRITICAL']),
        len([r for r in reddit_data if r['threat_level'] == 'HIGH']),
        len([r for r in reddit_data if r['threat_level'] == 'MEDIUM']),
        len([r for r in reddit_data if r['threat_level'] == 'LOW']),
        len(reddit_data)
    ]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=youtube_values,
        theta=categories,
        fill='toself',
        name='YouTube',
        line_color='#ff0000',
        fillcolor='rgba(255,0,0,0.3)'
    ))
    
    fig.add_trace(go.Scatterpolar(
        r=reddit_values,
        theta=categories,
        fill='toself',
        name='Reddit',
        line_color='#ff4500',
        fillcolor='rgba(255,69,0,0.3)'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, max(max(youtube_values), max(reddit_values)) + 1] if youtube_values or reddit_values else [0, 1],
                color='white'
            ),
            angularaxis=dict(color='white')
        ),
        showlegend=True,
        title=dict(
            text="🎯 Platform Threat Comparison",
            font=dict(size=20, color='white', family='Orbitron'),
            x=0.5
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='white'
    )
    
    return fig

def display_result_card(result: Dict, index: int):
    """Display result card"""
    threat_class = f"threat-{result['threat_level'].lower()}"
    platform_class = f"platform-{result['platform'].lower()}"
    
    threat_colors = {
        'CRITICAL': '#ff0040',
        'HIGH': '#ff6348',
        'MEDIUM': '#ffa502',
        'LOW': '#4caf50',
        'MINIMAL': '#2196f3'
    }
    
    threat_color = threat_colors.get(result['threat_level'], '#ffffff')
    
    with st.container():
        st.markdown(f"""
        <div class="results-container" style="border-left: 4px solid {threat_color};">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                <span class="{platform_class}">{result['platform']}</span>
                <span class="{threat_class}">{result['threat_level']} ({result['threat_score']})</span>
            </div>
            
            <h3 style="margin: 1rem 0; color: #ffffff; font-family: 'Rajdhani', sans-serif; font-weight: 600;">
                {result['title']}
            </h3>
            
            <p style="color: #cccccc; margin: 1rem 0; line-height: 1.6;">
                {result['description']}
            </p>
            
            <div style="margin: 1.5rem 0;">
                <a href="{result['url']}" target="_blank" style="
                    background: linear-gradient(45deg, #00d4ff, #0099cc);
                    color: white;
                    padding: 0.8rem 1.5rem;
                    border-radius: 25px;
                    text-decoration: none;
                    font-weight: bold;
                    font-family: 'Orbitron', monospace;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    box-shadow: 0 0 15px rgba(0, 212, 255, 0.3);
                    border: 2px solid rgba(0, 212, 255, 0.6);
                ">🔗 Analyze Content</a>
            </div>
        """, unsafe_allow_html=True)
        
        # Platform-specific information
        if result['platform'] == 'YouTube':
            col1, col2 = st.columns(2)
            with col1:
                st.metric("📺 Channel", result['channel'])
            with col2:
                st.metric("📅 Published", result['published'][:10])
        else:  # Reddit
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("⬆️ Score", result['score'])
            with col2:
                st.metric("💬 Comments", result['comments'])
            with col3:
                st.metric("📍 Subreddit", f"r/{result['subreddit']}")
        
        # Threat analysis details
        if result['matched_keywords']:
            with st.expander("🔍 **Threat Analysis Details**", expanded=False):
                st.markdown("**🎯 Detected Threat Indicators:**")
                for keyword in result['matched_keywords']:
                    st.markdown(f"• {keyword}")
        
        st.markdown("</div>", unsafe_allow_html=True)

def main():
    # Initialize session state
    if 'results' not in st.session_state:
        st.session_state.results = []
    if 'search_performed' not in st.session_state:
        st.session_state.search_performed = False
    
    # Cyber Header
    st.markdown("""
    <div class="cyber-header">
        <h1 class="cyber-title">🛡️ DHARMA PLATFORM</h1>
        <h2 style="font-family: 'Orbitron', monospace; font-size: 1.5rem; margin: 1rem 0; opacity: 0.9;">
            ULTRA IMMERSIVE THREAT DETECTION SYSTEM
        </h2>
        <p style="font-family: 'Rajdhani', sans-serif; font-size: 1.2rem; margin: 0; opacity: 0.8;">
            Advanced Multi-Platform Intelligence • Real-Time Analysis • Neural Threat Detection
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize detector
    detector = FixedThreatDetector()
    
    # Sidebar Control Panel
    with st.sidebar:
        st.markdown("## 🎛️ Control Matrix")
        
        # API Status
        st.markdown("### 🔌 System Status")
        youtube_status = "🟢 ONLINE" if detector.youtube_api_key else "🔴 OFFLINE"
        reddit_status = "🟢 ONLINE"
        
        st.markdown(f"""
        <div style="font-family: 'Orbitron', monospace;">
            <p>YouTube API: {youtube_status}</p>
            <p>Reddit API: {reddit_status}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Search Configuration
        st.markdown("### 🔍 Search Parameters")
        search_query = st.text_input(
            "Target Query",
            value="anti india propaganda",
            help="Enter keywords for threat detection scan"
        )
        
        max_results = st.slider("Results Per Platform", 5, 25, 15)
        
        # Platform Selection
        st.markdown("### 📡 Platform Matrix")
        search_youtube = st.checkbox("🎥 YouTube Scanner", value=True)
        search_reddit = st.checkbox("🔴 Reddit Monitor", value=True)
        
        # Threat Filters
        st.markdown("### ⚠️ Threat Filters")
        show_critical = st.checkbox("🚨 Critical", value=True)
        show_high = st.checkbox("⚠️ High", value=True)
        show_medium = st.checkbox("🔶 Medium", value=True)
        show_low = st.checkbox("✅ Low", value=True)
        show_minimal = st.checkbox("ℹ️ Minimal", value=False)
    
    # Main Search Interface
    col1, col2, col3 = st.columns([3, 2, 2])
    
    with col1:
        if st.button("🚀 **INITIATE DEEP SCAN**", type="primary", key="main_search"):
            with st.spinner("🔍 **SCANNING THREAT MATRIX...**"):
                all_results = []
                
                # Search YouTube
                if search_youtube and detector.youtube_api_key:
                    with st.status("🎥 **Analyzing YouTube Vectors...**") as status:
                        youtube_results = detector.search_youtube(search_query, max_results)
                        all_results.extend(youtube_results)
                        status.update(label=f"✅ **YouTube: {len(youtube_results)} threats detected**", state="complete")
                
                # Search Reddit
                if search_reddit:
                    with st.status("🔴 **Scanning Reddit Networks...**") as status:
                        reddit_results = detector.search_reddit(search_query, max_results)
                        all_results.extend(reddit_results)
                        status.update(label=f"✅ **Reddit: {len(reddit_results)} threats detected**", state="complete")
                
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
                
                st.success(f"✅ **SCAN COMPLETE** • {len(filtered_results)} THREATS IDENTIFIED")
    
    with col2:
        if st.button("🎯 **AUTO DETECT**", key="auto_detect"):
            with st.spinner("🎯 **EXECUTING AUTO-DETECTION...**"):
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
                
                st.success(f"🎯 **AUTO-DETECTION COMPLETE** • {len(filtered_results)} threats identified")
    
    with col3:
        if st.button("🔄 **RESET MATRIX**", key="clear_results"):
            st.session_state.results = []
            st.session_state.search_performed = False
            st.success("✅ **MATRIX RESET COMPLETE**")
    
    # Display Results
    results = st.session_state.results
    
    if results and st.session_state.search_performed:
        # Summary Dashboard
        st.markdown("""
        <div style="margin: 3rem 0 2rem 0;">
            <h2 style="font-family: 'Orbitron', monospace; color: #40e0d0; text-align: center; font-size: 2.5rem;">
                📊 THREAT INTELLIGENCE DASHBOARD
            </h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Metrics Row
        col1, col2, col3, col4, col5 = st.columns(5)
        
        threat_counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0, 'MINIMAL': 0}
        total_threat_score = 0
        
        for result in results:
            threat_counts[result['threat_level']] += 1
            total_threat_score += result['threat_score']
        
        avg_threat_score = total_threat_score / len(results) if results else 0
        
        with col1:
            st.markdown(f"""
            <div class="metric-holo" style="border-color: #ff0040;">
                <div class="metric-value" style="color: #ff0040;">{threat_counts['CRITICAL']}</div>
                <div class="metric-label">🚨 Critical</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-holo" style="border-color: #ff6348;">
                <div class="metric-value" style="color: #ff6348;">{threat_counts['HIGH']}</div>
                <div class="metric-label">⚠️ High</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-holo" style="border-color: #ffa502;">
                <div class="metric-value" style="color: #ffa502;">{threat_counts['MEDIUM']}</div>
                <div class="metric-label">🔶 Medium</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-holo" style="border-color: #4caf50;">
                <div class="metric-value" style="color: #4caf50;">{threat_counts['LOW']}</div>
                <div class="metric-label">✅ Low</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col5:
            st.markdown(f"""
            <div class="metric-holo" style="border-color: #40e0d0;">
                <div class="metric-value" style="color: #40e0d0;">{avg_threat_score:.1f}</div>
                <div class="metric-label">📊 Avg Score</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Analytics Charts
        st.markdown("""
        <div style="margin: 3rem 0 2rem 0;">
            <h3 style="font-family: 'Orbitron', monospace; color: #40e0d0; text-align: center; font-size: 2rem;">
                📈 ADVANCED ANALYTICS MATRIX
            </h3>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig1 = create_fixed_threat_chart(results)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            fig2 = create_platform_comparison(results)
            st.plotly_chart(fig2, use_container_width=True)
        
        # Results Display
        st.markdown("""
        <div style="margin: 3rem 0 2rem 0;">
            <h3 style="font-family: 'Orbitron', monospace; color: #40e0d0; text-align: center; font-size: 2rem;">
                🎯 THREAT DETECTION RESULTS
            </h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Sort options
        col1, col2 = st.columns([2, 4])
        with col1:
            sort_by = st.selectbox("🔄 Sort By", ["Threat Score", "Platform", "Date"])
        
        # Sort results
        if sort_by == "Threat Score":
            results = sorted(results, key=lambda x: x['threat_score'], reverse=True)
        elif sort_by == "Platform":
            results = sorted(results, key=lambda x: x['platform'])
        elif sort_by == "Date":
            results = sorted(results, key=lambda x: x.get('published', x.get('created', '')), reverse=True)
        
        # Display results
        for i, result in enumerate(results):
            display_result_card(result, i)
    
    elif st.session_state.search_performed and not results:
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, rgba(255, 193, 7, 0.2), rgba(255, 193, 7, 0.1));
            border: 2px solid #ffc107;
            border-radius: 20px;
            padding: 2rem;
            text-align: center;
            font-family: 'Orbitron', monospace;
            color: #ffc107;
            margin: 2rem 0;
        ">
            <h3>🔍 NO THREATS DETECTED</h3>
            <p>Current filters may be too restrictive. Try adjusting threat level filters or search terms.</p>
        </div>
        """, unsafe_allow_html=True)
    
    else:
        # Welcome Interface
        st.markdown("""
        <div class="holo-card" style="text-align: center; margin: 3rem 0;">
            <h3 style="font-family: 'Orbitron', monospace; color: #40e0d0; font-size: 2rem; margin-bottom: 2rem;">
                🛡️ THREAT DETECTION SYSTEM READY
            </h3>
            
            <p style="font-size: 1.2rem; line-height: 1.8; margin-bottom: 2rem;">
                Advanced multi-platform intelligence system ready for deployment.<br>
                Click <strong>"INITIATE DEEP SCAN"</strong> to begin threat analysis.
            </p>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; margin-top: 2rem;">
                <div style="
                    background: linear-gradient(135deg, rgba(255, 0, 0, 0.1), rgba(255, 0, 0, 0.05));
                    border: 2px solid rgba(255, 0, 0, 0.3);
                    border-radius: 15px;
                    padding: 1.5rem;
                ">
                    <h4 style="color: #ff0000; font-family: 'Orbitron', monospace;">🎥 YOUTUBE SCANNER</h4>
                    <p>Advanced video content analysis with engagement metrics</p>
                </div>
                
                <div style="
                    background: linear-gradient(135deg, rgba(255, 69, 0, 0.1), rgba(255, 69, 0, 0.05));
                    border: 2px solid rgba(255, 69, 0, 0.3);
                    border-radius: 15px;
                    padding: 1.5rem;
                ">
                    <h4 style="color: #ff4500; font-family: 'Orbitron', monospace;">🔴 REDDIT MONITOR</h4>
                    <p>Real-time discussion and post monitoring across subreddits</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()