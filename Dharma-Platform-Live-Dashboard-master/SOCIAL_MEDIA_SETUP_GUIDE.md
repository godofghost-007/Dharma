# Social Media Setup Guide

## Table of Contents

1. [Introduction & Prerequisites](#introduction--prerequisites)
2. [Platform-Specific Setup](#platform-specific-setup)
   - [Twitter/X Configuration](#twitterx-configuration)
   - [YouTube Configuration](#youtube-configuration)
   - [Telegram Configuration](#telegram-configuration)
   - [Web Scraping Configuration](#web-scraping-configuration)
3. [Configuration Examples](#configuration-examples)
4. [Troubleshooting](#troubleshooting)
5. [Security & Compliance](#security--compliance)
6. [Quick Reference](#quick-reference)

## Introduction & Prerequisites

This guide provides comprehensive instructions for configuring social media monitoring and data collection across all supported platforms in the Dharma system. The system supports monitoring of:

- **Twitter/X** - User timelines, hashtags, search terms
- **YouTube** - Channels, videos, playlists, search results
- **Telegram** - Public channels and groups
- **Web Scraping** - News sites, forums, and other web content

### Prerequisites

- Docker and Docker Compose installed
- API credentials for each platform you want to monitor
- Basic understanding of YAML configuration files
- Network access to target platforms

### Supported Data Collection

- Real-time posts and messages
- User profiles and metadata
- Engagement metrics (likes, shares, comments)
- Media content (images, videos, links)
- Temporal data for trend analysis

## Platform-Specific Setup

### Twitter/X Configuration

#### API Credentials Setup

1. **Create Twitter Developer Account**

   - Visit [developer.twitter.com](https://developer.twitter.com)
   - Apply for developer access
   - Create a new app in the developer portal

2. **Obtain API Credentials**
   ```bash
   # Required credentials
   TWITTER_API_KEY=1MTs9hyoDlo99vAIRM5wnrcb1
   TWITTER_API_SECRET=f12uEdLI13ubrnfNLyuVtFXtXYuTUU5I74CSdPElvyIR8MSODk
   TWITTER_BEARER_TOKEN=AAAAAAAAAAAAAAAAAAAAAGtA3wEAAAAAaDjLZI1JoAKZ4facy5p3R6on7aw%3DKu1b10pw9S4Is6fG7rVIB1rsOv5r4UnM5pXbG7LWwpo7MBhiq2
   TWITTER_ACCESS_TOKEN=1562070818066116609-2koONcWseaIntbNg1JsYvgV6pac0K6
   TWITTER_ACCESS_TOKEN_SECRET=pEBknFp3XGXQ6vANsHdDFtKfqCUaN0WjwahjFMYejoJ9F
   ```

#### Monitoring Configuration Examples

**User Monitoring**

```yaml
twitter:
  users:
    - "@BBCBreaking" # BBC Breaking News
    - "@CNN" # CNN Official
    - "@Reuters" # Reuters News
    - "@AP" # Associated Press
    - "@nytimes" # New York Times
```

**Hashtag Monitoring**

```yaml
twitter:
  hashtags:
    - "#BreakingNews" # General breaking news
    - "#Politics" # Political discussions
    - "#Technology" # Tech news and trends
    - "#ClimateChange" # Environmental topics
    - "#Election2024" # Election coverage
```

**Search Terms and Keywords**

```yaml
twitter:
  keywords:
    - "data breach" # Security incidents
    - "market crash" # Financial events
    - "natural disaster" # Emergency situations
    - "policy change" # Government updates
    - "product launch" # Business announcements
```

#### Rate Limiting

- Standard API: 300 requests per 15-minute window
- Premium API: Higher limits available
- Recommended collection frequency: Every 5-10 minutes

### YouTube Configuration

#### API Credentials Setup

1. **Google Cloud Console Setup**

   - Visit [console.cloud.google.com](https://console.cloud.google.com)
   - Create new project or select existing one
   - Enable YouTube Data API v3
   - Create API key credentials

2. **API Key Configuration**
   ```bash
   YOUTUBE_API_KEY=AIzaSyDwwgdEraFpnybyWGcpQ5nELoLTqpr6Q9c
   ```

#### Monitoring Configuration Examples

**Channel Monitoring**

```yaml
youtube:
  channels:
    - "@BBC" # BBC Official Channel
    - "@CNNInternational" # CNN International
    - "UC_x5XG1OV2P6uZZ5FSM9Ttw" # Google News (Channel ID)
    - "@TEDTalks" # TED Talks
    - "@NatGeo" # National Geographic
```

**Video Search Criteria**

```yaml
youtube:
  search_terms:
    - "breaking news today"
    - "technology trends 2024"
    - "climate change report"
    - "economic analysis"
    - "scientific breakthrough"
  categories:
    - "News & Politics" # Category ID: 25
    - "Science & Technology" # Category ID: 28
    - "Education" # Category ID: 27
```

**Playlist Monitoring**

```yaml
youtube:
  playlists:
    - "PLrAXtmRdnEQy8Q9nQQW6bJ8Q7K5Z1X2Y3" # News Playlist
    - "PLbpi6ZahtOH4YQW6bJ8Q7K5Z1X2Y3ABC" # Tech Updates
```

#### Quota Management

- Daily quota: 10,000 units (default)
- Search operation: ~100 units
- Channel details: ~1 unit
- Recommended: Monitor 50-100 channels maximum

### Telegram Configuration

#### Bot Setup and Permissions

1. **Create Telegram Bot**

   - Message @BotFather on Telegram
   - Use `/newbot` command
   - Follow setup instructions
   - Save the bot token

2. **Bot Token Configuration**
   ```bash
   TELEGRAM_BOT_TOKEN=8021290510:AAHd83QoNHhOOuyANuPxdQo-Ya5O4C6Mrqw
   ```

#### Monitoring Configuration Examples

**Public Channel Monitoring**

```yaml
telegram:
  channels:
    - "@BBCBreaking" # BBC Breaking News
    - "@CNNBrk" # CNN Breaking News
    - "@reutersagency" # Reuters News Agency
    - "@AP" # Associated Press
    - "@nytimes" # New York Times
```

**Chat ID Examples**

```yaml
telegram:
  chat_ids:
    - "-1001234567890" # Public channel (negative ID)
    - "-1009876543210" # Public group (negative ID)
    - "1234567890" # Private chat (positive ID)
```

#### Access Considerations

- **Public Channels**: Bot can read without being added
- **Private Channels**: Bot must be added as admin
- **Groups**: Bot must be added as member
- **Rate Limiting**: 30 messages per second maximum

### Web Scraping Configuration

#### Target Website Examples

```yaml
web_scraping:
  sites:
    - name: "Reddit News"
      url: "https://reddit.com/r/news"
      selectors:
        title: "h3[data-testid='post-content-title']"
        content: "div[data-testid='post-content-text']"
        author: "a[data-testid='post-content-author']"
        timestamp: "time"

    - name: "Hacker News"
      url: "https://news.ycombinator.com"
      selectors:
        title: "a.storylink"
        score: "span.score"
        comments: "a[href*='item?id=']"

    - name: "BBC News"
      url: "https://www.bbc.com/news"
      selectors:
        title: "h3.gs-c-promo-heading__title"
        summary: "p.gs-c-promo-summary"
        link: "a.gs-c-promo-heading"
```

#### Request Configuration

```yaml
web_scraping:
  settings:
    user_agent: "Mozilla/5.0 (compatible; DharmaBot/1.0)"
    request_delay: 2 # seconds between requests
    timeout: 30 # request timeout in seconds
    respect_robots_txt: true
    max_retries: 3
```

#### Dynamic Content Handling

For JavaScript-heavy sites, enable browser automation:

```yaml
web_scraping:
  browser_automation:
    enabled: true
    headless: true
    wait_for_element: "div.content-loaded"
    screenshot: false
```

## Configuration Examples

### Complete Environment Variables

```bash
# Twitter/X Configuration
TWITTER_API_KEY=1MTs9hyoDlo99vAIRM5wnrcb1
TWITTER_API_SECRET=f12uEdLI13ubrnfNLyuVtFXtXYuTUU5I74CSdPElvyIR8MSODk
TWITTER_BEARER_TOKEN=AAAAAAAAAAAAAAAAAAAAAGtA3wEAAAAAaDjLZI1JoAKZ4facy5p3R6on7aw%3DKu1b10pw9S4Is6fG7rVIB1rsOv5r4UnM5pXbG7LWwpo7MBhiq2
TWITTER_ACCESS_TOKEN=1562070818066116609-2koONcWseaIntbNg1JsYvgV6pac0K6
TWITTER_ACCESS_TOKEN_SECRET=pEBknFp3XGXQ6vANsHdDFtKfqCUaN0WjwahjFMYejoJ9F

# YouTube Configuration
YOUTUBE_API_KEY=AIzaSyDwwgdEraFpnybyWGcpQ5nELoLTqpr6Q9c

# Telegram Configuration
TELEGRAM_BOT_TOKEN=8021290510:AAHd83QoNHhOOuyANuPxdQo-Ya5O4C6Mrqw

# Database Configuration
MONGODB_URI=mongodb://localhost:27017/dharma
REDIS_URL=redis://localhost:6379
ELASTICSEARCH_URL=http://localhost:9200
```

### Master Configuration File

```yaml
# config/data_collection.yml
platforms:
  twitter:
    enabled: true
    users: ["@BBCBreaking", "@CNN", "@Reuters"]
    hashtags: ["#BreakingNews", "#Politics", "#Technology"]
    keywords: ["data breach", "market crash", "policy change"]
    settings:
      collection_frequency: 300 # 5 minutes
      max_results_per_request: 100

  youtube:
    enabled: true
    channels: ["@BBC", "@CNNInternational", "UC_x5XG1OV2P6uZZ5FSM9Ttw"]
    search_terms: ["breaking news", "technology trends"]
    settings:
      collection_frequency: 600 # 10 minutes
      max_results_per_request: 50

  telegram:
    enabled: true
    channels: ["@BBCBreaking", "@CNNBrk", "@reutersagency"]
    settings:
      collection_frequency: 60 # 1 minute
      max_messages_per_request: 100

  web_scraping:
    enabled: true
    sites:
      - name: "Reddit News"
        url: "https://reddit.com/r/news"
        frequency: 1800 # 30 minutes
      - name: "Hacker News"
        url: "https://news.ycombinator.com"
        frequency: 3600 # 1 hour
```

## Troubleshooting

### API Authentication Issues

#### Twitter/X Authentication Errors

**Error**: `401 Unauthorized`

```bash
# Verify credentials
curl -H "Authorization: Bearer AAAAAAAAAAAAAAAAAAAAAGtA3wEAAAAAaDjLZI1JoAKZ4facy5p3R6on7aw%3DKu1b10pw9S4Is6fG7rVIB1rsOv5r4UnM5pXbG7LWwpo7MBhiq2" \
     "https://api.twitter.com/2/users/me"
```

**Solutions**:

1. Check API key and secret are correct
2. Verify bearer token is properly generated
3. Ensure app has required permissions
4. Check if API access level is sufficient

#### YouTube API Errors

**Error**: `403 Forbidden - Daily Limit Exceeded`

```bash
# Check quota usage
curl "https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true&key=AIzaSyDwwgdEraFpnybyWGcpQ5nELoLTqpr6Q9c"
```

**Solutions**:

1. Reduce collection frequency
2. Optimize API calls (batch requests)
3. Request quota increase from Google
4. Implement intelligent caching

#### Telegram Bot Issues

**Error**: `400 Bad Request - Bot was blocked by user`

```bash
# Test bot connectivity
curl "https://api.telegram.org/bot8021290510:AAHd83QoNHhOOuyANuPxdQo-Ya5O4C6Mrqw/getMe"
```

**Solutions**:

1. Verify bot token is correct
2. Check bot permissions in target channels
3. Ensure bot is added to private channels
4. Verify chat IDs are correct format

### Data Collection Failures

#### Network Connectivity Issues

```bash
# Test platform connectivity
ping api.twitter.com
ping www.googleapis.com
ping api.telegram.org

# Test with curl
curl -I https://api.twitter.com/2/tweets/search/recent
```

#### Rate Limiting Solutions

1. **Implement exponential backoff**

   ```python
   import time
   import random

   def retry_with_backoff(func, max_retries=3):
       for attempt in range(max_retries):
           try:
               return func()
           except RateLimitError:
               wait_time = (2 ** attempt) + random.uniform(0, 1)
               time.sleep(wait_time)
   ```

2. **Adjust collection frequencies**
   - Twitter: Increase from 5 to 10+ minutes
   - YouTube: Increase from 10 to 30+ minutes
   - Telegram: Increase from 1 to 5+ minutes

#### Configuration Validation

```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('config/data_collection.yml'))"

# Test database connections
python -c "
import pymongo
import redis
from elasticsearch import Elasticsearch

# Test MongoDB
mongo = pymongo.MongoClient('mongodb://localhost:27017/')
print('MongoDB:', mongo.admin.command('ping'))

# Test Redis
r = redis.Redis(host='localhost', port=6379)
print('Redis:', r.ping())

# Test Elasticsearch
es = Elasticsearch(['http://localhost:9200'])
print('Elasticsearch:', es.ping())
"
```

### Common Error Messages

| Error                      | Platform     | Solution                                |
| -------------------------- | ------------ | --------------------------------------- |
| `Invalid or expired token` | Twitter      | Regenerate bearer token                 |
| `Quota exceeded`           | YouTube      | Reduce API calls or request increase    |
| `Chat not found`           | Telegram     | Verify chat ID format and permissions   |
| `403 Forbidden`            | Web Scraping | Check robots.txt and user agent         |
| `Connection timeout`       | All          | Check network connectivity and firewall |

## Security & Compliance

### Credential Security

#### Secure Storage

```bash
# Use environment files (never commit to git)
echo "TWITTER_API_KEY=1MTs9hyoDlo99vAIRM5wnrcb1" >> .env
echo ".env" >> .gitignore

# Use Docker secrets in production
docker secret create twitter_api_key twitter_key.txt
```

#### Credential Rotation

```bash
# Automated credential rotation script
#!/bin/bash
# rotate_credentials.sh

# Backup current credentials
cp .env .env.backup.$(date +%Y%m%d)

# Update with new credentials
echo "TWITTER_API_KEY=1MTs9hyoDlo99vAIRM5wnrcb1" > .env.new
echo "YOUTUBE_API_KEY=$NEW_YOUTUBE_KEY" >> .env.new

# Test new credentials before applying
if test_credentials.py --config .env.new; then
    mv .env.new .env
    echo "Credentials rotated successfully"
else
    echo "Credential validation failed"
    exit 1
fi
```

### Privacy Compliance

#### Data Collection Guidelines

1. **Public Content Only**: Only collect publicly available content
2. **User Consent**: Respect user privacy settings and opt-outs
3. **Data Minimization**: Collect only necessary data fields
4. **Retention Limits**: Implement automatic data expiration

#### GDPR Compliance

```yaml
privacy_settings:
  data_retention_days: 90
  anonymize_personal_data: true
  respect_user_deletions: true
  provide_data_export: true

excluded_data_types:
  - private_messages
  - personal_identifiers
  - location_data
  - contact_information
```

#### Content Filtering

```python
# Example content filter
def filter_sensitive_content(post):
    sensitive_patterns = [
        r'\b\d{3}-\d{2}-\d{4}\b',      # SSN
        r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',  # Credit card
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'  # Email
    ]

    for pattern in sensitive_patterns:
        if re.search(pattern, post.content):
            post.content = re.sub(pattern, '[REDACTED]', post.content)

    return post
```

### Data Retention Management

#### Automated Cleanup

```python
# cleanup_old_data.py
from datetime import datetime, timedelta
import pymongo

def cleanup_old_posts(retention_days=90):
    client = pymongo.MongoClient()
    db = client.dharma

    cutoff_date = datetime.now() - timedelta(days=retention_days)

    # Remove old posts
    result = db.posts.delete_many({
        'created_at': {'$lt': cutoff_date}
    })

    print(f"Deleted {result.deleted_count} old posts")

# Run daily via cron
# 0 2 * * * /usr/bin/python /path/to/cleanup_old_data.py
```

## Quick Reference

### Platform Limits Summary

| Platform     | Rate Limit     | Quota         | Best Frequency |
| ------------ | -------------- | ------------- | -------------- |
| Twitter      | 300 req/15min  | N/A           | 5-10 minutes   |
| YouTube      | N/A            | 10K units/day | 10-30 minutes  |
| Telegram     | 30 msg/sec     | N/A           | 1-5 minutes    |
| Web Scraping | Site-dependent | N/A           | 30+ minutes    |

### Required Credentials Checklist

- [ ] **Twitter/X**

  - [ ] API Key
  - [ ] API Secret
  - [ ] Bearer Token
  - [ ] Access Token
  - [ ] Access Token Secret

- [ ] **YouTube**

  - [ ] API Key
  - [ ] Project enabled for YouTube Data API v3

- [ ] **Telegram**

  - [ ] Bot Token
  - [ ] Bot added to target channels (if private)

- [ ] **Infrastructure**
  - [ ] MongoDB connection
  - [ ] Redis connection
  - [ ] Elasticsearch connection
  - [ ] Kafka connection (if using event streaming)

### Configuration Validation Commands

```bash
# Test all platform connections
python scripts/test_connections.py

# Validate configuration syntax
python scripts/validate_config.py config/data_collection.yml

# Check API quotas and limits
python scripts/check_quotas.py

# Test data collection pipeline
python scripts/test_collection.py --platform twitter --duration 60
```

### Emergency Procedures

#### Stop All Collection

```bash
# Stop all data collection services
docker-compose stop data-collection-service

# Disable in configuration
sed -i 's/enabled: true/enabled: false/g' config/data_collection.yml
```

#### Rate Limit Recovery

```bash
# Increase collection intervals by 2x
python scripts/adjust_frequencies.py --multiply 2

# Restart with new settings
docker-compose restart data-collection-service
```

### Support Resources

- **Twitter API Documentation**: [developer.twitter.com/en/docs](https://developer.twitter.com/en/docs)
- **YouTube API Documentation**: [developers.google.com/youtube/v3](https://developers.google.com/youtube/v3)
- **Telegram Bot API**: [core.telegram.org/bots/api](https://core.telegram.org/bots/api)
- **Project Issues**: [github.com/your-org/dharma/issues](https://github.com/your-org/dharma/issues)

---

**Last Updated**: December 2024  
**Version**: 2.0  
**Maintainer**: Dharma Development Team
