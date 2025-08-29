#!/usr/bin/env python3
"""
Live Anti-Nationalist Content Detection Dashboard
Real-time YouTube search and analysis for anti-nationalist content
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Any
import re
from api_config import get_api_config
from textblob import TextBlob

# Page configuration
st.set_page_config(
    page_title="Dharma Platform - Anti-Nationalist Content Detection",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #dc3545 0%, #fd7e14 100%);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .threat-post {
        background: white;
        border-left: 5px solid #dc3545;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 5px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .threat-post:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
        background: #f8f9fa;
    }
    
    .threat-critical { border-left-color: #dc3545; background: #fff5f5; }
    .threat-high { border-left-color: #fd7e14; background: #fff8f0; }
    .threat-medium { border-left-color: #ffc107; background: #fffbf0; }
    .threat-low { border-left-color: #28a745; background: #f0fff4; }
    
    .post-content {
        font-size: 0.9rem;
        margin: 0.5rem 0;
        color: #495057;
        font-weight: 500;
    }
    
    .post-meta {
        font-size: 0.8rem;
        color: #6c757d;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 0.5rem;
    }
    
    .platform-badge {
        background: #dc3545;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 12px;
        font-size: 0.7rem;
        font-weight: bold;
    }
    
    .threat-badge {
        padding: 0.2rem 0.5rem;
        border-radius: 12px;
        font-size: 0.7rem;
        font-weight: bold;
        color: white;
    }
    
    .threat-critical-badge { background: #dc3545; }
    .threat-high-badge { background: #fd7e14; }
    .threat-medium-badge { background: #ffc107; color: #000; }
    .threat-low-badge { background: #28a745; }
    
    .live-search {
        background: linear-gradient(90deg, #dc3545 0%, #fd7e14 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
        animation: pulse 2s infinite;
        display: inline-block;
        margin: 0.5rem;
    }
    
    @keyframes pulse {
        0% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.8; transform: scale(1.05); }
        100% { opacity: 1; transform: scale(1); }
    }
    
    .search-box {
        background: white;
        border: 2px solid #dc3545;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .alert-box {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
        color: #856404;
    }
</style>
""", unsafe_allow_html=True)

class AntiNationalistDetector:
    """Live anti-nationalist content detection system"""
    
    def __init__(self):
        self.config = get_api_config()
        self.initialize_session_state()
        
        # Anti-nationalist keywords and patterns
        self.anti_nationalist_keywords = [
            # Direct anti-India terms
            'anti-india', 'anti india', 'against india', 'hate india', 'india bad',
            'corrupt india', 'fascist india', 'terrorist india', 'oppressive india',
            'india sucks', 'destroy india', 'break india', 'divide india',
            
            # Anti-government terms
            'modi dictator', 'fascist modi', 'hitler modi', 'corrupt government',
            'bjp fascist', 'hindutva terror', 'saffron terror', 'brahmin supremacy',
            
            # Separatist content
            'free kashmir', 'azad kashmir', 'khalistan', 'independent kashmir',
            'pakistan zindabad', 'china support', 'anti-national',
            
            # Religious hatred
            'hindu terror', 'brahmin oppression', 'caste system evil',
            'muslim persecution', 'christian persecution', 'minority oppression',
            
            # Economic criticism
            'india poverty', 'failed state', 'third world country',
            'economic disaster', 'unemployment crisis', 'farmer suicide',
            
            # International criticism
            'india isolated', 'world against india', 'boycott india',
            'sanctions on india', 'human rights violation'
        ]
        
        # Search terms for YouTube
        self.search_terms = [
            'anti india propaganda',
            'india criticism international',
            'modi dictator fascist',
            'kashmir human rights violation',
            'india minority persecution',
            'boycott india campaign',
            'pakistan vs india truth',
            'china india border dispute',
            'india failed state economy',
            'hindutva fascism documentary'
        ]
    
    def initialize_session_state(self):
        """Initialize session state variables"""
        if 'search_results' not in st.session_state:
            st.session_state.search_results = []
        if 'last_search' not in st.session_state:
            st.session_state.last_search = None
        if 'search_query' not in st.session_state:
            st.session_state.search_query = ""
        if 'threat_analysis' not in st.session_state:
            st.session_state.threat_analysis = {}
    
    def render_header(self):
        """Render dashboard header"""
        st.markdown("""
        <div class="main-header">
            <h1>🛡️ Dharma Platform - Anti-Nationalist Content Detection</h1>
            <p>Real-time YouTube Search and Analysis for Anti-Nationalist Content</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Status indicators
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown('<div class="live-search">🔍 LIVE SEARCH</div>', unsafe_allow_html=True)
        
        with col2:
            if st.session_state.last_search:
                search_time = st.session_state.last_search.strftime("%H:%M:%S")
                st.markdown(f'<div class="live-search">🕒 Last: {search_time}</div>', unsafe_allow_html=True)
        
        with col3:
            result_count = len(st.session_state.search_results)
            st.markdown(f'<div class="live-search">📊 Found: {result_count}</div>', unsafe_allow_html=True)
        
        with col4:
            threat_count = sum(1 for r in st.session_state.search_results if r.get('threat_level') in ['Critical', 'High'])
            st.markdown(f'<div class="live-search">⚠️ Threats: {threat_count}</div>', unsafe_allow_html=True)
    
    def render_search_controls(self):
        """Render search controls"""
        st.markdown("""
        <div class="search-box">
            <h3>🔍 Live YouTube Search for Anti-Nationalist Content</h3>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            search_query = st.text_input(
                "Enter search terms:",
                value=st.session_state.search_query,
                placeholder="e.g., anti india propaganda, modi criticism, kashmir issue"
            )
            st.session_state.search_query = search_query
        
        with col2:
            if st.button("🔍 Search YouTube", type="primary"):
                if search_query.strip():
                    self.search_youtube_content(search_query)
                else:
                    st.warning("Please enter search terms")
        
        with col3:
            if st.button("🎯 Auto Detect"):
                self.auto_detect_threats()
        
        # Predefined search buttons
        st.markdown("**Quick Search Options:**")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("Anti-India Propaganda"):
                self.search_youtube_content("anti india propaganda")
        
        with col2:
            if st.button("Modi Criticism"):
                self.search_youtube_content("modi dictator fascist criticism")
        
        with col3:
            if st.button("Kashmir Issue"):
                self.search_youtube_content("kashmir human rights violation")
        
        with col4:
            if st.button("Minority Issues"):
                self.search_youtube_content("india minority persecution")
    
    async def search_youtube_api(self, query: str, max_results: int = 20) -> List[Dict]:
        """Search YouTube API for content"""
        if not self.config.is_youtube_configured():
            st.error("YouTube API not configured")
            return []
        
        results = []
        
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://www.googleapis.com/youtube/v3/search"
                params = {
                    'part': 'snippet',
                    'q': query,
                    'type': 'video',
                    'maxResults': max_results,
                    'order': 'relevance',
                    'publishedAfter': (datetime.now() - timedelta(days=30)).isoformat() + 'Z',
                    'key': self.config.youtube_api_key
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for item in data.get('items', []):
                            snippet = item['snippet']
                            video_id = item['id']['videoId']
                            
                            # Get video statistics
                            stats_url = "https://www.googleapis.com/youtube/v3/videos"
                            stats_params = {
                                'part': 'statistics',
                                'id': video_id,
                                'key': self.config.youtube_api_key
                            }
                            
                            stats = {}
                            async with session.get(stats_url, params=stats_params) as stats_response:
                                if stats_response.status == 200:
                                    stats_data = await stats_response.json()
                                    if stats_data.get('items'):
                                        stats = stats_data['items'][0]['statistics']
                            
                            result = {
                                'video_id': video_id,
                                'title': snippet['title'],
                                'description': snippet.get('description', ''),
                                'channel_title': snippet['channelTitle'],
                                'published_at': snippet['publishedAt'],
                                'thumbnail': snippet['thumbnails']['medium']['url'],
                                'url': f"https://www.youtube.com/watch?v={video_id}",
                                'views': int(stats.get('viewCount', 0)),
                                'likes': int(stats.get('likeCount', 0)),
                                'comments': int(stats.get('commentCount', 0))
                            }
                            
                            results.append(result)
                    
                    else:
                        st.error(f"YouTube API error: {response.status}")
        
        except Exception as e:
            st.error(f"Error searching YouTube: {e}")
        
        return results
    
    def analyze_threat_level(self, content: str, title: str) -> Dict[str, Any]:
        """Analyze threat level of content"""
        combined_text = f"{title} {content}".lower()
        
        # Count anti-nationalist keywords
        keyword_matches = []
        for keyword in self.anti_nationalist_keywords:
            if keyword in combined_text:
                keyword_matches.append(keyword)
        
        # Calculate threat score
        threat_score = len(keyword_matches)
        
        # Sentiment analysis
        try:
            blob = TextBlob(combined_text)
            sentiment_score = blob.sentiment.polarity
        except:
            sentiment_score = 0
        
        # Determine threat level
        if threat_score >= 5 or sentiment_score < -0.5:
            threat_level = "Critical"
        elif threat_score >= 3 or sentiment_score < -0.3:
            threat_level = "High"
        elif threat_score >= 1 or sentiment_score < -0.1:
            threat_level = "Medium"
        else:
            threat_level = "Low"
        
        return {
            'threat_level': threat_level,
            'threat_score': threat_score,
            'sentiment_score': sentiment_score,
            'keyword_matches': keyword_matches,
            'analysis_summary': f"Found {len(keyword_matches)} anti-nationalist keywords"
        }
    
    def search_youtube_content(self, query: str):
        """Search YouTube for content and analyze threats"""
        with st.spinner(f"Searching YouTube for: {query}"):
            try:
                # Run async search
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                results = loop.run_until_complete(self.search_youtube_api(query))
                loop.close()
                
                # Analyze each result for threats
                analyzed_results = []
                for result in results:
                    analysis = self.analyze_threat_level(
                        result['description'], 
                        result['title']
                    )
                    result.update(analysis)
                    analyzed_results.append(result)
                
                # Sort by threat level
                threat_order = {'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3}
                analyzed_results.sort(key=lambda x: threat_order.get(x['threat_level'], 4))
                
                st.session_state.search_results = analyzed_results
                st.session_state.last_search = datetime.now()
                
                st.success(f"Found {len(results)} videos. Analyzed for anti-nationalist content.")
                
            except Exception as e:
                st.error(f"Error during search: {e}")
    
    def auto_detect_threats(self):
        """Automatically search for threats using predefined terms"""
        with st.spinner("Auto-detecting anti-nationalist content..."):
            all_results = []
            
            for search_term in self.search_terms[:3]:  # Limit to avoid quota
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    results = loop.run_until_complete(self.search_youtube_api(search_term, 10))
                    loop.close()
                    
                    for result in results:
                        analysis = self.analyze_threat_level(
                            result['description'], 
                            result['title']
                        )
                        result.update(analysis)
                        result['search_term'] = search_term
                        all_results.append(result)
                    
                    time.sleep(1)  # Rate limiting
                    
                except Exception as e:
                    st.error(f"Error searching for '{search_term}': {e}")
            
            # Remove duplicates and sort by threat
            unique_results = {}
            for result in all_results:
                if result['video_id'] not in unique_results:
                    unique_results[result['video_id']] = result
            
            threat_order = {'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3}
            final_results = list(unique_results.values())
            final_results.sort(key=lambda x: threat_order.get(x['threat_level'], 4))
            
            st.session_state.search_results = final_results
            st.session_state.last_search = datetime.now()
            
            st.success(f"Auto-detection complete. Found {len(final_results)} videos.")
    
    def render_results(self):
        """Render search results with threat analysis"""
        if not st.session_state.search_results:
            st.info("No search results yet. Use the search controls above to find content.")
            return
        
        # Summary metrics
        st.markdown("### 📊 Threat Analysis Summary")
        
        col1, col2, col3, col4 = st.columns(4)
        
        threat_counts = {'Critical': 0, 'High': 0, 'Medium': 0, 'Low': 0}
        for result in st.session_state.search_results:
            threat_level = result.get('threat_level', 'Low')
            threat_counts[threat_level] += 1
        
        with col1:
            st.metric("🔴 Critical Threats", threat_counts['Critical'])
        with col2:
            st.metric("🟠 High Threats", threat_counts['High'])
        with col3:
            st.metric("🟡 Medium Threats", threat_counts['Medium'])
        with col4:
            st.metric("🟢 Low Threats", threat_counts['Low'])
        
        # Threat level filter
        st.markdown("### 🎯 Filter Results")
        selected_threats = st.multiselect(
            "Show threat levels:",
            ['Critical', 'High', 'Medium', 'Low'],
            default=['Critical', 'High', 'Medium', 'Low']
        )
        
        # Filter results
        filtered_results = [
            r for r in st.session_state.search_results 
            if r.get('threat_level') in selected_threats
        ]
        
        # Display results
        st.markdown(f"### 🎬 Search Results ({len(filtered_results)} videos)")
        
        for i, result in enumerate(filtered_results):
            threat_level = result.get('threat_level', 'Low')
            threat_class = f"threat-{threat_level.lower()}"
            
            # Create clickable post
            with st.container():
                st.markdown(f"""
                <div class="threat-post {threat_class}" onclick="window.open('{result['url']}', '_blank')">
                    <div class="post-content">
                        <strong>{result['title']}</strong>
                    </div>
                    <div class="post-content">
                        {result['description'][:200]}...
                    </div>
                    <div class="post-meta">
                        <div>
                            <span class="platform-badge">YouTube</span>
                            <span class="threat-badge threat-{threat_level.lower()}-badge">{threat_level} Threat</span>
                        </div>
                        <div>
                            👁️ {result['views']:,} | 👍 {result['likes']:,} | 💬 {result['comments']:,}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Expandable analysis details
                with st.expander(f"🔍 Analysis Details - {result['title'][:50]}..."):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**Threat Analysis:**")
                        st.write(f"- Threat Level: {threat_level}")
                        st.write(f"- Threat Score: {result.get('threat_score', 0)}")
                        st.write(f"- Sentiment Score: {result.get('sentiment_score', 0):.2f}")
                        
                        if result.get('keyword_matches'):
                            st.write("**Detected Keywords:**")
                            for keyword in result['keyword_matches'][:5]:
                                st.write(f"- {keyword}")
                    
                    with col2:
                        st.write("**Video Details:**")
                        st.write(f"- Channel: {result['channel_title']}")
                        st.write(f"- Published: {result['published_at'][:10]}")
                        st.write(f"- Views: {result['views']:,}")
                        st.write(f"- Engagement: {result['likes'] + result['comments']:,}")
                        
                        if st.button(f"🔗 Open Video", key=f"open_{i}"):
                            st.markdown(f"[Open in YouTube]({result['url']})")
    
    def render_sidebar(self):
        """Render sidebar with controls and info"""
        with st.sidebar:
            st.markdown("## 🛡️ Threat Detection Controls")
            
            # API Status
            st.markdown("### 📡 API Status")
            if self.config.is_youtube_configured():
                st.success("✅ YouTube API Connected")
            else:
                st.error("❌ YouTube API Not Configured")
            
            # Search Statistics
            if st.session_state.search_results:
                st.markdown("### 📊 Current Session")
                st.write(f"Total Videos: {len(st.session_state.search_results)}")
                
                threat_counts = {'Critical': 0, 'High': 0, 'Medium': 0, 'Low': 0}
                for result in st.session_state.search_results:
                    threat_level = result.get('threat_level', 'Low')
                    threat_counts[threat_level] += 1
                
                for level, count in threat_counts.items():
                    if count > 0:
                        st.write(f"{level}: {count}")
            
            # Clear results
            if st.button("🗑️ Clear Results"):
                st.session_state.search_results = []
                st.rerun()
            
            # Information
            st.markdown("### ℹ️ About")
            st.info("""
            This dashboard searches YouTube in real-time for potentially anti-nationalist content and analyzes threat levels based on:
            
            - Anti-India keywords
            - Sentiment analysis
            - Content patterns
            - Engagement metrics
            """)
            
            st.markdown("### 🎯 Detection Criteria")
            st.write("""
            **Critical**: 5+ keywords, very negative sentiment
            **High**: 3+ keywords, negative sentiment  
            **Medium**: 1+ keywords, slightly negative
            **Low**: Minimal indicators
            """)

def main():
    """Main dashboard function"""
    detector = AntiNationalistDetector()
    
    # Render components
    detector.render_header()
    detector.render_search_controls()
    detector.render_sidebar()
    detector.render_results()
    
    # Auto-refresh functionality
    if st.sidebar.checkbox("🔄 Auto-refresh (30s)"):
        time.sleep(30)
        st.rerun()

if __name__ == "__main__":
    main()