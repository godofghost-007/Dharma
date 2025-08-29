"""
Alert Management Dashboard Interface using Streamlit.

This module provides a comprehensive web-based interface for alert management
including inbox, filtering, search, acknowledgment, assignment, resolution tracking,
and reporting capabilities.
"""

import asyncio
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any
import json

from shared.models.alert import (
    Alert, AlertSummary, AlertType, SeverityLevel, AlertStatus, EscalationLevel
)
from ..core.alert_manager import AlertManager
from ..core.search_service import AlertSearchService
from ..core.reporting_service import ReportingService
from ..core.escalation_engine import EscalationEngine


class AlertManagementDashboard:
    """Main alert management dashboard interface."""
    
    def __init__(self):
        self.alert_manager = AlertManager()
        self.search_service = AlertSearchService()
        self.reporting_service = ReportingService()
        self.escalation_engine = EscalationEngine()
        
        # Initialize session state
        if 'current_user' not in st.session_state:
            st.session_state.current_user = "analyst_1"  # Default user
        if 'selected_alerts' not in st.session_state:
            st.session_state.selected_alerts = []
        if 'refresh_data' not in st.session_state:
            st.session_state.refresh_data = False
    
    def run(self):
        """Main dashboard entry point."""
        st.set_page_config(
            page_title="Project Dharma - Alert Management",
            page_icon="🚨",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # Custom CSS for better styling
        st.markdown("""
        <style>
        .alert-critical { background-color: #ffebee; border-left: 5px solid #f44336; }
        .alert-high { background-color: #fff3e0; border-left: 5px solid #ff9800; }
        .alert-medium { background-color: #f3e5f5; border-left: 5px solid #9c27b0; }
        .alert-low { background-color: #e8f5e8; border-left: 5px solid #4caf50; }
        .metric-card { 
            background-color: #f8f9fa; 
            padding: 1rem; 
            border-radius: 0.5rem; 
            border: 1px solid #dee2e6; 
        }
        .stButton > button {
            width: 100%;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Sidebar navigation
        page = st.sidebar.selectbox(
            "Navigation",
            ["Alert Inbox", "Search & Filter", "Analytics & Reports", "Escalation Management", "Bulk Operations"]
        )
        
        # User selection
        st.sidebar.markdown("---")
        st.session_state.current_user = st.sidebar.selectbox(
            "Current User",
            ["analyst_1", "analyst_2", "supervisor_1", "admin"]
        )
        
        # Auto-refresh toggle
        auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)", value=False)
        if auto_refresh:
            st.rerun()
        
        # Main content based on selected page
        if page == "Alert Inbox":
            self.render_alert_inbox()
        elif page == "Search & Filter":
            self.render_search_interface()
        elif page == "Analytics & Reports":
            self.render_analytics_dashboard()
        elif page == "Escalation Management":
            self.render_escalation_management()
        elif page == "Bulk Operations":
            self.render_bulk_operations()
    
    def render_alert_inbox(self):
        """Render the main alert inbox interface."""
        st.title("🚨 Alert Inbox")
        
        # Quick stats
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Active Alerts", self._get_active_alerts_count())
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Critical Alerts", self._get_critical_alerts_count())
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("My Assignments", self._get_my_assignments_count())
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col4:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Overdue Alerts", self._get_overdue_alerts_count())
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Filter controls
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            status_filter = st.multiselect(
                "Status",
                options=[status.value for status in AlertStatus],
                default=["new", "acknowledged", "investigating"]
            )
        
        with col2:
            severity_filter = st.multiselect(
                "Severity",
                options=[severity.value for severity in SeverityLevel],
                default=[]
            )
        
        with col3:
            type_filter = st.multiselect(
                "Alert Type",
                options=[alert_type.value for alert_type in AlertType],
                default=[]
            )
        
        with col4:
            assignment_filter = st.selectbox(
                "Assignment",
                options=["All", "Assigned to me", "Unassigned", "Assigned to others"]
            )
        
        # Date range filter
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("From Date", value=date.today() - timedelta(days=7))
        with col2:
            end_date = st.date_input("To Date", value=date.today())
        
        # Load and display alerts
        alerts = self._load_filtered_alerts(
            status_filter, severity_filter, type_filter, 
            assignment_filter, start_date, end_date
        )
        
        if alerts:
            self._render_alert_table(alerts)
        else:
            st.info("No alerts found matching the current filters.")
    
    def render_search_interface(self):
        """Render advanced search interface."""
        st.title("🔍 Advanced Search & Filter")
        
        # Search input
        search_query = st.text_input(
            "Search alerts",
            placeholder="Enter keywords, alert IDs, or phrases...",
            help="Search across alert titles, descriptions, and content"
        )
        
        # Advanced filters in expandable section
        with st.expander("Advanced Filters", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Content Filters")
                risk_score_range = st.slider(
                    "Risk Score Range",
                    min_value=0.0, max_value=1.0,
                    value=(0.0, 1.0), step=0.1
                )
                
                platforms = st.multiselect(
                    "Source Platforms",
                    options=["twitter", "youtube", "telegram", "web", "tiktok"]
                )
                
                regions = st.multiselect(
                    "Affected Regions",
                    options=["north", "south", "east", "west", "central", "national"]
                )
            
            with col2:
                st.subheader("Time Filters")
                time_range = st.selectbox(
                    "Time Range",
                    options=["Last 24 hours", "Last 7 days", "Last 30 days", "Custom"]
                )
                
                if time_range == "Custom":
                    custom_start = st.date_input("Custom Start Date")
                    custom_end = st.date_input("Custom End Date")
                
                escalation_filter = st.multiselect(
                    "Escalation Level",
                    options=[level.value for level in EscalationLevel]
                )
        
        # Search button
        if st.button("Search Alerts", type="primary"):
            if search_query or any([platforms, regions, escalation_filter]):
                search_results = self._perform_advanced_search(
                    search_query, risk_score_range, platforms, regions, escalation_filter
                )
                
                if search_results:
                    st.success(f"Found {len(search_results)} alerts")
                    self._render_search_results(search_results)
                else:
                    st.warning("No alerts found matching your search criteria")
            else:
                st.warning("Please enter a search query or select filters")
        
        # Search suggestions
        if search_query and len(search_query) >= 2:
            suggestions = self._get_search_suggestions(search_query)
            if suggestions:
                st.subheader("Search Suggestions")
                for suggestion in suggestions[:5]:
                    if st.button(f"💡 {suggestion}", key=f"suggestion_{suggestion}"):
                        st.rerun()
    
    def render_analytics_dashboard(self):
        """Render analytics and reporting dashboard."""
        st.title("📊 Analytics & Reports")
        
        # Time period selector
        col1, col2 = st.columns(2)
        with col1:
            period_days = st.selectbox(
                "Analysis Period",
                options=[7, 14, 30, 60, 90],
                index=2,
                format_func=lambda x: f"Last {x} days"
            )
        
        with col2:
            report_type = st.selectbox(
                "Report Type",
                options=["Overview", "Performance", "Trends", "Escalations", "User Performance"]
            )
        
        # Generate report based on selection
        if report_type == "Overview":
            self._render_overview_analytics(period_days)
        elif report_type == "Performance":
            self._render_performance_analytics(period_days)
        elif report_type == "Trends":
            self._render_trends_analytics(period_days)
        elif report_type == "Escalations":
            self._render_escalation_analytics(period_days)
        elif report_type == "User Performance":
            self._render_user_performance_analytics(period_days)
        
        # Export options
        st.markdown("---")
        st.subheader("Export Reports")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Export CSV"):
                csv_data = self._export_report_csv(period_days)
                st.download_button(
                    label="Download CSV",
                    data=csv_data,
                    file_name=f"alert_report_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
        
        with col2:
            if st.button("Export JSON"):
                json_data = self._export_report_json(period_days)
                st.download_button(
                    label="Download JSON",
                    data=json_data,
                    file_name=f"alert_report_{datetime.now().strftime('%Y%m%d')}.json",
                    mime="application/json"
                )
        
        with col3:
            if st.button("Generate PDF"):
                st.info("PDF generation would be implemented with a proper PDF library")
    
    def render_escalation_management(self):
        """Render escalation management interface."""
        st.title("⚡ Escalation Management")
        
        tab1, tab2, tab3 = st.tabs(["Escalation Rules", "Manual Escalation", "Escalation History"])
        
        with tab1:
            self._render_escalation_rules()
        
        with tab2:
            self._render_manual_escalation()
        
        with tab3:
            self._render_escalation_history()
    
    def render_bulk_operations(self):
        """Render bulk operations interface."""
        st.title("⚙️ Bulk Operations")
        
        # Alert selection
        st.subheader("Select Alerts")
        
        # Load alerts for bulk operations
        alerts = self._load_alerts_for_bulk_ops()
        
        if alerts:
            # Create selection interface
            selected_alerts = st.multiselect(
                "Choose alerts for bulk operation",
                options=[f"{alert['alert_id']} - {alert['title']}" for alert in alerts],
                format_func=lambda x: x.split(' - ', 1)[1][:50] + "..." if len(x.split(' - ', 1)[1]) > 50 else x.split(' - ', 1)[1]
            )
            
            if selected_alerts:
                alert_ids = [alert.split(' - ')[0] for alert in selected_alerts]
                
                st.subheader("Bulk Operation")
                operation = st.selectbox(
                    "Select Operation",
                    options=["Acknowledge", "Assign", "Resolve", "Add Tags", "Change Priority"]
                )
                
                # Operation-specific parameters
                if operation == "Acknowledge":
                    notes = st.text_area("Acknowledgment Notes (optional)")
                    if st.button("Acknowledge Selected Alerts"):
                        self._perform_bulk_acknowledge(alert_ids, notes)
                
                elif operation == "Assign":
                    assignee = st.selectbox(
                        "Assign to",
                        options=["analyst_1", "analyst_2", "supervisor_1"]
                    )
                    notes = st.text_area("Assignment Notes (optional)")
                    if st.button("Assign Selected Alerts"):
                        self._perform_bulk_assign(alert_ids, assignee, notes)
                
                elif operation == "Resolve":
                    resolution_type = st.selectbox(
                        "Resolution Type",
                        options=["False Positive", "Resolved", "Duplicate", "No Action Required"]
                    )
                    resolution_notes = st.text_area("Resolution Notes", placeholder="Required")
                    if st.button("Resolve Selected Alerts"):
                        if resolution_notes:
                            self._perform_bulk_resolve(alert_ids, resolution_type, resolution_notes)
                        else:
                            st.error("Resolution notes are required")
                
                elif operation == "Add Tags":
                    tags = st.text_input("Tags (comma-separated)")
                    if st.button("Add Tags to Selected Alerts"):
                        if tags:
                            tag_list = [tag.strip() for tag in tags.split(',')]
                            self._perform_bulk_tag(alert_ids, tag_list)
                        else:
                            st.error("Please enter at least one tag")
        else:
            st.info("No alerts available for bulk operations")
    
    def _render_alert_table(self, alerts: List[Dict]):
        """Render the main alert table with actions."""
        # Create DataFrame for display
        df_data = []
        for alert in alerts:
            df_data.append({
                "ID": alert['alert_id'][:8] + "...",
                "Title": alert['title'][:50] + "..." if len(alert['title']) > 50 else alert['title'],
                "Type": alert['alert_type'],
                "Severity": alert['severity'],
                "Status": alert['status'],
                "Created": alert['created_at'].strftime('%Y-%m-%d %H:%M') if isinstance(alert['created_at'], datetime) else alert['created_at'],
                "Assigned": alert.get('assigned_to', 'Unassigned'),
                "Actions": alert['alert_id']  # Store full ID for actions
            })
        
        df = pd.DataFrame(df_data)
        
        # Display table with styling
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Severity": st.column_config.SelectboxColumn(
                    options=["critical", "high", "medium", "low"]
                ),
                "Status": st.column_config.SelectboxColumn(
                    options=["new", "acknowledged", "investigating", "resolved", "dismissed"]
                )
            }
        )
        
        # Action buttons for selected alerts
        st.subheader("Quick Actions")
        
        # Alert selection for actions
        selected_indices = st.multiselect(
            "Select alerts for actions",
            options=range(len(alerts)),
            format_func=lambda i: f"{alerts[i]['alert_id'][:8]}... - {alerts[i]['title'][:30]}..."
        )
        
        if selected_indices:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("Acknowledge Selected"):
                    for idx in selected_indices:
                        self._acknowledge_alert(alerts[idx]['alert_id'])
                    st.success(f"Acknowledged {len(selected_indices)} alerts")
                    st.rerun()
            
            with col2:
                assignee = st.selectbox("Assign to", ["analyst_1", "analyst_2", "supervisor_1"])
                if st.button("Assign Selected"):
                    for idx in selected_indices:
                        self._assign_alert(alerts[idx]['alert_id'], assignee)
                    st.success(f"Assigned {len(selected_indices)} alerts to {assignee}")
                    st.rerun()
            
            with col3:
                if st.button("Escalate Selected"):
                    for idx in selected_indices:
                        self._escalate_alert(alerts[idx]['alert_id'])
                    st.success(f"Escalated {len(selected_indices)} alerts")
                    st.rerun()
            
            with col4:
                if st.button("View Details"):
                    if len(selected_indices) == 1:
                        self._show_alert_details(alerts[selected_indices[0]])
                    else:
                        st.warning("Please select only one alert to view details")
    
    def _render_search_results(self, results: List[Dict]):
        """Render search results with highlighting."""
        st.subheader("Search Results")
        
        for result in results:
            # Create alert card
            severity_class = f"alert-{result['severity']}"
            
            st.markdown(f"""
            <div class="{severity_class}" style="padding: 1rem; margin: 0.5rem 0; border-radius: 0.5rem;">
                <h4>{result['title']}</h4>
                <p><strong>Type:</strong> {result['alert_type']} | 
                   <strong>Severity:</strong> {result['severity']} | 
                   <strong>Status:</strong> {result['status']}</p>
                <p><strong>Created:</strong> {result['created_at']}</p>
                <p>{result.get('description', '')[:200]}...</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Action buttons for each result
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                if st.button(f"View Details", key=f"view_{result['alert_id']}"):
                    self._show_alert_details(result)
            with col2:
                if st.button(f"Acknowledge", key=f"ack_{result['alert_id']}"):
                    self._acknowledge_alert(result['alert_id'])
            with col3:
                if st.button(f"Assign to Me", key=f"assign_{result['alert_id']}"):
                    self._assign_alert(result['alert_id'], st.session_state.current_user)
            with col4:
                if st.button(f"Escalate", key=f"escalate_{result['alert_id']}"):
                    self._escalate_alert(result['alert_id'])
    
    def _render_overview_analytics(self, period_days: int):
        """Render overview analytics."""
        st.subheader("Alert Overview")
        
        # Mock data for demonstration
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)
        
        # Alert volume chart
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        alert_counts = [20 + i % 10 for i in range(len(dates))]
        
        fig = px.line(
            x=dates, y=alert_counts,
            title="Alert Volume Over Time",
            labels={'x': 'Date', 'y': 'Number of Alerts'}
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Severity distribution
        severity_data = {
            'Severity': ['Critical', 'High', 'Medium', 'Low'],
            'Count': [15, 45, 80, 60]
        }
        fig = px.pie(
            values=severity_data['Count'],
            names=severity_data['Severity'],
            title="Alert Distribution by Severity"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Status distribution
        col1, col2 = st.columns(2)
        with col1:
            status_data = {
                'Status': ['New', 'Acknowledged', 'Investigating', 'Resolved'],
                'Count': [25, 35, 40, 100]
            }
            fig = px.bar(
                x=status_data['Status'],
                y=status_data['Count'],
                title="Alerts by Status"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Response time metrics
            response_times = [15, 25, 30, 20, 35, 18, 22]
            fig = px.box(
                y=response_times,
                title="Response Time Distribution (minutes)"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    def _render_escalation_rules(self):
        """Render escalation rules management."""
        st.subheader("Escalation Rules Configuration")
        
        # Display current rules
        rules_data = [
            {"Alert Type": "high_risk_content", "Severity": "critical", "Delay (min)": 15, "Max Level": "level_2"},
            {"Alert Type": "coordinated_campaign", "Severity": "critical", "Delay (min)": 10, "Max Level": "level_3"},
            {"Alert Type": "bot_network_detected", "Severity": "high", "Delay (min)": 45, "Max Level": "level_2"},
        ]
        
        df = pd.DataFrame(rules_data)
        st.dataframe(df, use_container_width=True)
        
        # Add new rule form
        with st.expander("Add New Escalation Rule"):
            col1, col2 = st.columns(2)
            with col1:
                alert_type = st.selectbox("Alert Type", [t.value for t in AlertType])
                severity = st.selectbox("Severity", [s.value for s in SeverityLevel])
                delay_minutes = st.number_input("Escalation Delay (minutes)", min_value=1, value=30)
            
            with col2:
                escalation_level = st.selectbox("Escalation Level", [l.value for l in EscalationLevel])
                max_unack_time = st.number_input("Max Unacknowledged Time (minutes)", min_value=1, value=60)
                max_investigation_time = st.number_input("Max Investigation Time (minutes)", min_value=1, value=240)
            
            if st.button("Add Escalation Rule"):
                # Here you would call the escalation engine to add the rule
                st.success("Escalation rule added successfully!")
    
    def _render_manual_escalation(self):
        """Render manual escalation interface."""
        st.subheader("Manual Alert Escalation")
        
        # Alert selection
        alert_id = st.text_input("Alert ID")
        
        if alert_id:
            # Mock alert details
            st.info(f"Alert: {alert_id} - High Risk Content Detection")
            
            col1, col2 = st.columns(2)
            with col1:
                escalation_level = st.selectbox("Escalate to Level", [l.value for l in EscalationLevel])
                reason = st.text_area("Escalation Reason", placeholder="Explain why this alert needs escalation...")
            
            with col2:
                notes = st.text_area("Additional Notes", placeholder="Any additional context...")
                urgent = st.checkbox("Mark as Urgent")
            
            if st.button("Escalate Alert", type="primary"):
                if reason:
                    # Here you would call the escalation engine
                    st.success(f"Alert {alert_id} escalated to {escalation_level}")
                else:
                    st.error("Escalation reason is required")
    
    def _render_escalation_history(self):
        """Render escalation history."""
        st.subheader("Escalation History")
        
        # Mock escalation history data
        history_data = [
            {
                "Alert ID": "alert_001",
                "Escalated By": "analyst_1",
                "From Level": "level_1",
                "To Level": "level_2",
                "Reason": "No response within SLA",
                "Timestamp": "2024-01-15 14:30:00"
            },
            {
                "Alert ID": "alert_002",
                "Escalated By": "system",
                "From Level": "level_1",
                "To Level": "level_3",
                "Reason": "Critical severity auto-escalation",
                "Timestamp": "2024-01-15 13:15:00"
            }
        ]
        
        df = pd.DataFrame(history_data)
        st.dataframe(df, use_container_width=True)
        
        # Escalation trends
        escalation_counts = [5, 8, 12, 6, 9, 15, 11]
        dates = pd.date_range(start=datetime.now() - timedelta(days=6), periods=7, freq='D')
        
        fig = px.bar(
            x=dates,
            y=escalation_counts,
            title="Daily Escalation Count"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Helper methods for data loading and operations
    def _load_filtered_alerts(self, status_filter, severity_filter, type_filter, assignment_filter, start_date, end_date):
        """Load alerts based on filters."""
        # Mock data - in real implementation, this would call the alert manager
        mock_alerts = [
            {
                'alert_id': 'alert_001',
                'title': 'High Risk Content Detected on Twitter',
                'alert_type': 'high_risk_content',
                'severity': 'critical',
                'status': 'new',
                'created_at': datetime.now() - timedelta(hours=2),
                'assigned_to': None,
                'description': 'Anti-India sentiment detected in viral tweet thread'
            },
            {
                'alert_id': 'alert_002',
                'title': 'Coordinated Bot Network Activity',
                'alert_type': 'bot_network_detected',
                'severity': 'high',
                'status': 'acknowledged',
                'created_at': datetime.now() - timedelta(hours=4),
                'assigned_to': 'analyst_1',
                'description': 'Suspicious coordinated posting pattern detected'
            },
            {
                'alert_id': 'alert_003',
                'title': 'Viral Misinformation Campaign',
                'alert_type': 'viral_misinformation',
                'severity': 'critical',
                'status': 'investigating',
                'created_at': datetime.now() - timedelta(hours=1),
                'assigned_to': 'analyst_2',
                'description': 'False information about government policy spreading rapidly'
            }
        ]
        
        # Apply filters
        filtered_alerts = []
        for alert in mock_alerts:
            if status_filter and alert['status'] not in status_filter:
                continue
            if severity_filter and alert['severity'] not in severity_filter:
                continue
            if type_filter and alert['alert_type'] not in type_filter:
                continue
            
            # Assignment filter
            if assignment_filter == "Assigned to me" and alert['assigned_to'] != st.session_state.current_user:
                continue
            elif assignment_filter == "Unassigned" and alert['assigned_to'] is not None:
                continue
            elif assignment_filter == "Assigned to others" and (alert['assigned_to'] is None or alert['assigned_to'] == st.session_state.current_user):
                continue
            
            filtered_alerts.append(alert)
        
        return filtered_alerts
    
    def _get_active_alerts_count(self):
        """Get count of active alerts."""
        return 47  # Mock data
    
    def _get_critical_alerts_count(self):
        """Get count of critical alerts."""
        return 8  # Mock data
    
    def _get_my_assignments_count(self):
        """Get count of alerts assigned to current user."""
        return 12  # Mock data
    
    def _get_overdue_alerts_count(self):
        """Get count of overdue alerts."""
        return 3  # Mock data
    
    def _acknowledge_alert(self, alert_id: str):
        """Acknowledge an alert."""
        # In real implementation, this would call the alert manager
        pass
    
    def _assign_alert(self, alert_id: str, assignee: str):
        """Assign an alert to a user."""
        # In real implementation, this would call the alert manager
        pass
    
    def _escalate_alert(self, alert_id: str):
        """Escalate an alert."""
        # In real implementation, this would call the escalation engine
        pass
    
    def _show_alert_details(self, alert: Dict):
        """Show detailed alert information."""
        with st.expander(f"Alert Details: {alert['alert_id']}", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Title:** {alert['title']}")
                st.write(f"**Type:** {alert['alert_type']}")
                st.write(f"**Severity:** {alert['severity']}")
                st.write(f"**Status:** {alert['status']}")
            
            with col2:
                st.write(f"**Created:** {alert['created_at']}")
                st.write(f"**Assigned:** {alert.get('assigned_to', 'Unassigned')}")
                st.write(f"**Alert ID:** {alert['alert_id']}")
            
            st.write(f"**Description:** {alert.get('description', 'No description available')}")
    
    def _perform_advanced_search(self, query, risk_range, platforms, regions, escalation_levels):
        """Perform advanced search."""
        # Mock search results
        return [
            {
                'alert_id': 'search_001',
                'title': 'Search Result 1',
                'alert_type': 'high_risk_content',
                'severity': 'high',
                'status': 'new',
                'created_at': '2024-01-15 10:30:00',
                'description': 'This is a search result description'
            }
        ]
    
    def _get_search_suggestions(self, query):
        """Get search suggestions."""
        return ["bot network", "misinformation", "viral content", "election interference"]
    
    def _export_report_csv(self, period_days):
        """Export report as CSV."""
        return "alert_id,title,type,severity,status,created_at\nalert_001,Test Alert,high_risk_content,critical,new,2024-01-15"
    
    def _export_report_json(self, period_days):
        """Export report as JSON."""
        return json.dumps([{
            "alert_id": "alert_001",
            "title": "Test Alert",
            "type": "high_risk_content",
            "severity": "critical",
            "status": "new",
            "created_at": "2024-01-15"
        }])
    
    def _load_alerts_for_bulk_ops(self):
        """Load alerts for bulk operations."""
        return [
            {'alert_id': 'bulk_001', 'title': 'Bulk Operation Alert 1'},
            {'alert_id': 'bulk_002', 'title': 'Bulk Operation Alert 2'},
            {'alert_id': 'bulk_003', 'title': 'Bulk Operation Alert 3'}
        ]
    
    def _perform_bulk_acknowledge(self, alert_ids, notes):
        """Perform bulk acknowledgment."""
        st.success(f"Acknowledged {len(alert_ids)} alerts")
    
    def _perform_bulk_assign(self, alert_ids, assignee, notes):
        """Perform bulk assignment."""
        st.success(f"Assigned {len(alert_ids)} alerts to {assignee}")
    
    def _perform_bulk_resolve(self, alert_ids, resolution_type, notes):
        """Perform bulk resolution."""
        st.success(f"Resolved {len(alert_ids)} alerts as {resolution_type}")
    
    def _perform_bulk_tag(self, alert_ids, tags):
        """Perform bulk tagging."""
        st.success(f"Added tags {tags} to {len(alert_ids)} alerts")


def main():
    """Main entry point for the dashboard."""
    dashboard = AlertManagementDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()