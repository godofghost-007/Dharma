"""
Campaign Analysis Page
Interface for investigating and analyzing coordinated campaigns
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import asyncio
import networkx as nx
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from ..core.api_client import APIClient
from ..components.charts import ChartGenerator
from ..utils.formatters import format_number, format_datetime, format_time_ago

class CampaignAnalysisPage:
    """Campaign investigation and analysis interface"""
    
    def __init__(self, api_client: APIClient):
        self.api_client = api_client
        self.chart_generator = ChartGenerator()
    
    def render(self):
        """Render the campaign analysis page"""
        st.title("🎯 Campaign Analysis")
        st.markdown("### Investigate Coordinated Disinformation Campaigns")
        
        # Load campaigns data
        with st.spinner("Loading campaigns..."):
            campaigns = asyncio.run(self.api_client.get_campaigns())
        
        if not campaigns:
            st.warning("No campaigns detected yet.")
            return
        
        # Campaign selection and filtering
        self._render_campaign_filters(campaigns)
        
        # Get selected campaign
        selected_campaign = self._get_selected_campaign(campaigns)
        
        if selected_campaign:
            # Load detailed campaign data
            with st.spinner("Loading campaign details..."):
                campaign_details = asyncio.run(
                    self.api_client.get_campaign_details(selected_campaign['id'])
                )
            
            # Render campaign analysis sections
            self._render_campaign_overview(campaign_details)
            
            col1, col2 = st.columns(2)
            with col1:
                self._render_network_visualization(campaign_details)
                self._render_participant_analysis(campaign_details)
            
            with col2:
                self._render_timeline_analysis(campaign_details)
                self._render_content_analysis(campaign_details)
            
            # Export functionality
            self._render_export_options(campaign_details)
    
    def _render_campaign_filters(self, campaigns: List[Dict[str, Any]]):
        """Render campaign selection and filtering interface"""
        st.markdown("#### 🔍 Campaign Selection & Filters")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Campaign selection
            campaign_options = [
                f"{camp['name']} (ID: {camp['id']})" 
                for camp in campaigns
            ]
            selected_idx = st.selectbox(
                "Select Campaign",
                range(len(campaign_options)),
                format_func=lambda x: campaign_options[x]
            )
            st.session_state.selected_campaign_idx = selected_idx
        
        with col2:
            # Status filter
            status_filter = st.selectbox(
                "Status Filter",
                ["All", "Active", "Monitoring", "Resolved", "Archived"]
            )
        
        with col3:
            # Date range filter
            date_range = st.selectbox(
                "Time Range",
                ["Last 24 hours", "Last 7 days", "Last 30 days", "Custom"]
            )
        
        with col4:
            # Coordination score filter
            min_coordination = st.slider(
                "Min Coordination Score",
                min_value=0.0,
                max_value=1.0,
                value=0.5,
                step=0.1
            )
        
        # Apply filters (for demo, we'll just show the interface)
        if st.button("🔄 Apply Filters"):
            st.success("Filters applied successfully!")
    
    def _get_selected_campaign(self, campaigns: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Get the currently selected campaign"""
        if not campaigns:
            return None
        
        selected_idx = st.session_state.get('selected_campaign_idx', 0)
        if 0 <= selected_idx < len(campaigns):
            return campaigns[selected_idx]
        
        return campaigns[0] if campaigns else None
    
    def _render_campaign_overview(self, campaign: Dict[str, Any]):
        """Render campaign overview section"""
        st.markdown("---")
        st.markdown("#### 📊 Campaign Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Coordination Score",
                f"{campaign.get('coordination_score', 0):.2f}",
                delta="+0.05 from last check"
            )
        
        with col2:
            st.metric(
                "Participants",
                format_number(campaign.get('participants', 0)),
                delta="+3 new accounts"
            )
        
        with col3:
            detection_date = campaign.get('detection_date', '')
            if detection_date:
                time_ago = format_time_ago(detection_date)
                st.metric("Detected", time_ago)
            else:
                st.metric("Detected", "Unknown")
        
        with col4:
            impact_score = campaign.get('impact_score', 0)
            st.metric(
                "Impact Score",
                f"{impact_score:.2f}",
                delta="+0.12 trending up"
            )
        
        # Campaign description
        st.markdown("**Description:**")
        st.info(campaign.get('description', 'No description available'))
        
        # Status indicator
        status = campaign.get('status', 'unknown')
        status_colors = {
            'active': '🔴',
            'monitoring': '🟡',
            'resolved': '🟢',
            'archived': '⚪'
        }
        status_icon = status_colors.get(status.lower(), '❓')
        st.markdown(f"**Status:** {status_icon} {status.title()}")
    
    def _render_network_visualization(self, campaign: Dict[str, Any]):
        """Render network graph visualization using NetworkX"""
        st.markdown("#### 🕸️ Network Graph")
        
        network_data = campaign.get('network_graph', {})
        nodes = network_data.get('nodes', [])
        edges = network_data.get('edges', [])
        
        if not nodes or not edges:
            st.warning("No network data available for this campaign")
            return
        
        # Create network graph
        fig = self.chart_generator.create_network_graph(
            nodes=nodes,
            edges=edges,
            title="Campaign Participant Network",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Network statistics
        st.markdown("**Network Statistics:**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Nodes", len(nodes))
        with col2:
            st.metric("Total Edges", len(edges))
        with col3:
            # Calculate network density
            max_edges = len(nodes) * (len(nodes) - 1) / 2
            density = len(edges) / max_edges if max_edges > 0 else 0
            st.metric("Network Density", f"{density:.3f}")
    
    def _render_timeline_analysis(self, campaign: Dict[str, Any]):
        """Render timeline analysis with interactive charts"""
        st.markdown("#### 📅 Timeline Analysis")
        
        # Mock timeline data for demo
        timeline_data = self._generate_mock_timeline_data()
        
        # Create timeline chart
        df = pd.DataFrame(timeline_data)
        
        fig = go.Figure()
        
        # Add activity timeline
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['activity_count'],
            mode='lines+markers',
            name='Activity Count',
            line=dict(color='#1f77b4', width=3),
            marker=dict(size=8)
        ))
        
        # Add coordination events
        coordination_events = df[df['coordination_spike'] == True]
        if not coordination_events.empty:
            fig.add_trace(go.Scatter(
                x=coordination_events['timestamp'],
                y=coordination_events['activity_count'],
                mode='markers',
                name='Coordination Spikes',
                marker=dict(
                    color='red',
                    size=12,
                    symbol='diamond'
                )
            ))
        
        fig.update_layout(
            title="Campaign Activity Timeline",
            xaxis_title="Time",
            yaxis_title="Activity Count",
            height=300,
            margin=dict(l=0, r=0, t=50, b=0)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Timeline insights
        st.markdown("**Timeline Insights:**")
        st.markdown("• Peak activity detected at 14:30 UTC")
        st.markdown("• Coordination spike coincides with major news event")
        st.markdown("• Activity pattern suggests automated behavior")
    
    def _render_participant_analysis(self, campaign: Dict[str, Any]):
        """Render participant analysis and behavioral insights"""
        st.markdown("#### 👥 Participant Analysis")
        
        # Mock participant data
        participants_data = self._generate_mock_participants_data()
        
        # Participant type distribution
        participant_types = {}
        for participant in participants_data:
            ptype = participant['type']
            participant_types[ptype] = participant_types.get(ptype, 0) + 1
        
        # Create pie chart for participant types
        fig = go.Figure(data=[go.Pie(
            labels=list(participant_types.keys()),
            values=list(participant_types.values()),
            marker_colors=['#ff7f0e', '#2ca02c', '#d62728'],
            textinfo='label+percent',
            hole=0.4
        )])
        
        fig.update_layout(
            title="Participant Types",
            height=250,
            margin=dict(l=0, r=0, t=50, b=0),
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Top participants table
        st.markdown("**Top Participants:**")
        df_participants = pd.DataFrame(participants_data)
        df_top = df_participants.nlargest(5, 'influence_score')
        
        st.dataframe(
            df_top[['username', 'type', 'influence_score', 'post_count']],
            use_container_width=True,
            hide_index=True
        )
    
    def _render_content_analysis(self, campaign: Dict[str, Any]):
        """Render content analysis section"""
        st.markdown("#### 📝 Content Analysis")
        
        # Mock content analysis data
        content_data = {
            'sentiment_distribution': {
                'Anti-India': 65.2,
                'Neutral': 25.8,
                'Pro-India': 9.0
            },
            'top_keywords': [
                {'keyword': 'government', 'frequency': 245},
                {'keyword': 'policy', 'frequency': 189},
                {'keyword': 'corruption', 'frequency': 156},
                {'keyword': 'economy', 'frequency': 134},
                {'keyword': 'protest', 'frequency': 98}
            ],
            'language_distribution': {
                'English': 45.6,
                'Hindi': 32.1,
                'Bengali': 12.3,
                'Tamil': 10.0
            }
        }
        
        # Sentiment distribution
        sentiment_dist = content_data['sentiment_distribution']
        fig_sentiment = go.Figure(data=[go.Pie(
            labels=list(sentiment_dist.keys()),
            values=list(sentiment_dist.values()),
            marker_colors=['#dc3545', '#6c757d', '#28a745'],
            textinfo='label+percent',
            hole=0.3
        )])
        
        fig_sentiment.update_layout(
            title="Sentiment Distribution",
            height=250,
            margin=dict(l=0, r=0, t=50, b=0),
            showlegend=False
        )
        
        st.plotly_chart(fig_sentiment, use_container_width=True)
        
        # Top keywords
        st.markdown("**Top Keywords:**")
        keywords_df = pd.DataFrame(content_data['top_keywords'])
        st.dataframe(
            keywords_df,
            use_container_width=True,
            hide_index=True
        )
    
    def _render_export_options(self, campaign: Dict[str, Any]):
        """Render export functionality for reports and data"""
        st.markdown("---")
        st.markdown("#### 📤 Export Options")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("📊 Export Report (PDF)"):
                st.success("PDF report generation started...")
                # In real implementation, this would generate a PDF report
        
        with col2:
            if st.button("📈 Export Charts (PNG)"):
                st.success("Chart export started...")
                # In real implementation, this would export charts as images
        
        with col3:
            if st.button("📋 Export Data (CSV)"):
                st.success("CSV export started...")
                # In real implementation, this would export raw data
        
        with col4:
            if st.button("🕸️ Export Network (JSON)"):
                st.success("Network data export started...")
                # In real implementation, this would export network graph data
        
        # Export options
        st.markdown("**Export Options:**")
        export_options = st.multiselect(
            "Select data to include:",
            ["Network Graph", "Timeline Data", "Participant List", "Content Samples", "Analysis Results"],
            default=["Network Graph", "Analysis Results"]
        )
        
        date_range = st.date_input(
            "Date Range for Export",
            value=[datetime.now() - timedelta(days=7), datetime.now()],
            max_value=datetime.now()
        )
    
    def _generate_mock_timeline_data(self) -> List[Dict[str, Any]]:
        """Generate mock timeline data for demo"""
        import random
        from datetime import datetime, timedelta
        
        data = []
        base_time = datetime.now() - timedelta(days=7)
        
        for i in range(168):  # 7 days * 24 hours
            timestamp = base_time + timedelta(hours=i)
            activity_count = random.randint(10, 100)
            coordination_spike = random.random() > 0.95  # 5% chance of spike
            
            data.append({
                'timestamp': timestamp,
                'activity_count': activity_count,
                'coordination_spike': coordination_spike
            })
        
        return data
    
    def _generate_mock_participants_data(self) -> List[Dict[str, Any]]:
        """Generate mock participant data for demo"""
        import random
        
        participants = []
        types = ['bot', 'human', 'suspicious']
        
        for i in range(20):
            participants.append({
                'username': f'user_{i+1:03d}',
                'type': random.choice(types),
                'influence_score': random.uniform(0.1, 1.0),
                'post_count': random.randint(5, 150),
                'join_date': datetime.now() - timedelta(days=random.randint(1, 365))
            })
        
        return participants