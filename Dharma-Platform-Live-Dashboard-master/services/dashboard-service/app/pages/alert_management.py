"""
Alert Management Page
Interface for managing alerts, notifications, and incident response
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from ..core.api_client import APIClient
from ..components.charts import ChartGenerator
from ..utils.formatters import format_datetime, format_time_ago, format_number

class AlertManagementPage:
    """Alert management and incident response interface"""
    
    def __init__(self, api_client: APIClient):
        self.api_client = api_client
        self.chart_generator = ChartGenerator()
    
    def render(self):
        """Render the alert management page"""
        st.title("🚨 Alert Management")
        st.markdown("### Monitor and Respond to Security Alerts")
        
        # Load alerts data
        with st.spinner("Loading alerts..."):
            alerts = asyncio.run(self.api_client.get_alerts())
        
        # Alert management interface
        self._render_alert_controls()
        
        # Alert statistics
        self._render_alert_statistics(alerts)
        
        # Main alert interface
        col1, col2 = st.columns([2, 1])
        
        with col1:
            self._render_alert_inbox(alerts)
        
        with col2:
            self._render_alert_analytics(alerts)
            self._render_recent_activity()
        
        # Alert trends and reporting
        st.markdown("---")
        self._render_alert_trends(alerts)
    
    def _render_alert_controls(self):
        """Render alert filtering and control interface"""
        st.markdown("#### 🔧 Alert Controls")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            status_filter = st.selectbox(
                "Status Filter",
                ["All", "New", "Acknowledged", "In Progress", "Resolved"],
                key="alert_status_filter"
            )
        
        with col2:
            severity_filter = st.selectbox(
                "Severity Filter", 
                ["All", "Critical", "High", "Medium", "Low"],
                key="alert_severity_filter"
            )
        
        with col3:
            type_filter = st.selectbox(
                "Type Filter",
                ["All", "Bot Network", "Coordination", "Sentiment Spike", "Campaign"],
                key="alert_type_filter"
            )
        
        with col4:
            time_filter = st.selectbox(
                "Time Range",
                ["Last 24h", "Last 7d", "Last 30d", "All Time"],
                key="alert_time_filter"
            )
        
        with col5:
            if st.button("🔄 Refresh Alerts"):
                st.rerun()
        
        # Bulk actions
        st.markdown("**Bulk Actions:**")
        bulk_col1, bulk_col2, bulk_col3, bulk_col4 = st.columns(4)
        
        with bulk_col1:
            if st.button("✅ Acknowledge Selected"):
                st.success("Selected alerts acknowledged")
        
        with bulk_col2:
            if st.button("🔄 Assign to Me"):
                st.success("Selected alerts assigned")
        
        with bulk_col3:
            if st.button("📧 Send Notification"):
                st.success("Notifications sent")
        
        with bulk_col4:
            if st.button("📊 Generate Report"):
                st.success("Report generation started")
    
    def _render_alert_statistics(self, alerts: List[Dict[str, Any]]):
        """Render alert statistics overview"""
        st.markdown("#### 📊 Alert Statistics")
        
        # Calculate statistics
        total_alerts = len(alerts)
        new_alerts = len([a for a in alerts if a.get('status') == 'new'])
        critical_alerts = len([a for a in alerts if a.get('severity') == 'critical'])
        resolved_today = len([a for a in alerts if a.get('status') == 'resolved'])
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Alerts",
                format_number(total_alerts),
                delta="+5 from yesterday"
            )
        
        with col2:
            st.metric(
                "New Alerts",
                format_number(new_alerts),
                delta="+2 from last hour",
                delta_color="inverse"
            )
        
        with col3:
            st.metric(
                "Critical Alerts",
                format_number(critical_alerts),
                delta="+1 from yesterday",
                delta_color="inverse"
            )
        
        with col4:
            st.metric(
                "Resolved Today",
                format_number(resolved_today),
                delta="+8 from yesterday"
            )
    
    def _render_alert_inbox(self, alerts: List[Dict[str, Any]]):
        """Render alert inbox with filtering, sorting, and search"""
        st.markdown("#### 📥 Alert Inbox")
        
        # Search functionality
        search_query = st.text_input("🔍 Search alerts...", placeholder="Search by title, description, or ID")
        
        # Filter alerts based on search
        filtered_alerts = alerts
        if search_query:
            filtered_alerts = [
                alert for alert in alerts
                if search_query.lower() in alert.get('title', '').lower() or
                   search_query.lower() in alert.get('description', '').lower() or
                   search_query.lower() in alert.get('id', '').lower()
            ]
        
        # Sort options
        sort_col1, sort_col2 = st.columns(2)
        with sort_col1:
            sort_by = st.selectbox("Sort by", ["Created Date", "Severity", "Status", "Type"])
        with sort_col2:
            sort_order = st.selectbox("Order", ["Descending", "Ascending"])
        
        # Display alerts
        if not filtered_alerts:
            st.info("No alerts match the current filters.")
            return
        
        # Alert list
        for i, alert in enumerate(filtered_alerts[:20]):  # Show first 20 alerts
            self._render_alert_card(alert, i)
        
        # Pagination
        if len(filtered_alerts) > 20:
            st.markdown(f"Showing 20 of {len(filtered_alerts)} alerts")
            if st.button("Load More"):
                st.info("Loading more alerts...")
    
    def _render_alert_card(self, alert: Dict[str, Any], index: int):
        """Render individual alert card"""
        alert_id = alert.get('id', f'alert_{index}')
        severity = alert.get('severity', 'medium')
        status = alert.get('status', 'new')
        title = alert.get('title', 'Unknown Alert')
        description = alert.get('description', 'No description available')
        created_at = alert.get('created_at', '')
        
        # Severity colors
        severity_colors = {
            'critical': '#dc3545',
            'high': '#fd7e14', 
            'medium': '#ffc107',
            'low': '#28a745'
        }
        
        # Status colors
        status_colors = {
            'new': '#6c757d',
            'acknowledged': '#17a2b8',
            'in_progress': '#ffc107',
            'resolved': '#28a745'
        }
        
        severity_color = severity_colors.get(severity, '#6c757d')
        status_color = status_colors.get(status, '#6c757d')
        
        # Create expandable alert card
        with st.expander(f"🚨 {title} ({severity.upper()})", expanded=False):
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.markdown(f"**Description:** {description}")
                st.markdown(f"**Alert ID:** `{alert_id}`")
                if created_at:
                    st.markdown(f"**Created:** {format_time_ago(created_at)}")
            
            with col2:
                st.markdown(f"**Severity:** <span style='color: {severity_color}'>●</span> {severity.title()}", 
                           unsafe_allow_html=True)
                st.markdown(f"**Status:** <span style='color: {status_color}'>●</span> {status.title()}", 
                           unsafe_allow_html=True)
            
            with col3:
                # Alert actions
                if st.button(f"✅ Acknowledge", key=f"ack_{alert_id}"):
                    success = asyncio.run(self.api_client.acknowledge_alert(alert_id))
                    if success:
                        st.success("Alert acknowledged!")
                        st.rerun()
                    else:
                        st.error("Failed to acknowledge alert")
                
                if st.button(f"👤 Assign to Me", key=f"assign_{alert_id}"):
                    st.success("Alert assigned!")
                
                if st.button(f"📝 Add Note", key=f"note_{alert_id}"):
                    st.info("Note functionality coming soon")
    
    def _render_alert_analytics(self, alerts: List[Dict[str, Any]]):
        """Render alert analytics and trend reporting"""
        st.markdown("#### 📈 Alert Analytics")
        
        # Severity distribution
        severity_counts = {}
        for alert in alerts:
            severity = alert.get('severity', 'unknown')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        if severity_counts:
            fig_severity = go.Figure(data=[go.Pie(
                labels=list(severity_counts.keys()),
                values=list(severity_counts.values()),
                marker_colors=['#dc3545', '#fd7e14', '#ffc107', '#28a745'],
                textinfo='label+percent',
                hole=0.4
            )])
            
            fig_severity.update_layout(
                title="Severity Distribution",
                height=250,
                margin=dict(l=0, r=0, t=50, b=0),
                showlegend=False
            )
            
            st.plotly_chart(fig_severity, use_container_width=True)
        
        # Status distribution
        status_counts = {}
        for alert in alerts:
            status = alert.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        if status_counts:
            st.markdown("**Status Breakdown:**")
            for status, count in status_counts.items():
                percentage = (count / len(alerts)) * 100 if alerts else 0
                st.markdown(f"• {status.title()}: {count} ({percentage:.1f}%)")
    
    def _render_recent_activity(self):
        """Render recent alert activity feed"""
        st.markdown("#### 🕐 Recent Activity")
        
        # Mock recent activity data
        recent_activities = [
            {
                "time": "2 minutes ago",
                "action": "Alert acknowledged",
                "user": "analyst_1",
                "alert_id": "alert_001"
            },
            {
                "time": "15 minutes ago", 
                "action": "New alert created",
                "user": "system",
                "alert_id": "alert_002"
            },
            {
                "time": "1 hour ago",
                "action": "Alert resolved",
                "user": "analyst_2", 
                "alert_id": "alert_003"
            },
            {
                "time": "2 hours ago",
                "action": "Alert escalated",
                "user": "supervisor_1",
                "alert_id": "alert_004"
            }
        ]
        
        for activity in recent_activities:
            st.markdown(f"""
            <div style="padding: 8px; margin: 4px 0; border-left: 3px solid #007bff; background-color: #f8f9fa;">
                <small><strong>{activity['time']}</strong></small><br>
                {activity['action']} by {activity['user']}<br>
                <small>Alert: {activity['alert_id']}</small>
            </div>
            """, unsafe_allow_html=True)
    
    def _render_alert_trends(self, alerts: List[Dict[str, Any]]):
        """Render alert trends and historical analysis"""
        st.markdown("#### 📊 Alert Trends & Reporting")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Alert volume over time
            st.markdown("**Alert Volume (Last 7 Days)**")
            
            # Generate mock time series data
            dates = []
            alert_counts = []
            base_date = datetime.now() - timedelta(days=7)
            
            for i in range(7):
                date = base_date + timedelta(days=i)
                dates.append(date.strftime("%Y-%m-%d"))
                # Mock data with some variation
                import random
                alert_counts.append(random.randint(5, 25))
            
            fig_volume = go.Figure()
            fig_volume.add_trace(go.Scatter(
                x=dates,
                y=alert_counts,
                mode='lines+markers',
                name='Alert Count',
                line=dict(color='#007bff', width=3),
                marker=dict(size=8)
            ))
            
            fig_volume.update_layout(
                height=300,
                xaxis_title="Date",
                yaxis_title="Alert Count",
                margin=dict(l=0, r=0, t=30, b=0)
            )
            
            st.plotly_chart(fig_volume, use_container_width=True)
        
        with col2:
            # Response time metrics
            st.markdown("**Response Time Metrics**")
            
            # Mock response time data
            response_times = {
                'Average Response Time': '15 minutes',
                'Fastest Response': '2 minutes',
                'Slowest Response': '4 hours',
                'SLA Compliance': '94.2%'
            }
            
            for metric, value in response_times.items():
                st.metric(metric, value)
            
            # Response time distribution
            response_buckets = ['< 5 min', '5-15 min', '15-60 min', '> 1 hour']
            response_counts = [12, 28, 15, 5]
            
            fig_response = go.Figure(data=[go.Bar(
                x=response_buckets,
                y=response_counts,
                marker_color='#28a745'
            )])
            
            fig_response.update_layout(
                title="Response Time Distribution",
                height=250,
                xaxis_title="Response Time",
                yaxis_title="Count",
                margin=dict(l=0, r=0, t=50, b=0)
            )
            
            st.plotly_chart(fig_response, use_container_width=True)
        
        # Export and reporting options
        st.markdown("---")
        st.markdown("**📤 Export & Reporting**")
        
        export_col1, export_col2, export_col3, export_col4 = st.columns(4)
        
        with export_col1:
            if st.button("📊 Daily Report"):
                st.success("Daily report generated!")
        
        with export_col2:
            if st.button("📈 Weekly Summary"):
                st.success("Weekly summary generated!")
        
        with export_col3:
            if st.button("📋 Export CSV"):
                st.success("CSV export started!")
        
        with export_col4:
            if st.button("📧 Email Report"):
                st.success("Email report sent!")