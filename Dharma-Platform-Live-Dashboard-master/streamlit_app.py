#!/usr/bin/env python3
"""
🛡️ Dharma Platform - Enhanced Streamlit Cloud Entry Point
Main entry point for Streamlit Cloud deployment with Reddit integration
"""

import streamlit as st
import sys
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

def main():
    st.set_page_config(
        page_title="🛡️ Dharma Platform - Anti-Nationalist Detection",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    try:
        # Try enhanced threat dashboard first (with proper links and analysis)
        from enhanced_threat_dashboard import main as enhanced_dashboard_main
        enhanced_dashboard_main()
    except ImportError:
        try:
            # Fallback to fixed immersive dashboard (Plotly compatible)
            from fixed_immersive_dashboard import main as fixed_dashboard_main
            fixed_dashboard_main()
        except ImportError:
            try:
                # Fallback to simple cloud dashboard (most reliable)
                from simple_cloud_dashboard import main as simple_dashboard_main
                simple_dashboard_main()
            except ImportError:
                try:
                    # Fallback to Streamlit Cloud optimized dashboard
                    from streamlit_cloud_dashboard import main as cloud_dashboard_main
                    cloud_dashboard_main()
                except ImportError:
                    try:
                        # Fallback to basic dashboard
                        from streamlit_live_dashboard import main as basic_dashboard_main
                        basic_dashboard_main()
                    except ImportError:
                        # Final fallback - inline simple dashboard
                        st.title("🛡️ Dharma Platform")
                        st.subheader("Anti-Nationalist Content Detection System")
                        
                        youtube_api_key = st.secrets.get("YOUTUBE_API_KEY", "")
                        
                        if not youtube_api_key:
                            st.error("⚠️ YouTube API key not configured")
                            st.info("Please add YOUTUBE_API_KEY to Streamlit secrets")
                        else:
                            st.success("✅ YouTube API configured")
                            st.info("Dashboard is loading... Please refresh if needed.")
                            
                            search_query = st.text_input("Search Query:", "anti india propaganda")
                            if st.button("🔍 Search"):
                                st.info("Search functionality will be available once the dashboard loads properly.")
    except Exception as e:
        st.error(f"Application error: {e}")
        st.info("Please refresh the page or check the deployment logs.")

if __name__ == "__main__":
    main()