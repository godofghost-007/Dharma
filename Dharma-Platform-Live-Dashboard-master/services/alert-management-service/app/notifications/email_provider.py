"""Email notification provider with HTML templates."""

import asyncio
import logging
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, Any, Optional
import re

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../'))

from shared.models.alert import Alert, NotificationChannel, SeverityLevel
from ..core.config import config
from .notification_service import NotificationProvider, NotificationRecord, NotificationStatus

logger = logging.getLogger(__name__)


class EmailProvider(NotificationProvider):
    """Email notification provider with HTML templates."""
    
    def __init__(self):
        self.smtp_server = config.smtp_server
        self.smtp_port = config.smtp_port
        self.smtp_username = config.smtp_username
        self.smtp_password = config.smtp_password
        self.from_email = config.smtp_from_email
        self.template_manager = EmailTemplateManager()
    
    def get_channel(self) -> NotificationChannel:
        """Get the notification channel this provider handles."""
        return NotificationChannel.EMAIL
    
    async def validate_recipient(self, recipient: str) -> bool:
        """Validate email address format."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, recipient))
    
    async def send_notification(
        self,
        alert: Alert,
        recipient: str,
        template_data: Dict[str, Any]
    ) -> NotificationRecord:
        """Send email notification."""
        notification_id = f"email_{alert.alert_id}_{recipient.replace('@', '_at_')}"
        record = NotificationRecord(
            notification_id=notification_id,
            alert_id=alert.alert_id,
            channel=NotificationChannel.EMAIL,
            recipient=recipient
        )
        
        try:
            # Generate email content
            subject = template_data.get("subject", f"Project Dharma Alert: {alert.title}")
            html_content = await self.template_manager.generate_html_content(alert, template_data)
            text_content = await self.template_manager.generate_text_content(alert, template_data)
            
            # Create email message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.from_email
            message["To"] = recipient
            message["Date"] = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")
            
            # Add message ID for tracking
            message["Message-ID"] = f"<{notification_id}@dharma.gov>"
            
            # Add priority header for high severity alerts
            if alert.severity in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]:
                message["X-Priority"] = "1"
                message["Importance"] = "high"
            
            # Attach text and HTML parts
            text_part = MIMEText(text_content, "plain", "utf-8")
            html_part = MIMEText(html_content, "html", "utf-8")
            
            message.attach(text_part)
            message.attach(html_part)
            
            # Send email
            await self._send_email(message, recipient)
            
            record.metadata["subject"] = subject
            record.metadata["message_id"] = notification_id
            record.mark_sent()
            
            logger.info(f"Email sent successfully to {recipient}")
            
        except Exception as e:
            error_msg = f"Failed to send email: {str(e)}"
            record.mark_failed(error_msg)
            logger.error(f"Failed to send email to {recipient}: {error_msg}")
        
        return record
    
    async def _send_email(self, message: MIMEMultipart, recipient: str):
        """Send email using SMTP."""
        try:
            # Use asyncio to run SMTP in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._send_smtp_email, message, recipient)
            
        except Exception as e:
            logger.error(f"SMTP error sending to {recipient}: {e}")
            raise
    
    def _send_smtp_email(self, message: MIMEMultipart, recipient: str):
        """Send email via SMTP (synchronous)."""
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.smtp_username and self.smtp_password:
                    server.starttls()
                    server.login(self.smtp_username, self.smtp_password)
                
                server.send_message(message, to_addrs=[recipient])
                
        except smtplib.SMTPException as e:
            logger.error(f"SMTP exception: {e}")
            raise
        except Exception as e:
            logger.error(f"Email sending error: {e}")
            raise
    
    async def get_provider_stats(self) -> Dict[str, Any]:
        """Get email provider statistics."""
        return {
            "provider": "smtp",
            "smtp_server": self.smtp_server,
            "smtp_port": self.smtp_port,
            "from_email": self.from_email,
            "configured": bool(self.smtp_server and self.from_email)
        }


class EmailTemplateManager:
    """Manages email templates and content generation."""
    
    def __init__(self):
        self.severity_colors = {
            SeverityLevel.CRITICAL: "#dc3545",  # Red
            SeverityLevel.HIGH: "#fd7e14",      # Orange
            SeverityLevel.MEDIUM: "#ffc107",    # Yellow
            SeverityLevel.LOW: "#28a745"        # Green
        }
        
        self.severity_icons = {
            SeverityLevel.CRITICAL: "🚨",
            SeverityLevel.HIGH: "⚠️",
            SeverityLevel.MEDIUM: "📢",
            SeverityLevel.LOW: "ℹ️"
        }
    
    async def generate_html_content(self, alert: Alert, template_data: Dict[str, Any]) -> str:
        """Generate HTML email content."""
        severity_color = self.severity_colors.get(alert.severity, "#6c757d")
        severity_icon = self.severity_icons.get(alert.severity, "📢")
        
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Project Dharma Alert</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: {severity_color};
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 8px 8px 0 0;
                }}
                .content {{
                    background-color: #f8f9fa;
                    padding: 20px;
                    border: 1px solid #dee2e6;
                }}
                .footer {{
                    background-color: #e9ecef;
                    padding: 15px;
                    text-align: center;
                    border-radius: 0 0 8px 8px;
                    font-size: 12px;
                    color: #6c757d;
                }}
                .alert-details {{
                    background-color: white;
                    padding: 15px;
                    margin: 15px 0;
                    border-radius: 4px;
                    border-left: 4px solid {severity_color};
                }}
                .metric {{
                    display: inline-block;
                    margin: 5px 10px;
                    padding: 5px 10px;
                    background-color: #e9ecef;
                    border-radius: 4px;
                    font-size: 12px;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 24px;
                    background-color: {severity_color};
                    color: white;
                    text-decoration: none;
                    border-radius: 4px;
                    margin: 10px 0;
                }}
                .content-sample {{
                    background-color: #f1f3f4;
                    padding: 10px;
                    margin: 10px 0;
                    border-radius: 4px;
                    font-style: italic;
                    border-left: 3px solid #6c757d;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{severity_icon} Project Dharma Alert</h1>
                <h2>{alert.title}</h2>
                <p><strong>{alert.severity.upper()}</strong> | {alert.alert_type.replace('_', ' ').title()}</p>
            </div>
            
            <div class="content">
                <div class="alert-details">
                    <h3>Alert Details</h3>
                    <p><strong>Description:</strong> {alert.description}</p>
                    <p><strong>Platform:</strong> {alert.context.source_platform or 'Unknown'}</p>
                    <p><strong>Detection Time:</strong> {alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if alert.created_at else 'Unknown'}</p>
                    
                    <div style="margin: 15px 0;">
                        <span class="metric">Confidence: {alert.context.confidence_score:.0%}</span>
                        <span class="metric">Risk Score: {alert.context.risk_score:.0%}</span>
                        {f'<span class="metric">Regions: {", ".join(alert.context.affected_regions[:3])}</span>' if alert.context.affected_regions else ''}
                    </div>
                </div>
                
                {self._generate_content_samples_html(alert)}
                {self._generate_keywords_html(alert)}
                {self._generate_metrics_html(alert)}
                
                <div style="text-align: center; margin: 20px 0;">
                    <a href="{template_data.get('dashboard_url', '#')}" class="button">
                        View in Dashboard
                    </a>
                </div>
            </div>
            
            <div class="footer">
                <p>This is an automated alert from Project Dharma Social Media Intelligence Platform</p>
                <p>Generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            </div>
        </body>
        </html>
        """
        
        return html_template
    
    def _generate_content_samples_html(self, alert: Alert) -> str:
        """Generate HTML for content samples."""
        if not alert.context.content_samples:
            return ""
        
        samples_html = "<h4>Content Samples:</h4>"
        for i, sample in enumerate(alert.context.content_samples[:3], 1):
            samples_html += f'<div class="content-sample">Sample {i}: {sample[:200]}{"..." if len(sample) > 200 else ""}</div>'
        
        return samples_html
    
    def _generate_keywords_html(self, alert: Alert) -> str:
        """Generate HTML for keywords."""
        if not alert.context.keywords_matched:
            return ""
        
        keywords = ", ".join(alert.context.keywords_matched[:10])
        return f"<p><strong>Keywords:</strong> {keywords}</p>"
    
    def _generate_metrics_html(self, alert: Alert) -> str:
        """Generate HTML for metrics."""
        metrics_html = ""
        
        if alert.context.volume_metrics:
            metrics_html += "<h4>Volume Metrics:</h4><div>"
            for key, value in alert.context.volume_metrics.items():
                metrics_html += f'<span class="metric">{key.replace("_", " ").title()}: {value}</span>'
            metrics_html += "</div>"
        
        if alert.context.engagement_metrics:
            metrics_html += "<h4>Engagement Metrics:</h4><div>"
            for key, value in alert.context.engagement_metrics.items():
                metrics_html += f'<span class="metric">{key.replace("_", " ").title()}: {value}</span>'
            metrics_html += "</div>"
        
        return metrics_html
    
    async def generate_text_content(self, alert: Alert, template_data: Dict[str, Any]) -> str:
        """Generate plain text email content."""
        severity_icon = self.severity_icons.get(alert.severity, "📢")
        
        text_content = f"""
{severity_icon} PROJECT DHARMA ALERT {severity_icon}

ALERT: {alert.title}
SEVERITY: {alert.severity.upper()}
TYPE: {alert.alert_type.replace('_', ' ').title()}

DESCRIPTION:
{alert.description}

DETAILS:
- Platform: {alert.context.source_platform or 'Unknown'}
- Detection Time: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if alert.created_at else 'Unknown'}
- Confidence Score: {alert.context.confidence_score:.0%}
- Risk Score: {alert.context.risk_score:.0%}
"""
        
        if alert.context.affected_regions:
            text_content += f"- Affected Regions: {', '.join(alert.context.affected_regions[:5])}\n"
        
        if alert.context.content_samples:
            text_content += "\nCONTENT SAMPLES:\n"
            for i, sample in enumerate(alert.context.content_samples[:2], 1):
                text_content += f"{i}. {sample[:150]}{'...' if len(sample) > 150 else ''}\n"
        
        if alert.context.keywords_matched:
            keywords = ", ".join(alert.context.keywords_matched[:10])
            text_content += f"\nKEYWORDS: {keywords}\n"
        
        text_content += f"\nVIEW IN DASHBOARD: {template_data.get('dashboard_url', 'N/A')}\n"
        text_content += f"\nGenerated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        text_content += "\n\nThis is an automated alert from Project Dharma Social Media Intelligence Platform"
        
        return text_content
    
    def generate_summary_email(self, alerts: list, period: str) -> Dict[str, str]:
        """Generate summary email for multiple alerts."""
        total_alerts = len(alerts)
        severity_counts = {}
        
        for alert in alerts:
            severity = alert.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        subject = f"Project Dharma Alert Summary - {total_alerts} alerts in {period}"
        
        html_content = f"""
        <h2>Alert Summary - {period}</h2>
        <p>Total Alerts: <strong>{total_alerts}</strong></p>
        
        <h3>By Severity:</h3>
        <ul>
        """
        
        for severity, count in severity_counts.items():
            html_content += f"<li>{severity.title()}: {count}</li>"
        
        html_content += "</ul>"
        
        return {
            "subject": subject,
            "html_content": html_content,
            "text_content": f"Alert Summary - {period}\nTotal: {total_alerts} alerts"
        }