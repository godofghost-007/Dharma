# 🛡️ Dharma Platform - Enhanced Anti-Nationalist Detection System

Advanced real-time monitoring system for detecting anti-nationalist content across multiple social media platforms with immersive dashboard design.

## 🚀 Quick Deploy to Streamlit Cloud

### Option 1: Direct Streamlit Cloud Deployment (Recommended)
1. **Fork this repository** to your GitHub account
2. **Go to** [share.streamlit.io](https://share.streamlit.io/)
3. **Click "New app"**
4. **Connect your GitHub** and select this repository
5. **Set main file path:** `streamlit_app.py`
6. **Deploy!** 🎉

### Option 2: Local Development
```bash
# Clone the repository
git clone https://github.com/yourusername/project-dharma.git
cd project-dharma

# Install dependencies
pip install -r requirements.txt

# Run the enhanced dashboard
streamlit run streamlit_app.py
```

## 🎯 Enhanced Features

### 🔍 Multi-Platform Content Detection
- **🎥 YouTube Integration**: Video content analysis with advanced search
- **🔴 Reddit Integration**: Discussion and post monitoring across subreddits
- **Advanced Threat Scoring**: AI-powered content analysis with pattern recognition
- **Real-Time Monitoring**: Live updates and alerts across platforms
- **Immersive Dashboard**: Modern, responsive UI with dark theme and animations

### 🛡️ Advanced Threat Analysis
- **Multi-Level Classification**: Critical, High, Medium, Low threat levels with visual indicators
- **Enhanced Keyword Detection**: Advanced pattern matching with regex support
- **Sentiment Analysis**: Natural language processing with TextBlob
- **Content Scoring**: Automated threat assessment with detailed breakdowns
- **Timeline Analysis**: Historical threat tracking and trend visualization

### 📊 Interactive Analytics & Reporting
- **Visual Dashboards**: Interactive charts with Plotly integration
- **Platform Comparison**: Side-by-side analysis of YouTube vs Reddit threats
- **Threat Distribution**: Real-time pie charts and bar graphs
- **Timeline Visualization**: Scatter plots showing threat evolution
- **Export Capabilities**: Data download and sharing options

### 🎨 Immersive UI/UX Design
- **Dark Theme**: Modern gradient backgrounds with glass morphism effects
- **Animated Elements**: Smooth transitions and hover effects
- **Responsive Layout**: Optimized for all screen sizes
- **Interactive Cards**: Expandable result cards with detailed analysis
- **Real-Time Indicators**: Pulsing animations for critical threats
- **Platform Badges**: Color-coded platform identification

## 🔧 Configuration

### API Keys Setup
The application requires API keys for full functionality:

#### YouTube API Key:
1. **Get YouTube API Key:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing
   - Enable YouTube Data API v3
   - Create credentials (API Key)

#### Reddit API Key:
1. **Get Reddit API Credentials:**
   - Go to [Reddit App Preferences](https://www.reddit.com/prefs/apps)
   - Click "Create App" or "Create Another App"
   - Choose "script" type
   - Note down Client ID and Client Secret

2. **Configure in Streamlit Cloud:**
   - In your Streamlit Cloud app settings
   - Go to "Secrets" section
   - Add the following:
   ```toml
   YOUTUBE_API_KEY = "your_youtube_api_key_here"
   REDDIT_CLIENT_ID = "your_reddit_client_id"
   REDDIT_CLIENT_SECRET = "your_reddit_client_secret"
   REDDIT_USER_AGENT = "DharmaAntiNationalistDetector/1.0"
   ```

3. **Local Development:**
   - Create `.streamlit/secrets.toml` file
   - Add your API keys as shown above

## 🎮 Enhanced Usage

### Multi-Platform Search
1. **Configure Platforms**: Select YouTube and/or Reddit in the sidebar
2. **Enter Search Terms**: Use the enhanced search interface
3. **Start Detection**: Click "🔍 Start Detection Scan"
4. **Review Results**: Interactive cards with threat analysis

### Advanced Controls
- **🎛️ Control Panel**: Sidebar with search configuration
- **📱 Platform Selection**: Toggle YouTube and Reddit monitoring
- **⚠️ Threat Level Filters**: Show/hide specific threat levels
- **🔄 Auto Refresh**: Continuous monitoring with 30-second intervals
- **📊 Sort Options**: Sort by threat score, platform, or date

### Auto-Detection Features
1. **🎯 Auto Detect**: Predefined threat search patterns
2. **🔄 Real-Time Updates**: Live monitoring with auto-refresh
3. **📈 Analytics Dashboard**: Real-time charts and visualizations
4. **🎯 Detection Results**: Enhanced result cards with detailed analysis

## 🛠️ Technical Stack

### Core Technologies
- **Frontend**: Streamlit with custom CSS and animations
- **APIs**: YouTube Data API v3, Reddit API (PRAW)
- **Analysis**: TextBlob, Custom NLP algorithms, Regex patterns
- **Visualization**: Plotly, Pandas, NumPy
- **Deployment**: Streamlit Cloud, Docker support

### Enhanced Features
- **Async Processing**: aiohttp for concurrent API calls
- **Real-Time Updates**: WebSocket-like functionality with Streamlit
- **Responsive Design**: CSS Grid and Flexbox layouts
- **Animation Framework**: CSS animations and transitions
- **Error Handling**: Comprehensive exception management

## 📈 Deployment Status

✅ **Streamlit Cloud Ready**: Optimized for cloud deployment  
✅ **Multi-Platform Support**: YouTube + Reddit integration  
✅ **Enhanced UI/UX**: Immersive dashboard design  
✅ **Requirements Updated**: All dependencies compatible  
✅ **API Integration**: Full YouTube and Reddit functionality  
✅ **Error Handling**: Robust error management  
✅ **Documentation**: Complete setup guides  

## 🎨 UI/UX Highlights

### Visual Design
- **🌈 Gradient Backgrounds**: Dynamic color animations
- **🔮 Glass Morphism**: Translucent cards with backdrop blur
- **⚡ Smooth Animations**: Hover effects and transitions
- **🎯 Threat Indicators**: Color-coded severity levels
- **📱 Responsive Layout**: Mobile-friendly design

### Interactive Elements
- **🔍 Enhanced Search**: Real-time search suggestions
- **📊 Live Charts**: Interactive Plotly visualizations
- **🎛️ Control Panel**: Comprehensive sidebar controls
- **📋 Result Cards**: Expandable analysis details
- **🔄 Auto-Refresh**: Real-time monitoring capabilities

---

**⚡ Enhanced immersive dashboard ready to deploy in under 5 minutes!**  
**🎨 Modern UI with YouTube + Reddit integration**