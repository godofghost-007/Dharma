"""
Metrics Cards Component
Reusable components for displaying key metrics
"""

import streamlit as st
from typing import Dict, Any, Optional

class MetricsCards:
    """Component for rendering metrics cards"""
    
    def render_metric_card(
        self,
        title: str,
        value: str,
        delta: Optional[str] = None,
        delta_color: str = "normal",
        icon: str = "📊"
    ):
        """Render a single metric card"""
        st.metric(
            label=f"{icon} {title}",
            value=value,
            delta=delta,
            delta_color=delta_color
        )
    
    def render_metrics_row(self, metrics: Dict[str, Dict[str, Any]]):
        """Render a row of metrics cards"""
        cols = st.columns(len(metrics))
        
        for i, (key, metric_data) in enumerate(metrics.items()):
            with cols[i]:
                self.render_metric_card(
                    title=metric_data.get('title', key),
                    value=metric_data.get('value', '0'),
                    delta=metric_data.get('delta'),
                    delta_color=metric_data.get('delta_color', 'normal'),
                    icon=metric_data.get('icon', '📊')
                )
    
    def render_status_card(
        self,
        title: str,
        status: str,
        description: str,
        color: str = "blue"
    ):
        """Render a status card with colored background"""
        color_map = {
            "green": "#d4edda",
            "yellow": "#fff3cd", 
            "red": "#f8d7da",
            "blue": "#d1ecf1"
        }
        
        bg_color = color_map.get(color, "#d1ecf1")
        
        st.markdown(f"""
        <div style="
            padding: 15px;
            margin: 10px 0;
            background-color: {bg_color};
            border-radius: 5px;
            border-left: 4px solid {color};
        ">
            <h4 style="margin: 0 0 5px 0;">{title}</h4>
            <p style="margin: 0; font-weight: bold;">{status}</p>
            <p style="margin: 5px 0 0 0; font-size: 0.9em;">{description}</p>
        </div>
        """, unsafe_allow_html=True)