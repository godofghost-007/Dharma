#!/usr/bin/env python3
"""
Enhanced Real Data Dashboard for Dharma Platform
Uses real social media data with clickable links to original posts
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import asyncio
import aiohttp
import sqlite3
import json
import time
from typing import Dict, List, Any
import re
from real_data_collector import RealDataCollector, collect_real_data
from api_config import get_api_config

# Page configuration
st.set_page_config(
    page_title="Dharma Platform - Real Data Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS with clickable post styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
    
    .threat-high { border-left-color: #fd7e14; }
    .threat-medium { border-left-color: #ffc107; }
    .threat-low { border-left-color: #28a745; }
    
    .post-content {
        font-size: 0.9rem;
        margin: 0.5rem 0;
        color: #495057;
    }
    
    .post-meta {
        font-size: 0.8rem;
        color: #6c757d;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .platform-badge {
        background: #007bff;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 12px;
        font-size: 0.7rem;
        font-weight: bold;
    }
    
    .sentiment-badge {
        padding: 0.2rem 0.5rem;
        border-radius: 12px;
        font-size: 0.7rem;
        font-weight: bold;
    }
    
    .sentiment-anti-india { background: #dc3545; color: white; }
    .sentiment-pro-india { background: #28a745; color: white; }
    .sentiment-neutral { background: #6c757d; color: white; }
    
    .live-indicator {
        background: linear-gradient(90deg, #ff4444 0%, #ff6666 100%);
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
    
    .metric-card {
        background: white;
        border: 1px solid #e9ecef;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        margin: 0.5rem 0;
    }
    
    .data-source-info {
        background: #e3f2fd;
        border: 1px solid #2196f3;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

class RealDataDashboard:
    """Enhanced dashboard using real social media data"""
    
    def __init__(self):
        self.collector = RealDataCollector()
        self.config = get_api_config()
        self.initialize_session_state()
        
        # Anti-nationalist detection keywords
        self.anti_nationalist_keywords = [
            'anti-india', 'anti india', 'against india', 'hate india', 'india bad',
            'corrupt india', 'fascist india', 'terrorist india', 'oppressive india',
            'modi dictator', 'fascist modi', 'hitler modi', 'bjp fascist',
            'free kashmir', 'azad kashmir', 'khalistan', 'pakistan zindabad',
            'hindu terror', 'brahmin oppression', 'minority persecution'
        ]
    
    def initialize_session_state(self):
        """Initialize session state variables"""
        if 'real_data' not in st.session_state:
            st.session_state.real_data = []
        if 'last_update' not in st.session_state:
            st.session_state.last_update = None
        if 'auto_refresh' not in st.session_state:
            st.session_state.auto_refresh = True
        if 'selected_platforms' not in st.session_state:
            st.session_state.selected_platforms = ['Twitter', 'YouTube', 'Reddit']
        if 'youtube_search_results' not in st.session_state:
            st.session_state.youtube_search_results = []
        if 'last_youtube_search' not in st.session_state:
            st.session_state.last_youtube_search = None
    
    def render_header(self):
        """Render dashboard header"""
        st.markdown("""
        <div class="main-header">
            <h1>🛡️ Dharma Platform - Real Data Intelligence</h1>
            <p>Live Social Media Monitoring with Real Data Sources</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Status indicators
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown('<div class="live-indicator">🔴 LIVE DATA</div>', unsafe_allow_html=True)
        
        with col2:
            if st.session_state.last_update:
                update_time = st.session_state.last_update.strftime("%H:%M:%S")
                st.markdown(f'<div class="live-indicator">🕒 Updated: {update_time}</div>', unsafe_allow_html=True)
        
        with col3:
            data_count = len(st.session_state.real_data)
            st.markdown(f'<div class="live-indicator">📊 Posts: {data_count}</div>', unsafe_allow_html=True)
        
        with col4:
            if st.button("🔄 Refresh Data"):
                self.load_real_data()
                st.rerun()
    
    def render_sidebar(self):
        """Render sidebar controls"""
        with st.sidebar:
            st.markdown("## 🎛️ Real Data Controls")
            
            # Live YouTube Search
            st.markdown("### 🔍 Live YouTube Search")
            search_query = st.text_input("Search YouTube:", placeholder="anti india, modi criticism")
            
            if st.button("🎯 Search Anti-Nationalist Content"):
                if search_query.strip():
                    self.search_youtube_live(search_query)
                else:
                    # Auto-search for anti-nationalist content
                    self.search_youtube_live("anti india propaganda")
            
            # Quick search buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🚨 Auto Detect"):
                    self.auto_detect_threats()
            with col2:
                if st.button("🔄 Refresh DB"):
                    self.load_real_data()
            
            # Data collection controls
            st.markdown("### 📡 Data Collection")
            
            if st.button("🔄 Collect Fresh Data", type="primary"):
                with st.spinner("Collecting real data from social media..."):
                    try:
                        # Run async data collection
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        new_data = loop.run_until_complete(collect_real_data())
                        loop.close()
                        
                        st.session_state.real_data = new_data
                        st.session_state.last_update = datetime.now()
                        st.success(f"Collected {len(new_data)} real posts!")
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error collecting data: {e}")
            
            # Platform selection
            st.markdown("### 🌐 Platform Filter")
            available_platforms = ['Twitter', 'YouTube', 'Reddit', 'All']
            selected_platform = st.selectbox(
                "Select Platform:",
                available_platforms,
                index=3
            )
            
            # Time range filter
            st.markdown("### ⏰ Time Range")
            time_range = st.selectbox(
                "Select Time Range:",
                ["Last Hour", "Last 6 Hours", "Last 24 Hours", "Last 7 Days"],
                index=2
            )
            
            # Threat level filter
            st.markdown("### 🚨 Threat Level")
            threat_levels = st.multiselect(
                "Show Threat Levels:",
                ["Critical", "High", "Medium", "Low"],
                default=["Critical", "High", "Medium", "Low"]
            )
            
            # Auto-refresh
            st.markdown("### 🔄 Auto Refresh")
            auto_refresh = st.checkbox("Enable Auto Refresh", value=st.session_state.auto_refresh)
            if auto_refresh:
                refresh_interval = st.slider("Refresh Interval (minutes)", 1, 30, 5)
            
            # Data source info
            st.markdown("### 📊 Data Sources")
            st.info("""
            **Real Data Sources:**
            • Twitter API v2
            • YouTube Data API
            • Reddit Public API
            • Real-time collection
            """)
            
            return selected_platform, time_range, threat_levels, auto_refresh
    
    def load_real_data(self):
        """Load real data from database"""
        try:
            posts = self.collector.get_posts_from_db(limit=200)
            
            # Add mock analysis results for demonstration
            for post in posts:
                if not post.get('sentiment'):
                    post['sentiment'] = self.analyze_sentiment_simple(post['content'])
                if post.get('bot_probability') is None:
                    post['bot_probability'] = self.calculate_bot_probability(post)
                if post.get('risk_score') is None:
                    post['risk_score'] = self.calculate_risk_score(post)
            
            st.session_state.real_data = posts
            st.session_state.last_update = datetime.now()
            
        except Exception as e:
            st.error(f"Error loading real data: {e}")
            st.session_state.real_data = []
    
    def analyze_sentiment_simple(self, content: str) -> str:
        """Simple sentiment analysis based on keywords"""
        content_lower = content.lower()
        
        # Anti-India keywords
        anti_india_keywords = [
            'anti-india', 'against india', 'hate india', 'india bad', 'corrupt india',
            'fascist india', 'terrorist india', 'oppressive india'
        ]
        
        # Pro-India keywords
        pro_india_keywords = [
            'proud india', 'great india', 'love india', 'jai hind', 'bharat mata',
            'incredible india', 'amazing india', 'strong india', 'digital india'
        ]
        
        anti_score = sum(1 for keyword in anti_india_keywords if keyword in content_lower)
        pro_score = sum(1 for keyword in pro_india_keywords if keyword in content_lower)
        
        if anti_score > pro_score:
            return 'Anti-India'
        elif pro_score > anti_score:
            return 'Pro-India'
        else:
            return 'Neutral'
    
    def calculate_bot_probability(self, post: Dict[str, Any]) -> float:
        """Calculate bot probability based on post characteristics"""
        score = 0.0
        
        try:
            # Check for repetitive content
            content = post.get('content', '')
            if content and len(content.split()) > 0:
                unique_words = len(set(content.split()))
                total_words = len(content.split())
                if unique_words < total_words * 0.7:
                    score += 0.3
            
            # Check engagement patterns
            engagement = post.get('engagement', {})
            if engagement:
                likes = engagement.get('likes', 0) or 0
                comments = engagement.get('comments', 0) or 0
                
                if likes > 0 and comments == 0:
                    score += 0.2
            
            # Check for suspicious patterns
            if content and re.search(r'(.)\1{3,}', content):  # Repeated characters
                score += 0.2
            
            return float(min(1.0, max(0.0, score)))
            
        except Exception as e:
            # Return default value if calculation fails
            return 0.0
    
    def calculate_risk_score(self, post: Dict[str, Any]) -> float:
        """Calculate risk score for the post"""
        sentiment = post.get('sentiment', 'Neutral')
        bot_prob = post.get('bot_probability', 0.0)
        
        # Ensure bot_prob is not None
        if bot_prob is None:
            bot_prob = 0.0
        
        base_score = 0.0
        
        if sentiment == 'Anti-India':
            base_score = 0.7
        elif sentiment == 'Pro-India':
            base_score = 0.1
        else:
            base_score = 0.3
        
        # Adjust for bot probability
        risk_score = base_score + (float(bot_prob) * 0.3)
        
        return float(min(1.0, max(0.0, risk_score)))
    
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
                    'publishedAfter': (datetime.now() - timedelta(days=7)).isoformat() + 'Z',
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
                            
                            # Analyze for anti-nationalist content
                            content = f"{snippet['title']} {snippet.get('description', '')}"
                            sentiment = self.analyze_sentiment_simple(content)
                            
                            result = {
                                'id': f"youtube_live_{video_id}",
                                'platform': 'YouTube',
                                'content': snippet['title'],
                                'description': snippet.get('description', ''),
                                'author_username': snippet['channelTitle'],
                                'timestamp': snippet['publishedAt'],
                                'url': f"https://www.youtube.com/watch?v={video_id}",
                                'engagement': {
                                    'likes': int(stats.get('likeCount', 0)),
                                    'shares': 0,
                                    'comments': int(stats.get('commentCount', 0)),
                                    'views': int(stats.get('viewCount', 0))
                                },
                                'thumbnail': snippet['thumbnails']['medium']['url'],
                                'sentiment': sentiment,
                                'bot_probability': 0.1,  # Lower for YouTube videos
                                'risk_score': self.calculate_risk_score({'sentiment': sentiment, 'bot_probability': 0.1})
                            }
                            
                            results.append(result)
                    
                    else:
                        st.error(f"YouTube API error: {response.status}")
        
        except Exception as e:
            st.error(f"Error searching YouTube: {e}")
        
        return results
    
    def search_youtube_live(self, query: str):
        """Search YouTube for live content"""
        with st.spinner(f"Searching YouTube for: {query}"):
            try:
                # Run async search
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                results = loop.run_until_complete(self.search_youtube_api(query))
                loop.close()
                
                # Sort by risk score
                results.sort(key=lambda x: x.get('risk_score', 0), reverse=True)
                
                # Add to session state
                st.session_state.youtube_search_results = results
                st.session_state.last_youtube_search = datetime.now()
                
                # Also add high-threat results to main data
                high_threat_results = [r for r in results if r.get('risk_score', 0) >= 0.5]
                st.session_state.real_data.extend(high_threat_results)
                
                st.success(f"Found {len(results)} videos. {len(high_threat_results)} flagged as potential threats.")
                
            except Exception as e:
                st.error(f"Error during YouTube search: {e}")
    
    def auto_detect_threats(self):
        """Auto-detect anti-nationalist threats from YouTube"""
        search_terms = [
            "anti india propaganda",
            "modi dictator fascist",
            "kashmir human rights violation"
        ]
        
        with st.spinner("Auto-detecting anti-nationalist content..."):
            all_results = []
            
            for search_term in search_terms[:2]:  # Limit to avoid quota
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    results = loop.run_until_complete(self.search_youtube_api(search_term, 10))
                    loop.close()
                    
                    all_results.extend(results)
                    time.sleep(1)  # Rate limiting
                    
                except Exception as e:
                    st.error(f"Error searching for '{search_term}': {e}")
            
            # Remove duplicates and sort by risk
            unique_results = {}
            for result in all_results:
                video_id = result['id']
                if video_id not in unique_results or result['risk_score'] > unique_results[video_id]['risk_score']:
                    unique_results[video_id] = result
            
            final_results = list(unique_results.values())
            final_results.sort(key=lambda x: x.get('risk_score', 0), reverse=True)
            
            st.session_state.youtube_search_results = final_results
            st.session_state.last_youtube_search = datetime.now()
            
            # Add high-threat results to main data
            high_threat_results = [r for r in final_results if r.get('risk_score', 0) >= 0.5]
            st.session_state.real_data.extend(high_threat_results)
            
            st.success(f"Auto-detection complete. Found {len(final_results)} videos, {len(high_threat_results)} potential threats.")
    
    def filter_data(self, data: List[Dict], platform: str, time_range: str, threat_levels: List[str]) -> List[Dict]:
        """Filter data based on user selections"""
        filtered_data = data.copy()
        
        # Platform filter
        if platform != 'All':
            filtered_data = [post for post in filtered_data if post.get('platform') == platform]
        
        # Time range filter
        now = datetime.now()
        if time_range == "Last Hour":
            cutoff = now - timedelta(hours=1)
        elif time_range == "Last 6 Hours":
            cutoff = now - timedelta(hours=6)
        elif time_range == "Last 24 Hours":
            cutoff = now - timedelta(days=1)
        else:  # Last 7 Days
            cutoff = now - timedelta(days=7)
        
        filtered_data = [
            post for post in filtered_data 
            if datetime.fromisoformat(str(post.get('timestamp', now)).replace('Z', '+00:00')) >= cutoff
        ]
        
        # Threat level filter
        if threat_levels:
            def get_threat_level(risk_score):
                # Handle None values
                if risk_score is None:
                    risk_score = 0.0
                
                if risk_score >= 0.8:
                    return "Critical"
                elif risk_score >= 0.6:
                    return "High"
                elif risk_score >= 0.4:
                    return "Medium"
                else:
                    return "Low"
            
            filtered_data = [
                post for post in filtered_data 
                if get_threat_level(post.get('risk_score', 0.0)) in threat_levels
            ]
        
        return filtered_data
    
    def render_metrics_overview(self, data: List[Dict]):
        """Render overview metrics"""
        st.markdown("## 📊 Real-Time Metrics")
        
        if not data:
            st.warning("No data available. Click 'Collect Fresh Data' to gather real social media posts.")
            return
        
        # Calculate metrics
        total_posts = len(data)
        anti_india_posts = len([p for p in data if p.get('sentiment') == 'Anti-India'])
        pro_india_posts = len([p for p in data if p.get('sentiment') == 'Pro-India'])
        high_risk_posts = len([p for p in data if p.get('risk_score') is not None and p.get('risk_score', 0) >= 0.6])
        
        # Display metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("📝 Total Posts", total_posts)
        
        with col2:
            threat_pct = (anti_india_posts / max(total_posts, 1)) * 100
            st.metric("🚨 Anti-India", anti_india_posts, f"{threat_pct:.1f}%")
        
        with col3:
            positive_pct = (pro_india_posts / max(total_posts, 1)) * 100
            st.metric("✅ Pro-India", pro_india_posts, f"{positive_pct:.1f}%")
        
        with col4:
            risk_pct = (high_risk_posts / max(total_posts, 1)) * 100
            st.metric("⚠️ High Risk", high_risk_posts, f"{risk_pct:.1f}%")
        
        with col5:
            avg_engagement = sum(p.get('engagement', {}).get('likes', 0) for p in data) / max(total_posts, 1)
            st.metric("👍 Avg Engagement", f"{avg_engagement:.0f}")
    
    def render_threat_posts(self, data: List[Dict]):
        """Render threat-level posts with clickable links"""
        st.markdown("## 🚨 Threat Level Posts (Click to View Original)")
        
        # Filter for threat posts
        threat_posts = [
            post for post in data 
            if post.get('sentiment') == 'Anti-India' or (post.get('risk_score') is not None and post.get('risk_score', 0) >= 0.5)
        ]
        
        if not threat_posts:
            st.success("✅ No high-threat posts detected in current data")
            return
        
        # Sort by risk score
        threat_posts.sort(key=lambda x: x.get('risk_score', 0), reverse=True)
        
        for post in threat_posts[:10]:  # Show top 10 threats
            risk_score = post.get('risk_score', 0)
            
            # Handle None risk scores
            if risk_score is None:
                risk_score = 0.0
            
            # Determine threat level
            if risk_score >= 0.8:
                threat_class = "threat-critical"
                threat_label = "🔴 CRITICAL"
            elif risk_score >= 0.6:
                threat_class = "threat-high"
                threat_label = "🟠 HIGH"
            elif risk_score >= 0.4:
                threat_class = "threat-medium"
                threat_label = "🟡 MEDIUM"
            else:
                threat_class = "threat-low"
                threat_label = "🟢 LOW"
            
            # Get post details
            content = post.get('content', 'No content')[:200] + "..."
            platform = post.get('platform', 'Unknown')
            author = post.get('author_username', 'Unknown')
            timestamp = post.get('timestamp', datetime.now())
            url = post.get('url', '#')
            sentiment = post.get('sentiment', 'Unknown')
            
            # Format timestamp
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except:
                    timestamp = datetime.now()
            
            time_str = timestamp.strftime("%Y-%m-%d %H:%M")
            
            # Render clickable post card
            st.markdown(f"""
            <div class="threat-post {threat_class}" onclick="window.open('{url}', '_blank')">
                <div class="post-meta">
                    <div>
                        <span class="platform-badge">{platform}</span>
                        <span class="sentiment-badge sentiment-{sentiment.lower().replace('-', '-')}">{sentiment}</span>
                        <strong>{threat_label}</strong>
                    </div>
                    <div>
                        <small>Risk: {risk_score:.2f} | {time_str}</small>
                    </div>
                </div>
                <div class="post-content">
                    <strong>@{author}:</strong> {content}
                </div>
                <div style="font-size: 0.7rem; color: #007bff; margin-top: 0.5rem;">
                    🔗 Click to view original post
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Add some spacing
            st.markdown("<br>", unsafe_allow_html=True)
    
    def render_analytics(self, data: List[Dict]):
        """Render analytics charts"""
        if not data:
            return
        
        st.markdown("## 📈 Real Data Analytics")
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Sentiment distribution
            if 'sentiment' in df.columns:
                sentiment_counts = df['sentiment'].value_counts()
                fig_sentiment = px.pie(
                    values=sentiment_counts.values,
                    names=sentiment_counts.index,
                    title="Sentiment Distribution (Real Data)",
                    color_discrete_map={
                        'Pro-India': '#28a745',
                        'Neutral': '#6c757d',
                        'Anti-India': '#dc3545'
                    }
                )
                st.plotly_chart(fig_sentiment, use_container_width=True)
        
        with col2:
            # Platform distribution
            if 'platform' in df.columns:
                platform_counts = df['platform'].value_counts()
                fig_platform = px.bar(
                    x=platform_counts.index,
                    y=platform_counts.values,
                    title="Posts by Platform (Real Data)",
                    color=platform_counts.values,
                    color_continuous_scale="viridis"
                )
                st.plotly_chart(fig_platform, use_container_width=True)
        
        # Timeline analysis
        if 'timestamp' in df.columns:
            st.markdown("### 📅 Timeline Analysis")
            
            # Convert timestamps
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['hour'] = df['timestamp'].dt.hour
            
            hourly_activity = df.groupby('hour').size().reset_index(name='posts')
            
            fig_timeline = px.line(
                hourly_activity,
                x='hour',
                y='posts',
                title="Hourly Activity (Real Data)",
                markers=True
            )
            st.plotly_chart(fig_timeline, use_container_width=True)
    
    def run(self):
        """Main dashboard function"""
        # Render header
        self.render_header()
        
        # Load data if not already loaded
        if not st.session_state.real_data:
            self.load_real_data()
        
        # Render sidebar and get filters
        platform_filter, time_filter, threat_filter, auto_refresh = self.render_sidebar()
        
        # Filter data
        filtered_data = self.filter_data(
            st.session_state.real_data, 
            platform_filter, 
            time_filter, 
            threat_filter
        )
        
        # Render main content
        self.render_metrics_overview(filtered_data)
        self.render_threat_posts(filtered_data)
        self.render_analytics(filtered_data)
        
        # Auto-refresh logic
        if auto_refresh and st.session_state.last_update:
            time_since_update = datetime.now() - st.session_state.last_update
            if time_since_update.total_seconds() > 300:  # 5 minutes
                st.rerun()

def main():
    """Main function"""
    dashboard = RealDataDashboard()
    dashboard.run()

if __name__ == "__main__":
    main()