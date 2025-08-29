"""
API Client for Dashboard Service
Handles communication with backend services
"""

import httpx
import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import streamlit as st

class APIClient:
    """Client for communicating with backend services"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
        self._token = None
    
    def set_token(self, token: str):
        """Set authentication token"""
        self._token = token
        self.client.headers.update({"Authorization": f"Bearer {token}"})
    
    async def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Get key dashboard metrics"""
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/dashboard/metrics")
            if response.status_code == 200:
                return response.json()
            return self._get_mock_metrics()
        except Exception as e:
            st.error(f"Error fetching metrics: {e}")
            return self._get_mock_metrics()
    
    async def get_sentiment_trends(self, days: int = 7) -> Dict[str, Any]:
        """Get sentiment analysis trends"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/analytics/sentiment-trends",
                params={"days": days}
            )
            if response.status_code == 200:
                return response.json()
            return self._get_mock_sentiment_trends(days)
        except Exception:
            return self._get_mock_sentiment_trends(days)
    
    async def get_platform_activity(self, hours: int = 24) -> Dict[str, Any]:
        """Get platform activity data"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/analytics/platform-activity",
                params={"hours": hours}
            )
            if response.status_code == 200:
                return response.json()
            return self._get_mock_platform_activity()
        except Exception:
            return self._get_mock_platform_activity()
    
    async def get_geographic_distribution(self) -> Dict[str, Any]:
        """Get geographic distribution of posts"""
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/analytics/geographic")
            if response.status_code == 200:
                return response.json()
            return self._get_mock_geographic_data()
        except Exception:
            return self._get_mock_geographic_data()
    
    async def get_campaigns(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get list of detected campaigns"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/campaigns",
                params={"limit": limit}
            )
            if response.status_code == 200:
                return response.json()
            return self._get_mock_campaigns()
        except Exception:
            return self._get_mock_campaigns()
    
    async def get_campaign_details(self, campaign_id: str) -> Dict[str, Any]:
        """Get detailed campaign analysis"""
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/campaigns/{campaign_id}")
            if response.status_code == 200:
                return response.json()
            return self._get_mock_campaign_details(campaign_id)
        except Exception:
            return self._get_mock_campaign_details(campaign_id)
    
    async def get_alerts(self, status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get alerts with optional status filter"""
        try:
            params = {"limit": limit}
            if status:
                params["status"] = status
            
            response = await self.client.get(f"{self.base_url}/api/v1/alerts", params=params)
            if response.status_code == 200:
                return response.json()
            return self._get_mock_alerts()
        except Exception:
            return self._get_mock_alerts()
    
    async def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        try:
            response = await self.client.post(f"{self.base_url}/api/v1/alerts/{alert_id}/acknowledge")
            return response.status_code == 200
        except Exception:
            return False
    
    # Mock data methods for development/demo
    def _get_mock_metrics(self) -> Dict[str, Any]:
        """Mock dashboard metrics"""
        return {
            "active_alerts": 23,
            "posts_analyzed_today": 45678,
            "bot_accounts_detected": 1234,
            "active_campaigns": 8,
            "sentiment_distribution": {
                "pro_india": 45.2,
                "neutral": 38.7,
                "anti_india": 16.1
            },
            "platform_breakdown": {
                "twitter": 35.4,
                "youtube": 28.9,
                "telegram": 20.3,
                "web": 15.4
            }
        }
    
    def _get_mock_sentiment_trends(self, days: int) -> Dict[str, Any]:
        """Mock sentiment trends data"""
        import random
        from datetime import datetime, timedelta
        
        dates = []
        pro_india = []
        neutral = []
        anti_india = []
        
        for i in range(days):
            date = datetime.now() - timedelta(days=days-i-1)
            dates.append(date.strftime("%Y-%m-%d"))
            
            # Generate realistic sentiment trends
            pro_india.append(random.uniform(40, 50))
            neutral.append(random.uniform(35, 45))
            anti_india.append(random.uniform(10, 20))
        
        return {
            "dates": dates,
            "pro_india": pro_india,
            "neutral": neutral,
            "anti_india": anti_india
        }
    
    def _get_mock_platform_activity(self) -> Dict[str, Any]:
        """Mock platform activity data"""
        import random
        
        platforms = ["Twitter", "YouTube", "Telegram", "Web"]
        hours = list(range(24))
        
        data = {}
        for platform in platforms:
            data[platform] = [random.randint(100, 1000) for _ in hours]
        
        return {
            "hours": hours,
            "platforms": data
        }
    
    def _get_mock_geographic_data(self) -> Dict[str, Any]:
        """Mock geographic distribution data"""
        return {
            "countries": [
                {"country": "India", "posts": 25000, "lat": 20.5937, "lon": 78.9629},
                {"country": "Pakistan", "posts": 5000, "lat": 30.3753, "lon": 69.3451},
                {"country": "Bangladesh", "posts": 3000, "lat": 23.6850, "lon": 90.3563},
                {"country": "USA", "posts": 2000, "lat": 37.0902, "lon": -95.7129},
                {"country": "UK", "posts": 1500, "lat": 55.3781, "lon": -3.4360}
            ]
        }
    
    def _get_mock_campaigns(self) -> List[Dict[str, Any]]:
        """Mock campaigns data"""
        return [
            {
                "id": "camp_001",
                "name": "Anti-Government Narrative",
                "status": "active",
                "coordination_score": 0.85,
                "participants": 45,
                "detection_date": "2024-01-15T10:30:00Z",
                "impact_score": 0.72
            },
            {
                "id": "camp_002", 
                "name": "Economic Policy Criticism",
                "status": "monitoring",
                "coordination_score": 0.67,
                "participants": 23,
                "detection_date": "2024-01-14T15:45:00Z",
                "impact_score": 0.58
            }
        ]
    
    def _get_mock_campaign_details(self, campaign_id: str) -> Dict[str, Any]:
        """Mock campaign details"""
        return {
            "id": campaign_id,
            "name": "Anti-Government Narrative",
            "description": "Coordinated campaign spreading negative sentiment about government policies",
            "status": "active",
            "coordination_score": 0.85,
            "participants": 45,
            "detection_date": "2024-01-15T10:30:00Z",
            "network_graph": {
                "nodes": [
                    {"id": "user1", "type": "bot", "influence": 0.8},
                    {"id": "user2", "type": "human", "influence": 0.6},
                    {"id": "user3", "type": "bot", "influence": 0.9}
                ],
                "edges": [
                    {"source": "user1", "target": "user2", "weight": 0.7},
                    {"source": "user1", "target": "user3", "weight": 0.8}
                ]
            }
        }
    
    def _get_mock_alerts(self) -> List[Dict[str, Any]]:
        """Mock alerts data"""
        return [
            {
                "id": "alert_001",
                "type": "high_coordination",
                "severity": "high",
                "title": "High Coordination Detected",
                "description": "Unusual coordination pattern detected in anti-government posts",
                "status": "new",
                "created_at": "2024-01-15T14:30:00Z"
            },
            {
                "id": "alert_002",
                "type": "bot_network",
                "severity": "medium", 
                "title": "Bot Network Activity",
                "description": "Increased activity from suspected bot network",
                "status": "acknowledged",
                "created_at": "2024-01-15T12:15:00Z"
            }
        ]