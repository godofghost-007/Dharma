"""
🛡️ Dharma Platform - Ultra Immersive Multi-Platform Dashboard
Advanced real-time monitoring with YouTube and Reddit integration
Next-generation UI/UX with immersive design elements
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
import base64

# Page Configuration
st.set_page_config(
    page_title="🛡️ Dharma Platform - Ultra Immersive Detection",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Ultra Immersive CSS with Advanced Animations
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;400;500;600;700&display=swap');
    
    /* Global Dark Theme */
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
    
    /* Cyber Header with Holographic Effect */
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
    
    .cyber-header::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: linear-gradient(45deg, transparent, rgba(255, 255, 255, 0.1), transparent);
        animation: scan 3s linear infinite;
    }
    
    @keyframes holographic {
        0%, 100% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
    }
    
    @keyframes scan {
        0% { transform: translateX(-100%) translateY(-100%) rotate(45deg); }
        100% { transform: translateX(100%) translateY(100%) rotate(45deg); }
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
    
    .cyber-subtitle {
        font-family: 'Orbitron', monospace;
        font-size: 1.5rem;
        font-weight: 400;
        margin: 1rem 0;
        opacity: 0.9;
        letter-spacing: 2px;
    }
    
    /* Holographic Cards */
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
        position: relative;
        overflow: hidden;
    }
    
    .holo-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
        transition: left 0.5s;
    }
    
    .holo-card:hover {
        transform: translateY(-10px) scale(1.02);
        box-shadow: 
            0 20px 40px rgba(0, 0, 0, 0.4),
            0 0 30px rgba(64, 224, 208, 0.4);
        border-color: rgba(64, 224, 208, 0.6);
    }
    
    .holo-card:hover::before {
        left: 100%;
    }
    
    /* Neon Threat Indicators */
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
    
    /* Platform Badges with Glow */
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
        animation: youtubeGlow 2s ease-in-out infinite alternate;
    }
    
    @keyframes youtubeGlow {
        from { box-shadow: 0 0 15px rgba(255, 0, 0, 0.5); }
        to { box-shadow: 0 0 25px rgba(255, 0, 0, 0.8); }
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
        animation: redditGlow 2s ease-in-out infinite alternate;
    }
    
    @keyframes redditGlow {
        from { box-shadow: 0 0 15px rgba(255, 69, 0, 0.5); }
        to { box-shadow: 0 0 25px rgba(255, 69, 0, 0.8); }
    }
    
    /* Cyber Buttons */
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
    
    /* Metric Cards with Holographic Effect */
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
        position: relative;
        overflow: hidden;
    }
    
    .metric-holo::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: conic-gradient(transparent, rgba(64, 224, 208, 0.1), transparent);
        animation: rotate 4s linear infinite;
    }
    
    @keyframes rotate {
        100% { transform: rotate(360deg); }
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
        position: relative;
        z-index: 1;
    }
    
    .metric-label {
        font-family: 'Orbitron', monospace;
        font-size: 1.2rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 2px;
        opacity: 0.9;
        position: relative;
        z-index: 1;
    }
    
    /* Control Panel Styling */
    .control-panel {
        background: linear-gradient(135deg, 
            rgba(0, 0, 0, 0.8) 0%,
            rgba(20, 20, 40, 0.8) 100%);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(64, 224, 208, 0.3);
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    
    /* Search Interface */
    .search-interface {
        background: linear-gradient(135deg, 
            rgba(255, 255, 255, 0.05) 0%,
            rgba(64, 224, 208, 0.05) 100%);
        backdrop-filter: blur(15px);
        border: 2px solid rgba(64, 224, 208, 0.2);
        border-radius: 20px;
        padding: 2rem;
        margin: 2rem 0;
        position: relative;
    }
    
    .search-interface::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, #40e0d0, transparent);
        animation: searchScan 2s linear infinite;
    }
    
    @keyframes searchScan {
        0% { transform: translateX(-100%); }
        100% { transform: translateX(100%); }
    }
    
    /* Results Container */
    .results-container {
        background: linear-gradient(135deg, 
            rgba(0, 0, 0, 0.6) 0%,
            rgba(20, 20, 40, 0.6) 100%);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 2rem;
        margin: 1rem 0;
        position: relative;
        overflow: hidden;
    }
    
    .results-container::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(45deg, 
            rgba(64, 224, 208, 0.05) 0%,
            transparent 50%,
            rgba(255, 0, 128, 0.05) 100%);
        pointer-events: none;
    }
    
    /* Sidebar Styling */
    .css-1d391kg {
        background: linear-gradient(180deg, 
            rgba(0, 0, 0, 0.9) 0%,
            rgba(20, 20, 40, 0.9) 100%);
        backdrop-filter: blur(20px);
        border-right: 2px solid rgba(64, 224, 208, 0.2);
    }
    
    /* Loading Animation */
    .loading-cyber {
        display: inline-block;
        width: 40px;
        height: 40px;
        border: 3px solid rgba(64, 224, 208, 0.3);
        border-radius: 50%;
        border-top-color: #40e0d0;
        animation: spin 1s ease-in-out infinite;
    }
    
    @keyframes spin {
        to { transform: rotate(360deg); }
    }
    
    /* Status Indicators */
    .status-online {
        color: #4caf50;
        text-shadow: 0 0 10px #4caf50;
        animation: statusPulse 2s ease-in-out infinite;
    }
    
    .status-offline {
        color: #f44336;
        text-shadow: 0 0 10px #f44336;
    }
    
    @keyframes statusPulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.6; }
    }
    
    /* Scrollbar Styling */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(0, 0, 0, 0.3);
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, #40e0d0, #0099cc);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(180deg, #0099cc, #40e0d0);
    }
</style>
""", unsafe_allow_html=True)

class UltraImmersiveThreatDetector:
    def __init__(self):
        self.youtube_api_key = st.secrets.get("YOUTUBE_API_KEY", "")
        
        # Enhanced threat keywords with categories
        self.threat_keywords = {
            'critical': [
                'anti india', 'anti-india', 'destroy india', 'break india',
                'india terrorist', 'hindu terrorist', 'modi terrorist',
                'kashmir independence', 'khalistan', 'separate kashmir',
                'india occupation', 'indian army crimes', 'genocide india',
                'bomb india', 'attack india', 'kill indians'
            ],
            'high': [
                'india bad', 'india evil', 'india problem', 'hate india',
                'india fascist', 'india nazi', 'bjp terrorist', 'rss terrorist',
                'india fake', 'india lies', 'boycott india', 'stop india',
                'india oppressor', 'indian brutality', 'india violence'
            ],
            'medium': [
                'india issues', 'india problems', 'india criticism',
                'india negative', 'india wrong', 'india mistake',
                'india controversy', 'india dispute', 'india conflict',
                'india bias', 'indian propaganda', 'india manipulation'
            ]
        }
        
        # Advanced sentiment patterns
        self.negative_patterns = [
            r'\b(hate|destroy|kill|bomb|attack|terror|eliminate)\b.*\b(india|indian|hindu|modi)\b',
            r'\b(india|indian|hindu|modi)\b.*\b(bad|evil|worst|terrible|awful|disgusting)\b',
            r'\b(fake|false|lie|propaganda|manipulation)\b.*\b(india|indian)\b',
            r'\b(boycott|ban|stop|end)\b.*\b(india|indian)\b',
            r'\b(india|indian)\b.*\b(oppressor|fascist|nazi|terrorist)\b'
        ]

    def calculate_threat_score(self, text: str) -> tuple:
        """Advanced threat scoring with multiple factors"""
        text_lower = text.lower()
        score = 0
        matched_keywords = []
        threat_factors = []
        
        # Check critical keywords (highest weight)
        for keyword in self.threat_keywords['critical']:
            if keyword in text_lower:
                score += 15
                matched_keywords.append(f"🚨 CRITICAL: {keyword}")
                threat_factors.append("Direct threat language")
        
        # Check high keywords
        for keyword in self.threat_keywords['high']:
            if keyword in text_lower:
                score += 10
                matched_keywords.append(f"⚠️ HIGH: {keyword}")
                threat_factors.append("Hostile language")
        
        # Check medium keywords
        for keyword in self.threat_keywords['medium']:
            if keyword in text_lower:
                score += 6
                matched_keywords.append(f"🔶 MEDIUM: {keyword}")
                threat_factors.append("Negative sentiment")
        
        # Advanced pattern matching
        for pattern in self.negative_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                score += 8
                matched_keywords.append(f"🎯 PATTERN: Advanced threat pattern detected")
                threat_factors.append("Structured threat pattern")
        
        # Sentiment analysis with TextBlob
        try:
            blob = TextBlob(text)
            sentiment = blob.sentiment.polarity
            subjectivity = blob.sentiment.subjectivity
            
            if sentiment < -0.7:
                score += 5
                matched_keywords.append("😡 SENTIMENT: Extremely negative")
                threat_factors.append("Extreme negativity")
            elif sentiment < -0.4:
                score += 3
                matched_keywords.append("😠 SENTIMENT: Highly negative")
                threat_factors.append("High negativity")
            elif sentiment < -0.1:
                score += 1
                matched_keywords.append("😐 SENTIMENT: Negative")
                threat_factors.append("Negative tone")
            
            # High subjectivity with negative sentiment is more concerning
            if subjectivity > 0.7 and sentiment < -0.3:
                score += 2
                matched_keywords.append("🎭 SUBJECTIVITY: Highly opinionated negative content")
                threat_factors.append("Opinionated negativity")
                
        except Exception:
            pass
        
        # Keyword density analysis
        total_words = len(text.split())
        if total_words > 0:
            threat_word_count = sum(1 for word in text_lower.split() 
                                  if any(keyword.split()[0] in word for keywords in self.threat_keywords.values() 
                                        for keyword in keywords))
            threat_density = threat_word_count / total_words
            
            if threat_density > 0.1:  # More than 10% threat words
                score += 4
                matched_keywords.append(f"📊 DENSITY: High threat word density ({threat_density:.1%})")
                threat_factors.append("High threat density")
        
        # Determine threat level with more granular scoring
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
        
        return score, level, matched_keywords, threat_factors

    def search_youtube(self, query: str, max_results: int = 15) -> List[Dict]:
        """Enhanced YouTube search with detailed analysis"""
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
                'publishedAfter': (datetime.now() - timedelta(days=60)).isoformat() + 'Z'
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
                    
                    score, level, keywords, factors = self.calculate_threat_score(combined_text)
                    
                    # Get video statistics if available
                    video_id = item['id']['videoId']
                    stats = self.get_video_stats(video_id)
                    
                    results.append({
                        'platform': 'YouTube',
                        'title': title,
                        'description': description[:300] + "..." if len(description) > 300 else description,
                        'url': f"https://www.youtube.com/watch?v={video_id}",
                        'thumbnail': snippet['thumbnails']['high']['url'] if 'high' in snippet['thumbnails'] else snippet['thumbnails']['medium']['url'],
                        'channel': snippet['channelTitle'],
                        'published': snippet['publishedAt'],
                        'threat_score': score,
                        'threat_level': level,
                        'matched_keywords': keywords,
                        'threat_factors': factors,
                        'stats': stats,
                        'video_id': video_id
                    })
                
                return sorted(results, key=lambda x: x['threat_score'], reverse=True)
            else:
                st.error(f"YouTube API error: {response.status_code}")
                return []
            
        except Exception as e:
            st.error(f"YouTube search error: {e}")
            return []

    def get_video_stats(self, video_id: str) -> Dict:
        """Get video statistics"""
        try:
            url = "https://www.googleapis.com/youtube/v3/videos"
            params = {
                'part': 'statistics',
                'id': video_id,
                'key': self.youtube_api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('items'):
                    stats = data['items'][0]['statistics']
                    return {
                        'views': int(stats.get('viewCount', 0)),
                        'likes': int(stats.get('likeCount', 0)),
                        'comments': int(stats.get('commentCount', 0))
                    }
        except Exception:
            pass
        
        return {'views': 0, 'likes': 0, 'comments': 0}

    def search_reddit(self, query: str, max_results: int = 15) -> List[Dict]:
        """Enhanced Reddit search using public JSON API"""
        try:
            results = []
            
            # Search multiple subreddits
            subreddits = ['india', 'worldnews', 'news', 'politics', 'IndiaSpeaks', 'unitedstatesofindia', 'geopolitics']
            
            for subreddit in subreddits:
                try:
                    url = f"https://www.reddit.com/r/{subreddit}/search.json"
                    params = {
                        'q': query,
                        'sort': 'new',
                        't': 'month',
                        'limit': max_results // len(subreddits) + 2
                    }
                    
                    headers = {'User-Agent': 'DharmaDetector/2.0'}
                    response = requests.get(url, params=params, headers=headers, timeout=15)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        for post in data.get('data', {}).get('children', []):
                            post_data = post['data']
                            combined_text = f"{post_data['title']} {post_data.get('selftext', '')}"
                            score, level, keywords, factors = self.calculate_threat_score(combined_text)
                            
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
                                'matched_keywords': keywords,
                                'threat_factors': factors,
                                'upvote_ratio': post_data.get('upvote_ratio', 0.5)
                            })
                
                except Exception:
                    continue
            
            return sorted(results, key=lambda x: x['threat_score'], reverse=True)[:max_results]
            
        except Exception as e:
            st.error(f"Reddit search error: {e}")
            return []

def create_advanced_threat_chart(results: List[Dict]) -> go.Figure:
    """Create advanced 3D threat visualization"""
    threat_counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0, 'MINIMAL': 0}
    platform_data = {'YouTube': {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0, 'MINIMAL': 0},
                     'Reddit': {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0, 'MINIMAL': 0}}
    
    for result in results:
        threat_counts[result['threat_level']] += 1
        platform_data[result['platform']][result['threat_level']] += 1
    
    fig = go.Figure()
    
    # Add bars with gradient colors
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

def create_platform_radar_chart(results: List[Dict]) -> go.Figure:
    """Create radar chart comparing platforms"""
    youtube_data = [r for r in results if r['platform'] == 'YouTube']
    reddit_data = [r for r in results if r['platform'] == 'Reddit']
    
    categories = ['Critical', 'High', 'Medium', 'Low', 'Total Posts']
    
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
                range=[0, max(max(youtube_values), max(reddit_values)) + 1],
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

def create_timeline_heatmap(results: List[Dict]) -> go.Figure:
    """Create timeline heatmap of threats"""
    if not results:
        return go.Figure()
    
    # Prepare data for heatmap
    timeline_data = []
    for result in results:
        if result['platform'] == 'YouTube':
            date = pd.to_datetime(result['published']).date()
        else:  # Reddit
            date = pd.to_datetime(result['created']).date()
        
        timeline_data.append({
            'date': date,
            'platform': result['platform'],
            'threat_score': result['threat_score'],
            'threat_level': result['threat_level']
        })
    
    df = pd.DataFrame(timeline_data)
    
    if df.empty:
        return go.Figure()
    
    # Create pivot table for heatmap
    pivot_df = df.pivot_table(
        values='threat_score', 
        index='platform', 
        columns='date', 
        aggfunc='mean',
        fill_value=0
    )
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot_df.values,
        x=pivot_df.columns,
        y=pivot_df.index,
        colorscale='Reds',
        hoverongaps=False,
        colorbar=dict(title="Threat Score", titlefont=dict(color='white'), tickfont=dict(color='white'))
    ))
    
    fig.update_layout(
        title=dict(
            text="📅 Threat Timeline Heatmap",
            font=dict(size=20, color='white', family='Orbitron'),
            x=0.5
        ),
        xaxis=dict(title=dict(text="Date", font=dict(color='white'))),
        yaxis=dict(title=dict(text="Platform", font=dict(color='white'))),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='white'
    )
    
    return fig

def display_ultra_result_card(result: Dict, index: int):
    """Display ultra-immersive result card"""
    threat_class = f"threat-{result['threat_level'].lower()}"
    platform_class = f"platform-{result['platform'].lower()}"
    
    # Threat level colors
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
            
            <div style="display: flex; gap: 1rem; margin: 1.5rem 0; flex-wrap: wrap;">
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
                    transition: all 0.3s ease;
                ">🔗 Analyze Content</a>
        """, unsafe_allow_html=True)
        
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
        
        # Threat analysis details
        if result['matched_keywords'] or result['threat_factors']:
            with st.expander("🔍 **Advanced Threat Analysis**", expanded=False):
                if result['matched_keywords']:
                    st.markdown("**🎯 Detected Threat Indicators:**")
                    for keyword in result['matched_keywords']:
                        st.markdown(f"• {keyword}")
                
                if result['threat_factors']:
                    st.markdown("**⚡ Threat Factors:**")
                    for factor in result['threat_factors']:
                        st.markdown(f"• {factor}")
                
                # Additional metadata
                st.markdown("**📊 Content Metadata:**")
                if result['platform'] == 'YouTube':
                    st.markdown(f"• **Published:** {result['published']}")
                    st.markdown(f"• **Channel:** {result['channel']}")
                else:
                    st.markdown(f"• **Posted:** {result['created']}")
                    st.markdown(f"• **Author:** {result['author']}")
                    st.markdown(f"• **Subreddit:** r/{result['subreddit']}")
        
        st.markdown("</div>", unsafe_allow_html=True)

def main():
    # Initialize session state
    if 'results' not in st.session_state:
        st.session_state.results = []
    if 'search_performed' not in st.session_state:
        st.session_state.search_performed = False
    if 'last_search_query' not in st.session_state:
        st.session_state.last_search_query = ""
    
    # Cyber Header
    st.markdown("""
    <div class="cyber-header">
        <h1 class="cyber-title">🛡️ DHARMA PLATFORM</h1>
        <h2 class="cyber-subtitle">ULTRA IMMERSIVE THREAT DETECTION SYSTEM</h2>
        <p style="font-family: 'Rajdhani', sans-serif; font-size: 1.2rem; margin: 0; opacity: 0.8;">
            Advanced Multi-Platform Intelligence • Real-Time Analysis • Neural Threat Detection
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize detector
    detector = UltraImmersiveThreatDetector()
    
    # Sidebar Control Panel
    with st.sidebar:
        st.markdown("""
        <div class="control-panel">
            <h2 style="font-family: 'Orbitron', monospace; color: #40e0d0; text-align: center; margin-bottom: 2rem;">
                🎛️ CONTROL MATRIX
            </h2>
        </div>
        """, unsafe_allow_html=True)
        
        # API Status
        st.markdown("### 🔌 System Status")
        youtube_status = "🟢 ONLINE" if detector.youtube_api_key else "🔴 OFFLINE"
        reddit_status = "🟢 ONLINE"  # Reddit uses public API
        
        st.markdown(f"""
        <div style="font-family: 'Orbitron', monospace;">
            <p><span class="status-{'online' if detector.youtube_api_key else 'offline'}">YouTube API: {youtube_status}</span></p>
            <p><span class="status-online">Reddit API: {reddit_status}</span></p>
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
        
        # Advanced Options
        st.markdown("### ⚙️ Advanced Options")
        auto_refresh = st.checkbox("🔄 Auto Refresh (60s)", value=False)
        show_stats = st.checkbox("📊 Show Statistics", value=True)
        detailed_analysis = st.checkbox("🔬 Detailed Analysis", value=True)
    
    # Main Search Interface
    st.markdown("""
    <div class="search-interface">
        <h3 style="font-family: 'Orbitron', monospace; color: #40e0d0; text-align: center; margin-bottom: 2rem;">
            🎯 THREAT DETECTION INTERFACE
        </h3>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
    
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
                st.session_state.last_search_query = search_query
                
                # Success message with cyber styling
                st.markdown(f"""
                <div style="
                    background: linear-gradient(45deg, rgba(76, 175, 80, 0.2), rgba(76, 175, 80, 0.1));
                    border: 2px solid #4caf50;
                    border-radius: 15px;
                    padding: 1rem;
                    text-align: center;
                    font-family: 'Orbitron', monospace;
                    color: #4caf50;
                    margin: 1rem 0;
                ">
                    ✅ **SCAN COMPLETE** • {len(filtered_results)} THREATS IDENTIFIED
                </div>
                """, unsafe_allow_html=True)
    
    with col2:
        if st.button("🎯 **AUTO DETECT**", key="auto_detect"):
            with st.spinner("🎯 **EXECUTING AUTO-DETECTION PROTOCOL...**"):
                auto_query = "anti india propaganda terrorism hate"
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
                st.session_state.last_search_query = auto_query
                
                st.success(f"🎯 **AUTO-DETECTION COMPLETE** • {len(filtered_results)} threats identified")
    
    with col3:
        if st.button("🔄 **RESET MATRIX**", key="clear_results"):
            st.session_state.results = []
            st.session_state.search_performed = False
            st.session_state.last_search_query = ""
            st.success("✅ **MATRIX RESET COMPLETE**")
    
    with col4:
        if st.button("📊 **STATS**", key="show_stats"):
            if st.session_state.results:
                total_results = len(st.session_state.results)
                avg_threat_score = np.mean([r['threat_score'] for r in st.session_state.results])
                st.info(f"📊 **{total_results}** results • **{avg_threat_score:.1f}** avg threat score")
            else:
                st.info("📊 **No data available**")
    
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
        platform_counts = {}
        total_threat_score = 0
        
        for result in results:
            threat_counts[result['threat_level']] += 1
            platform = result['platform']
            platform_counts[platform] = platform_counts.get(platform, 0) + 1
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
        
        # Advanced Analytics
        if show_stats:
            st.markdown("""
            <div style="margin: 3rem 0 2rem 0;">
                <h3 style="font-family: 'Orbitron', monospace; color: #40e0d0; text-align: center; font-size: 2rem;">
                    📈 ADVANCED ANALYTICS MATRIX
                </h3>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig1 = create_advanced_threat_chart(results)
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                fig2 = create_platform_radar_chart(results)
                st.plotly_chart(fig2, use_container_width=True)
            
            # Timeline heatmap
            fig3 = create_timeline_heatmap(results)
            if fig3.data:
                st.plotly_chart(fig3, use_container_width=True)
        
        # Results Display
        st.markdown("""
        <div style="margin: 3rem 0 2rem 0;">
            <h3 style="font-family: 'Orbitron', monospace; color: #40e0d0; text-align: center; font-size: 2rem;">
                🎯 THREAT DETECTION RESULTS
            </h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Sort options
        col1, col2, col3 = st.columns([2, 2, 4])
        with col1:
            sort_by = st.selectbox("🔄 Sort By", ["Threat Score", "Platform", "Date", "Engagement"])
        with col2:
            sort_order = st.selectbox("📊 Order", ["Descending", "Ascending"])
        
        # Sort results
        reverse_order = sort_order == "Descending"
        
        if sort_by == "Threat Score":
            results = sorted(results, key=lambda x: x['threat_score'], reverse=reverse_order)
        elif sort_by == "Platform":
            results = sorted(results, key=lambda x: x['platform'], reverse=reverse_order)
        elif sort_by == "Date":
            results = sorted(results, key=lambda x: x.get('published', x.get('created', '')), reverse=reverse_order)
        elif sort_by == "Engagement":
            results = sorted(results, key=lambda x: x.get('stats', {}).get('views', x.get('score', 0)), reverse=reverse_order)
        
        # Display results with ultra-immersive cards
        for i, result in enumerate(results):
            display_ultra_result_card(result, i)
            
            # Add separator between results
            if i < len(results) - 1:
                st.markdown("""
                <div style="
                    height: 2px;
                    background: linear-gradient(90deg, transparent, #40e0d0, transparent);
                    margin: 2rem 0;
                    opacity: 0.3;
                "></div>
                """, unsafe_allow_html=True)
    
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
    
    # Auto-refresh functionality
    if auto_refresh and st.session_state.search_performed:
        time.sleep(60)
        st.rerun()

if __name__ == "__main__":
    main()