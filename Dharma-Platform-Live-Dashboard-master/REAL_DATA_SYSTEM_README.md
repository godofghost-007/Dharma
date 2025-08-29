# Dharma Platform - Real Data System

## 🎯 Overview

The Dharma Platform Real Data System collects and analyzes real social media data from multiple platforms to detect anti-India sentiment, bot networks, and coordinated disinformation campaigns.

## ✨ Key Features

### 🔴 **Real Data Collection**
- **Twitter API v2**: Real-time tweet collection with advanced filtering
- **YouTube Data API**: Video and comment analysis from Indian channels
- **Reddit Public API**: Posts from India-related subreddits
- **Telegram API**: Channel and group monitoring (with API keys)

### 🤖 **Advanced AI Analysis**
- **Multi-language Sentiment Analysis**: Supports 11+ Indian languages
- **Bot Detection**: Behavioral analysis and pattern recognition
- **Risk Assessment**: Comprehensive threat scoring
- **Propaganda Detection**: Identifies manipulation techniques

### 🖱️ **Interactive Dashboard**
- **Clickable Threat Posts**: Click any post to view the original
- **Real-time Monitoring**: Live data updates and alerts
- **Platform Filtering**: Filter by Twitter, YouTube, Reddit, etc.
- **Time Range Analysis**: Historical and real-time views

## 🚀 Quick Start

### 1. **Automated Setup**
```bash
python setup_real_data_system.py
```
This will:
- Install all dependencies
- Configure API keys interactively
- Initialize the database
- Collect initial data sample
- Create startup scripts

### 2. **Manual Setup**

#### Install Dependencies
```bash
pip install streamlit fastapi pandas plotly tweepy aiohttp textblob requests python-dotenv
```

#### Configure API Keys
```bash
python api_config.py
```

#### Initialize Database
```bash
python real_data_collector.py
```

### 3. **Start the Dashboard**
```bash
python start_dharma.py
# OR
streamlit run enhanced_real_data_dashboard.py
```

## 🔑 API Configuration

### Required for Full Functionality

#### **Twitter API v2**
1. Create a Twitter Developer account
2. Create a new app and get Bearer Token
3. Set environment variable:
```bash
export TWITTER_BEARER_TOKEN="your_bearer_token_here"
```

#### **YouTube Data API**
1. Create a Google Cloud Project
2. Enable YouTube Data API v3
3. Create API key
4. Set environment variable:
```bash
export YOUTUBE_API_KEY="your_api_key_here"
```

#### **Telegram API (Optional)**
1. Create a Telegram Bot via @BotFather
2. Get bot token
3. Set environment variable:
```bash
export TELEGRAM_BOT_TOKEN="your_bot_token_here"
```

### **Reddit** (No API Key Required)
- Uses public Reddit API
- No authentication needed
- Always available

## 📊 Dashboard Features

### **Main Dashboard**
- **Live Metrics**: Real-time post counts, sentiment distribution
- **Threat Level Indicator**: Visual threat assessment
- **Platform Distribution**: Posts by social media platform
- **Timeline Analysis**: Hourly activity patterns

### **Threat Posts Section**
- **Clickable Posts**: Click any post to view original source
- **Risk Scoring**: Color-coded threat levels (Critical, High, Medium, Low)
- **Sentiment Analysis**: Pro-India, Anti-India, Neutral classification
- **Bot Detection**: Automated vs. human-generated content identification

### **Analytics Dashboard**
- **Sentiment Trends**: Historical sentiment analysis
- **Platform Comparison**: Cross-platform analytics
- **Geographic Analysis**: Location-based threat mapping
- **Engagement Metrics**: Likes, shares, comments analysis

## 🔧 System Components

### **Data Collection** (`real_data_collector.py`)
- Multi-platform data collection
- Rate limiting and API management
- SQLite database storage
- Automatic data normalization

### **AI Analysis** (`real_time_analyzer.py`)
- Advanced sentiment analysis with India-specific keywords
- Bot behavior detection using multiple indicators
- Risk score calculation
- Propaganda technique identification

### **Dashboard** (`enhanced_real_data_dashboard.py`)
- Interactive Streamlit interface
- Real-time data visualization
- Clickable post links to original sources
- Advanced filtering and search

### **Configuration** (`api_config.py`)
- API key management
- Platform configuration
- Environment variable handling

## 📈 Data Flow

1. **Collection**: Real data collected from social media APIs
2. **Storage**: Posts stored in SQLite database with metadata
3. **Analysis**: AI analysis for sentiment, bots, and threats
4. **Visualization**: Interactive dashboard with clickable posts
5. **Monitoring**: Real-time alerts and threat detection

## 🎯 Use Cases

### **Government & Security**
- Monitor anti-India sentiment trends
- Detect coordinated disinformation campaigns
- Track bot networks and fake accounts
- Analyze foreign interference patterns

### **Research & Academia**
- Study social media manipulation techniques
- Analyze public opinion trends
- Research bot behavior patterns
- Track propaganda techniques

### **Media & Journalism**
- Fact-checking and verification
- Story development and research
- Trend analysis and reporting
- Source verification

## 🔒 Security & Privacy

- **No Personal Data Storage**: Only public posts are collected
- **API Rate Limiting**: Respects platform rate limits
- **Local Database**: All data stored locally in SQLite
- **Configurable Collection**: Users control what data to collect

## 🛠️ Advanced Usage

### **Continuous Data Collection**
```bash
# Run continuous collection (every 5 minutes)
python -c "
import asyncio
from real_data_collector import RealDataCollector
collector = RealDataCollector()
asyncio.run(collector.collect_all_data())
"
```

### **Batch Analysis**
```bash
# Analyze all unanalyzed posts
python -c "
import asyncio
from real_time_analyzer import RealTimeAnalyzer
analyzer = RealTimeAnalyzer()
asyncio.run(analyzer.run_analysis_batch())
"
```

### **Custom Data Export**
```python
from real_data_collector import RealDataCollector

collector = RealDataCollector()
posts = collector.get_posts_from_db(limit=1000, platform='Twitter')

# Export to CSV
import pandas as pd
df = pd.DataFrame(posts)
df.to_csv('dharma_data_export.csv', index=False)
```

## 📋 Management Commands

### **Data Collection**
```bash
python real_data_collector.py          # Collect fresh data
python api_config.py                   # Configure API keys
```

### **Analysis**
```bash
python real_time_analyzer.py           # Run AI analysis
```

### **Dashboard**
```bash
python start_dharma.py                 # Start with launcher
streamlit run enhanced_real_data_dashboard.py  # Direct start
```

### **Database Management**
```bash
# View database contents
sqlite3 dharma_real_data.db "SELECT COUNT(*) FROM posts;"

# Export data
sqlite3 dharma_real_data.db ".mode csv" ".output export.csv" "SELECT * FROM posts;"
```

## 🔍 Troubleshooting

### **Common Issues**

#### **API Rate Limits**
- Twitter: 300 requests per 15 minutes
- YouTube: 10,000 units per day
- Solution: Reduce collection frequency

#### **No Data Collected**
- Check API key configuration
- Verify internet connection
- Check API quotas and limits

#### **Dashboard Not Loading**
- Ensure Streamlit is installed: `pip install streamlit`
- Check port 8501 is available
- Try: `streamlit run enhanced_real_data_dashboard.py --server.port 8502`

#### **Database Errors**
- Delete database file: `rm dharma_real_data.db`
- Reinitialize: `python real_data_collector.py`

### **Performance Optimization**

#### **Large Datasets**
- Limit collection with time ranges
- Use database indexes for faster queries
- Regular database cleanup

#### **Memory Usage**
- Reduce batch sizes in analysis
- Clear old data periodically
- Use streaming for large datasets

## 📞 Support

### **Getting Help**
1. Check this README for common solutions
2. Review error messages in terminal
3. Verify API key configuration
4. Check system requirements

### **System Requirements**
- **Python**: 3.8 or higher
- **Memory**: 2GB RAM minimum
- **Storage**: 1GB for database and dependencies
- **Network**: Internet connection for API access

## 🔮 Future Enhancements

- **Real-time Streaming**: WebSocket-based live updates
- **Advanced ML Models**: Custom trained models for Indian context
- **Multi-language UI**: Dashboard in Hindi and other Indian languages
- **Mobile App**: iOS and Android applications
- **API Integration**: RESTful API for external integrations

---

**Note**: This system is designed for research, security analysis, and legitimate monitoring purposes. Please ensure compliance with platform terms of service and applicable laws when collecting social media data.

## 📄 License

This project is part of the Dharma Platform and is intended for educational, research, and security analysis purposes.