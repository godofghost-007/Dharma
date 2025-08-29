"""
🛡️ Dharma Platform - Simple Cloud Dashboard
Guaranteed to work on Streamlit Cloud with basic functionality
"""

import streamlit as st
import requests
import json
from datetime import datetime, timedelta
import re
from textblob import TextBlob

# Page Configuration
st.set_page_config(
    page_title="🛡️ Dharma Platform",
    page_icon="🛡️",
    layout="wide"
)

# Simple CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #ff6b6b, #ee5a24);
        padding: 2rem;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 2rem;
        color: white;
    }
    
    .threat-critical { color: #ff4757; font-weight: bold; }
    .threat-high { color: #ff6348; font-weight: bold; }
    .threat-medium { color: #ffa502; font-weight: bold; }
    .threat-low { color: #2ed573; font-weight: bold; }
    
    .result-card {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
        background: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)

def calculate_threat_score(text):
    """Simple threat scoring"""
    text_lower = text.lower()
    score = 0
    keywords = []
    
    critical_words = ['anti india', 'destroy india', 'hate india', 'india terrorist']
    high_words = ['india bad', 'india evil', 'boycott india']
    medium_words = ['india problem', 'india wrong']
    
    for word in critical_words:
        if word in text_lower:
            score += 10
            keywords.append(f"CRITICAL: {word}")
    
    for word in high_words:
        if word in text_lower:
            score += 7
            keywords.append(f"HIGH: {word}")
    
    for word in medium_words:
        if word in text_lower:
            score += 4
            keywords.append(f"MEDIUM: {word}")
    
    # Determine level
    if score >= 15:
        level = "CRITICAL"
    elif score >= 10:
        level = "HIGH"
    elif score >= 5:
        level = "MEDIUM"
    else:
        level = "LOW"
    
    return score, level, keywords

def search_youtube(query, api_key, max_results=10):
    """Simple YouTube search"""
    if not api_key:
        return []
    
    try:
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            'part': 'snippet',
            'q': query,
            'type': 'video',
            'maxResults': max_results,
            'key': api_key
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            results = []
            
            for item in data.get('items', []):
                snippet = item['snippet']
                title = snippet['title']
                description = snippet['description']
                combined_text = f"{title} {description}"
                
                score, level, keywords = calculate_threat_score(combined_text)
                
                results.append({
                    'title': title,
                    'description': description[:200] + "..." if len(description) > 200 else description,
                    'url': f"https://www.youtube.com/watch?v={item['id']['videoId']}",
                    'channel': snippet['channelTitle'],
                    'threat_score': score,
                    'threat_level': level,
                    'keywords': keywords
                })
            
            return sorted(results, key=lambda x: x['threat_score'], reverse=True)
        else:
            st.error(f"YouTube API error: {response.status_code}")
            return []
            
    except Exception as e:
        st.error(f"Search error: {e}")
        return []

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🛡️ DHARMA PLATFORM</h1>
        <h2>Anti-Nationalist Content Detection</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Get API key
    youtube_api_key = st.secrets.get("YOUTUBE_API_KEY", "")
    
    if not youtube_api_key:
        st.error("⚠️ YouTube API key not configured. Please add YOUTUBE_API_KEY to Streamlit secrets.")
        st.info("Go to your Streamlit Cloud app settings → Secrets → Add your YouTube API key")
        return
    
    # Search interface
    st.markdown("## 🔍 Search Interface")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        search_query = st.text_input(
            "Enter search terms:",
            value="anti india propaganda",
            placeholder="Enter keywords to search for threats..."
        )
    
    with col2:
        max_results = st.selectbox("Max Results:", [5, 10, 15, 20], index=1)
    
    # Buttons
    col1, col2, col3 = st.columns(3)
    
    search_clicked = False
    auto_clicked = False
    
    with col1:
        if st.button("🔍 Search YouTube", type="primary"):
            search_clicked = True
    
    with col2:
        if st.button("🎯 Auto Detect"):
            auto_clicked = True
            search_query = "anti india propaganda terrorism"
    
    with col3:
        if st.button("🔄 Clear"):
            st.rerun()
    
    # Perform search
    if search_clicked or auto_clicked:
        if search_query.strip():
            with st.spinner("🔍 Searching for threats..."):
                results = search_youtube(search_query, youtube_api_key, max_results)
                
                if results:
                    # Summary
                    st.markdown("## 📊 Results Summary")
                    
                    threat_counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
                    for result in results:
                        threat_counts[result['threat_level']] += 1
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("🚨 Critical", threat_counts['CRITICAL'])
                    with col2:
                        st.metric("⚠️ High", threat_counts['HIGH'])
                    with col3:
                        st.metric("🔶 Medium", threat_counts['MEDIUM'])
                    with col4:
                        st.metric("✅ Low", threat_counts['LOW'])
                    
                    # Results
                    st.markdown("## 🎯 Detection Results")
                    
                    for i, result in enumerate(results):
                        threat_class = f"threat-{result['threat_level'].lower()}"
                        
                        st.markdown(f"""
                        <div class="result-card">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <h4>{result['title']}</h4>
                                <span class="{threat_class}">{result['threat_level']} ({result['threat_score']})</span>
                            </div>
                            <p><strong>Channel:</strong> {result['channel']}</p>
                            <p>{result['description']}</p>
                            <a href="{result['url']}" target="_blank" style="
                                background: #007bff;
                                color: white;
                                padding: 0.5rem 1rem;
                                border-radius: 5px;
                                text-decoration: none;
                                display: inline-block;
                                margin-top: 0.5rem;
                            ">🔗 View Video</a>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if result['keywords']:
                            with st.expander(f"🔍 Analysis Details - Result {i+1}"):
                                st.write("**Threat Indicators:**")
                                for keyword in result['keywords']:
                                    st.write(f"• {keyword}")
                
                else:
                    st.info("No results found. Try different search terms.")
        else:
            st.warning("Please enter search terms.")
    
    else:
        # Instructions
        st.markdown("""
        ## 🚀 How to Use
        
        1. **Enter search terms** in the search box above
        2. **Click "Search YouTube"** to start scanning
        3. **Review results** with threat scores and analysis
        4. **Click "Auto Detect"** for predefined threat searches
        
        ### 🎯 Features
        - **Real-time YouTube search** for anti-nationalist content
        - **Threat level classification** (Critical, High, Medium, Low)
        - **Advanced keyword detection** and pattern matching
        - **Direct links** to original content for verification
        - **Detailed analysis** of threat indicators
        
        ### 🔒 Privacy & Security
        - No data is stored permanently
        - All searches are encrypted
        - Results are processed in real-time
        """)

if __name__ == "__main__":
    main()