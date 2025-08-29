"""
Session Management for Dashboard
Handles user authentication and session state
"""

import streamlit as st
from typing import Dict, Optional, Any

class SessionManager:
    """Manages user sessions and authentication state"""
    
    def __init__(self):
        self._init_session_state()
    
    def _init_session_state(self):
        """Initialize session state variables"""
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'user' not in st.session_state:
            st.session_state.user = None
        if 'token' not in st.session_state:
            st.session_state.token = None
    
    def login(self, user_data: Dict[str, Any]) -> bool:
        """Login user and set session state"""
        try:
            st.session_state.authenticated = True
            st.session_state.user = user_data
            st.session_state.token = user_data.get('token')
            return True
        except Exception:
            return False
    
    def logout(self):
        """Logout user and clear session state"""
        st.session_state.authenticated = False
        st.session_state.user = None
        st.session_state.token = None
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return st.session_state.get('authenticated', False)
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get current user data"""
        return st.session_state.get('user')
    
    def get_token(self) -> Optional[str]:
        """Get authentication token"""
        return st.session_state.get('token')
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        user = self.get_current_user()
        if not user:
            return False
        
        # Simple role-based permissions for demo
        role = user.get('role', '')
        
        if role == 'admin':
            return True
        elif role == 'analyst':
            return permission in ['view_dashboard', 'view_campaigns', 'manage_alerts']
        elif role == 'viewer':
            return permission in ['view_dashboard']
        
        return False