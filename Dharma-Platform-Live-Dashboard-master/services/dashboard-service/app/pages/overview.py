"""
Dashboard Overview Page
Main dashboard with key metrics, trends, and real-time updates
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any

from ..core.api_client import APIClient
from ..components.metrics_cards import MetricsCards
from ..components.charts import ChartGenerator
from ..utils.formatters import format_number, format_percentage

class OverviewPage:
    """Main dashboard overview page"""
    
    def __init__(self, api_client: APIClient):
        self.api_client = api_client
        self.metrics_cards = MetricsCards()
        self.chart_generator = ChartGenerator()
    
    def render(self):
        """Render the overview page"""
        st.title("🛡️ Project Dharma - Dashboard Overview")
        st.markdown("### Social Media Intelligence Platform")
        
        # Auto-refresh toggle
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.markdown("**Real-time Social Media Monitoring**")
        with col2:
            auto_refresh = st.checkbox("Auto-refresh", value=True)
        with col3:
            if st.button("🔄 Refresh Now"):
                st.rerun()
        
        # Auto-refresh logic
        if auto_refresh:
            # Refresh every 30 seconds
            if 'last_refresh' not in st.session_state:
                st.session_state.last_refresh = datetime.now()
            
            if (datetime.now() - st.session_state.last_refresh).seconds > 30:
                st.session_state.last_refresh = datetime.now()
                st.rerun()
        
        # Load data
        with st.spinner("Loading dashboard data..."):
            metrics_data = asyncio.run(self.api_client.get_dashboard_metrics())
            sentiment_data = asyncio.run(self.api_client.get_sentiment_trends(days=7))
            platform_data = asyncio.run(self.api_client.get_platform_activity(hours=24))
            geo_data = asyncio.run(self.api_client.get_geographic_distribution())
        
        # Key Metrics Row
        self._render_key_metrics(metrics_data)
        
        st.markdown("---")
        
        # Charts Section
        col1, col2 = st.columns(2)
        
        with col1:
            self._render_sentiment_trends(sentiment_data)
            self._render_platform_activity(platform_data)
        
        with col2:
            self._render_sentiment_distribution(metrics_data)
            self._render_geographic_distribution(geo_data)
        
        # Recent Activity Section
        st.markdown("---")
        self._render_recent_activity()
    
    def _render_key_metrics(self, data: Dict[str, Any]):
        """Render key metrics cards"""
        st.markdown("### 📊 Key Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="🚨 Active Alerts",
                value=format_number(data.get('active_alerts', 0)),
                delta="+5 from yesterday"
            )
        
        with col2:
            st.metric(
                label="📝 Posts Analyzed Today",
                value=format_number(data.get('posts_analyzed_today', 0)),
                delta="+12.5% from yesterday"
            )
        
        with col3:
            st.metric(
                label="🤖 Bot Accounts Detected",
                value=format_number(data.get('bot_accounts_detected', 0)),
                delta="+8 from yesterday"
            )
        
        with col4:
            st.metric(
                label="🎯 Active Campaigns",
                value=format_number(data.get('active_campaigns', 0)),
                delta="+2 from yesterday"
            )
    
    def _render_sentiment_trends(self, data: Dict[str, Any]):
        """Render sentiment trends chart"""
        st.markdown("#### 📈 Sentiment Trends (7 Days)")
        
        if not data or 'dates' not in data:
            st.warning("No sentiment trend data available")
            return
        
        # Create DataFrame
        df = pd.DataFrame({
            'Date': pd.to_datetime(data['dates']),
            'Pro-India': data.get('pro_india', []),
            'Neutral': data.get('neutral', []),
            'Anti-India': data.get('anti_india', [])
        })
        
        # Create line chart
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df['Date'], y=df['Pro-India'],
            mode='lines+markers',
            name='Pro-India',
            line=dict(color='#2E8B57', width=3),
            marker=dict(size=6)
        ))
        
        fig.add_trace(go.Scatter(
            x=df['Date'], y=df['Neutral'],
            mode='lines+markers',
            name='Neutral',
            line=dict(color='#4682B4', width=3),
            marker=dict(size=6)
        ))
        
        fig.add_trace(go.Scatter(
            x=df['Date'], y=df['Anti-India'],
            mode='lines+markers',
            name='Anti-India',
            line=dict(color='#DC143C', width=3),
            marker=dict(size=6)
        ))
        
        fig.update_layout(
            height=300,
            xaxis_title="Date",
            yaxis_title="Percentage (%)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=0, r=0, t=30, b=0)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def _render_sentiment_distribution(self, data: Dict[str, Any]):
        """Render current sentiment distribution pie chart"""
        st.markdown("#### 🥧 Current Sentiment Distribution")
        
        sentiment_dist = data.get('sentiment_distribution', {})
        if not sentiment_dist:
            st.warning("No sentiment distribution data available")
            return
        
        # Create pie chart
        labels = ['Pro-India', 'Neutral', 'Anti-India']
        values = [
            sentiment_dist.get('pro_india', 0),
            sentiment_dist.get('neutral', 0),
            sentiment_dist.get('anti_india', 0)
        ]
        colors = ['#2E8B57', '#4682B4', '#DC143C']
        
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            marker_colors=colors,
            textinfo='label+percent',
            textfont_size=12,
            hole=0.4
        )])
        
        fig.update_layout(
            height=300,
            margin=dict(l=0, r=0, t=30, b=0),
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def _render_platform_activity(self, data: Dict[str, Any]):
        """Render platform activity chart"""
        st.markdown("#### 📱 Platform Activity (24 Hours)")
        
        if not data or 'hours' not in data:
            st.warning("No platform activity data available")
            return
        
        hours = data['hours']
        platforms_data = data.get('platforms', {})
        
        fig = go.Figure()
        
        colors = ['#1DA1F2', '#FF0000', '#0088CC', '#FF6B35']
        for i, (platform, values) in enumerate(platforms_data.items()):
            fig.add_trace(go.Scatter(
                x=hours,
                y=values,
                mode='lines+markers',
                name=platform,
                line=dict(color=colors[i % len(colors)], width=2),
                marker=dict(size=4)
            ))
        
        fig.update_layout(
            height=300,
            xaxis_title="Hour of Day",
            yaxis_title="Posts Count",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=0, r=0, t=30, b=0)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def _render_geographic_distribution(self, data: Dict[str, Any]):
        """Render geographic distribution map"""
        st.markdown("#### 🌍 Geographic Distribution")
        
        countries = data.get('countries', [])
        if not countries:
            st.warning("No geographic data available")
            return
        
        # Create DataFrame for map
        df = pd.DataFrame(countries)
        
        # Create scatter map
        fig = px.scatter_geo(
            df,
            lat='lat',
            lon='lon',
            size='posts',
            hover_name='country',
            hover_data={'posts': True, 'lat': False, 'lon': False},
            size_max=50,
            color='posts',
            color_continuous_scale='Viridis'
        )
        
        fig.update_layout(
            height=300,
            margin=dict(l=0, r=0, t=0, b=0),
            geo=dict(
                showframe=False,
                showcoastlines=True,
                projection_type='equirectangular'
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def _render_recent_activity(self):
        """Render recent activity feed"""
        st.markdown("### 📋 Recent Activity")
        
        # Mock recent activity data
        activities = [
            {
                "time": "2 minutes ago",
                "type": "alert",
                "message": "High coordination detected in anti-government posts",
                "severity": "high"
            },
            {
                "time": "15 minutes ago",
                "type": "campaign",
                "message": "New campaign detected: Economic Policy Criticism",
                "severity": "medium"
            },
            {
                "time": "1 hour ago",
                "type": "bot",
                "message": "Bot network activity increased by 25%",
                "severity": "medium"
            },
            {
                "time": "2 hours ago",
                "type": "sentiment",
                "message": "Anti-India sentiment spike detected on Twitter",
                "severity": "low"
            }
        ]
        
        for activity in activities:
            severity_color = {
                "high": "🔴",
                "medium": "🟡", 
                "low": "🟢"
            }.get(activity['severity'], "⚪")
            
            st.markdown(f"""
            <div style="padding: 10px; margin: 5px 0; border-left: 4px solid #ddd; background-color: #f9f9f9;">
                <strong>{severity_color} {activity['time']}</strong><br>
                {activity['message']}
            </div>
            """, unsafe_allow_html=True)