"""Webhook notification provider for external system integration."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import aiohttp
from urllib.parse import urlparse

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../'))

from shared.models.alert import Alert, NotificationChannel
from ..core.config import config
from .notification_service import NotificationProvider, NotificationRecord, NotificationStatus

logger = logging.getLogger(__name__)


class WebhookProvider(NotificationProvider):
    """Webhook notification provider for external systems."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.timeout = aiohttp.ClientTimeout(total=30)
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        
        # Initialize session
        asyncio.create_task(self._initialize_session())
    
    async def _initialize_session(self):
        """Initialize aiohttp session."""
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=10,
            ttl_dns_cache=300,
            use_dns_cache=True
        )
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=self.timeout,
            headers={
                "User-Agent": "Project-Dharma-Alert-System/1.0",
                "Content-Type": "application/json"
            }
        )
    
    def get_channel(self) -> NotificationChannel:
        """Get the notification channel this provider handles."""
        return NotificationChannel.WEBHOOK
    
    async def validate_recipient(self, recipient: str) -> bool:
        """Validate webhook URL format."""
        try:
            parsed = urlparse(recipient)
            return parsed.scheme in ['http', 'https'] and bool(parsed.netloc)
        except Exception:
            return False
    
    async def send_notification(
        self,
        alert: Alert,
        recipient: str,
        template_data: Dict[str, Any]
    ) -> NotificationRecord:
        """Send webhook notification."""
        notification_id = f"webhook_{alert.alert_id}_{hash(recipient) % 10000}"
        record = NotificationRecord(
            notification_id=notification_id,
            alert_id=alert.alert_id,
            channel=NotificationChannel.WEBHOOK,
            recipient=recipient
        )
        
        try:
            if not self.session:
                await self._initialize_session()
            
            # Prepare webhook payload
            payload = self._prepare_webhook_payload(alert, template_data)
            
            # Send webhook with retries
            success = await self._send_webhook_with_retries(recipient, payload, record)
            
            if success:
                record.mark_sent()
                logger.info(f"Webhook sent successfully to {recipient}")
            else:
                record.mark_failed("Failed after all retry attempts")
                
        except Exception as e:
            error_msg = f"Webhook error: {str(e)}"
            record.mark_failed(error_msg)
            logger.error(f"Failed to send webhook to {recipient}: {error_msg}")
        
        return record
    
    def _prepare_webhook_payload(self, alert: Alert, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare webhook payload."""
        payload = {
            "event": "alert.created",
            "timestamp": datetime.utcnow().isoformat(),
            "source": "project-dharma",
            "version": "1.0",
            "alert": {
                "id": alert.alert_id,
                "title": alert.title,
                "description": alert.description,
                "type": alert.alert_type,
                "severity": alert.severity,
                "status": alert.status,
                "created_at": alert.created_at.isoformat() if alert.created_at else None,
                "context": {
                    "platform": alert.context.source_platform,
                    "detection_method": alert.context.detection_method,
                    "confidence_score": alert.context.confidence_score,
                    "risk_score": alert.context.risk_score,
                    "affected_regions": alert.context.affected_regions,
                    "keywords": alert.context.keywords_matched,
                    "hashtags": alert.context.hashtags_involved,
                    "content_samples": alert.context.content_samples[:3],  # Limit samples
                    "detection_window": {
                        "start": alert.context.detection_window_start.isoformat(),
                        "end": alert.context.detection_window_end.isoformat()
                    }
                },
                "metrics": {
                    "volume": alert.context.volume_metrics,
                    "engagement": alert.context.engagement_metrics
                },
                "tags": alert.tags,
                "dashboard_url": template_data.get("dashboard_url")
            }
        }
        
        # Add assignment information if available
        if alert.assigned_to:
            payload["alert"]["assigned_to"] = alert.assigned_to
            payload["alert"]["assigned_at"] = alert.assigned_at.isoformat() if alert.assigned_at else None
        
        return payload
    
    async def _send_webhook_with_retries(
        self,
        url: str,
        payload: Dict[str, Any],
        record: NotificationRecord
    ) -> bool:
        """Send webhook with retry logic."""
        for attempt in range(self.max_retries):
            try:
                async with self.session.post(url, json=payload) as response:
                    # Record response details
                    record.metadata.update({
                        "attempt": attempt + 1,
                        "status_code": response.status,
                        "response_headers": dict(response.headers),
                        "url": url
                    })
                    
                    if response.status < 400:
                        # Success
                        response_text = await response.text()
                        record.metadata["response_body"] = response_text[:500]  # Limit size
                        return True
                    else:
                        # HTTP error
                        error_text = await response.text()
                        record.metadata["error_response"] = error_text[:500]
                        logger.warning(
                            f"Webhook attempt {attempt + 1} failed with status {response.status}: {error_text[:100]}"
                        )
                        
            except asyncio.TimeoutError:
                logger.warning(f"Webhook attempt {attempt + 1} timed out for {url}")
                record.metadata[f"attempt_{attempt + 1}_error"] = "timeout"
                
            except aiohttp.ClientError as e:
                logger.warning(f"Webhook attempt {attempt + 1} client error: {e}")
                record.metadata[f"attempt_{attempt + 1}_error"] = str(e)
                
            except Exception as e:
                logger.error(f"Webhook attempt {attempt + 1} unexpected error: {e}")
                record.metadata[f"attempt_{attempt + 1}_error"] = str(e)
            
            # Wait before retry (except on last attempt)
            if attempt < self.max_retries - 1:
                await asyncio.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
        
        return False
    
    async def send_test_webhook(self, url: str) -> Dict[str, Any]:
        """Send test webhook to validate endpoint."""
        test_payload = {
            "event": "test",
            "timestamp": datetime.utcnow().isoformat(),
            "source": "project-dharma",
            "message": "This is a test webhook from Project Dharma"
        }
        
        try:
            if not self.session:
                await self._initialize_session()
            
            async with self.session.post(url, json=test_payload) as response:
                return {
                    "success": response.status < 400,
                    "status_code": response.status,
                    "response_text": await response.text(),
                    "headers": dict(response.headers)
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_provider_stats(self) -> Dict[str, Any]:
        """Get webhook provider statistics."""
        return {
            "provider": "webhook",
            "session_active": self.session is not None,
            "timeout_seconds": self.timeout.total,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay
        }
    
    async def close(self):
        """Close the aiohttp session."""
        if self.session:
            await self.session.close()


class WebhookSecurityManager:
    """Manages webhook security features."""
    
    def __init__(self):
        self.signing_secret = config.webhook_signing_secret if hasattr(config, 'webhook_signing_secret') else None
        self.allowed_domains = getattr(config, 'webhook_allowed_domains', [])
    
    def generate_signature(self, payload: str, secret: str) -> str:
        """Generate HMAC signature for webhook payload."""
        import hmac
        import hashlib
        
        signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return f"sha256={signature}"
    
    def is_domain_allowed(self, url: str) -> bool:
        """Check if webhook domain is allowed."""
        if not self.allowed_domains:
            return True  # No restrictions
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            for allowed in self.allowed_domains:
                if domain == allowed.lower() or domain.endswith(f".{allowed.lower()}"):
                    return True
            
            return False
            
        except Exception:
            return False
    
    def add_security_headers(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Add security headers for webhook request."""
        headers = {}
        
        if self.signing_secret:
            payload_str = json.dumps(payload, separators=(',', ':'))
            signature = self.generate_signature(payload_str, self.signing_secret)
            headers["X-Dharma-Signature"] = signature
        
        headers["X-Dharma-Timestamp"] = str(int(datetime.utcnow().timestamp()))
        headers["X-Dharma-Event"] = payload.get("event", "unknown")
        
        return headers


class WebhookRetryManager:
    """Manages webhook retry logic and dead letter queue."""
    
    def __init__(self):
        self.retry_queue = asyncio.Queue()
        self.dead_letter_queue = []
        self.max_dead_letter_size = 1000
        
        # Start retry worker
        asyncio.create_task(self._retry_worker())
    
    async def add_to_retry_queue(self, webhook_data: Dict[str, Any]):
        """Add failed webhook to retry queue."""
        await self.retry_queue.put(webhook_data)
    
    async def _retry_worker(self):
        """Background worker for processing webhook retries."""
        while True:
            try:
                webhook_data = await self.retry_queue.get()
                
                # Implement exponential backoff
                retry_count = webhook_data.get("retry_count", 0)
                if retry_count < 5:  # Max 5 retries
                    delay = 2 ** retry_count  # Exponential backoff
                    await asyncio.sleep(delay)
                    
                    # Attempt retry (implementation would call webhook provider)
                    webhook_data["retry_count"] = retry_count + 1
                    # ... retry logic ...
                    
                else:
                    # Move to dead letter queue
                    await self._add_to_dead_letter_queue(webhook_data)
                
                self.retry_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in webhook retry worker: {e}")
                await asyncio.sleep(1)
    
    async def _add_to_dead_letter_queue(self, webhook_data: Dict[str, Any]):
        """Add webhook to dead letter queue."""
        webhook_data["failed_at"] = datetime.utcnow().isoformat()
        self.dead_letter_queue.append(webhook_data)
        
        # Limit dead letter queue size
        if len(self.dead_letter_queue) > self.max_dead_letter_size:
            self.dead_letter_queue.pop(0)  # Remove oldest
        
        logger.warning(f"Webhook moved to dead letter queue: {webhook_data.get('url', 'unknown')}")
    
    async def get_dead_letter_stats(self) -> Dict[str, Any]:
        """Get dead letter queue statistics."""
        return {
            "dead_letter_count": len(self.dead_letter_queue),
            "retry_queue_size": self.retry_queue.qsize(),
            "max_dead_letter_size": self.max_dead_letter_size
        }