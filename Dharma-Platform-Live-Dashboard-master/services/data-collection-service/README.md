# Data Collection Service

Handles multi-platform data ingestion from Twitter/X, YouTube, TikTok, Telegram, and web sources.

## Features

- Real-time streaming data collection
- Rate limiting and API quota management
- Robust error handling and retry mechanisms
- Data validation and preprocessing

## API Endpoints

- `POST /collect/twitter` - Start Twitter data collection
- `POST /collect/youtube` - Start YouTube data collection
- `POST /collect/web` - Start web scraping
- `GET /status` - Service health check