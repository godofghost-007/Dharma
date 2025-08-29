"""
Project Dharma Dashboard Service
Main Streamlit application for social media intelligence dashboard
"""

import streamlit as st
import asyncio
import sys
import os

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from app.core.config import DashboardConfig
from app.pages.overview import OverviewPage
from app.pages.campaign_analysis import CampaignAnalysisPage
from app.pages.alert_management import AlertManagementPage
from app.core.api_client import APIClient
from app.core.session_manager import SessionManager
from app.accessibility.wcag_compliance import WCAGCompliance
from app.i18n.translator import translator, t

# Configure Streamlit page
st.set_page_config(
    page_title="Project Dharma - Social Media Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize configuration
config = DashboardConfig()

# Initialize session manager
if 'session_manager' not in st.session_state:
    st.session_state.session_manager = SessionManager()

# Initialize API client
if 'api_client' not in st.session_state:
    st.session_state.api_client = APIClient(config.api_gateway_url)

# Initialize accessibility and i18n
wcag = WCAGCompliance()
wcag.apply_accessibility_settings()
translator.apply_rtl_css()

def main():
    """Main dashboard application"""
    
    # Add skip links for accessibility
    wcag.create_skip_links()
    wcag.add_keyboard_navigation_support()
    
    # Sidebar navigation
    st.sidebar.title(f"🛡️ {t('dashboard.title', 'Project Dharma')}")
    st.sidebar.markdown("---")
    
    # Navigation menu
    page = st.sidebar.selectbox(
        t("navigation.navigate_to", "Navigate to:"),
        [
            t("dashboard.overview", "Dashboard Overview"),
            t("dashboard.campaign_analysis", "Campaign Analysis"), 
            t("dashboard.alert_management", "Alert Management"),
            t("dashboard.settings", "Settings")
        ]
    )
    
    # Language selector
    translator.render_language_selector()
    
    # Accessibility controls
    wcag.render_accessibility_controls()
    
    # User info (if authenticated)
    if st.session_state.session_manager.is_authenticated():
        user = st.session_state.session_manager.get_current_user()
        st.sidebar.markdown(f"**User:** {user.get('username', 'Unknown')}")
        st.sidebar.markdown(f"**Role:** {user.get('role', 'Unknown')}")
        
        if st.sidebar.button(t("actions.logout", "Logout")):
            st.session_state.session_manager.logout()
            st.rerun()
    else:
        # Simple authentication for demo
        st.sidebar.markdown("### Authentication")
        username = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type="password")
        
        if st.sidebar.button(t("actions.login", "Login")):
            if username and password:
                # Mock authentication for demo
                st.session_state.session_manager.login({
                    'username': username,
                    'role': 'analyst',
                    'token': 'demo_token'
                })
                st.rerun()
    
    # Main content area with accessibility landmark
    st.markdown('<main id="main-content" role="main">', unsafe_allow_html=True)
    
    if not st.session_state.session_manager.is_authenticated():
        st.title(f"🛡️ {t('dashboard.title', 'Project Dharma')}")
        st.markdown(f"### {t('dashboard.title', 'Social Media Intelligence Platform')}")
        st.info(t("messages.please_login", "Please login using the sidebar to access the dashboard."))
        st.markdown('</main>', unsafe_allow_html=True)
        return
    
    # Route to appropriate page
    dashboard_overview = t("dashboard.overview", "Dashboard Overview")
    campaign_analysis = t("dashboard.campaign_analysis", "Campaign Analysis")
    alert_management = t("dashboard.alert_management", "Alert Management")
    settings = t("dashboard.settings", "Settings")
    
    if page == dashboard_overview:
        overview_page = OverviewPage(st.session_state.api_client)
        overview_page.render()
    elif page == campaign_analysis:
        campaign_page = CampaignAnalysisPage(st.session_state.api_client)
        campaign_page.render()
    elif page == alert_management:
        alert_page = AlertManagementPage(st.session_state.api_client)
        alert_page.render()
    elif page == settings:
        st.title(t("dashboard.settings", "Settings"))
        st.info("Settings page coming soon...")
    
    st.markdown('</main>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()