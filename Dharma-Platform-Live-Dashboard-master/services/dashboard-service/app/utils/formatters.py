"""
Utility functions for formatting data in the dashboard
"""

from typing import Union, Optional
from datetime import datetime, timedelta

def format_number(value: Union[int, float], precision: int = 0) -> str:
    """Format numbers with appropriate suffixes (K, M, B)"""
    if value is None:
        return "0"
    
    try:
        value = float(value)
    except (ValueError, TypeError):
        return str(value)
    
    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:.{precision}f}B"
    elif abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.{precision}f}M"
    elif abs(value) >= 1_000:
        return f"{value / 1_000:.{precision}f}K"
    else:
        return f"{value:.{precision}f}"

def format_percentage(value: Union[int, float], precision: int = 1) -> str:
    """Format percentage values"""
    if value is None:
        return "0.0%"
    
    try:
        value = float(value)
        return f"{value:.{precision}f}%"
    except (ValueError, TypeError):
        return "0.0%"

def format_datetime(dt: Union[datetime, str], format_str: str = "%Y-%m-%d %H:%M") -> str:
    """Format datetime objects or ISO strings"""
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except ValueError:
            return dt
    
    if isinstance(dt, datetime):
        return dt.strftime(format_str)
    
    return str(dt)

def format_time_ago(dt: Union[datetime, str]) -> str:
    """Format datetime as 'time ago' string"""
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except ValueError:
            return dt
    
    if not isinstance(dt, datetime):
        return str(dt)
    
    now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    else:
        return "Just now"

def format_duration(seconds: Union[int, float]) -> str:
    """Format duration in seconds to human readable format"""
    if seconds is None:
        return "0s"
    
    try:
        seconds = int(seconds)
    except (ValueError, TypeError):
        return str(seconds)
    
    if seconds >= 3600:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"
    elif seconds >= 60:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m {secs}s"
    else:
        return f"{seconds}s"

def format_file_size(bytes_size: Union[int, float]) -> str:
    """Format file size in bytes to human readable format"""
    if bytes_size is None:
        return "0 B"
    
    try:
        bytes_size = float(bytes_size)
    except (ValueError, TypeError):
        return str(bytes_size)
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    
    return f"{bytes_size:.1f} PB"

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to specified length"""
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def format_sentiment_score(score: Union[int, float]) -> tuple[str, str]:
    """Format sentiment score and return (label, color)"""
    if score is None:
        return ("Unknown", "gray")
    
    try:
        score = float(score)
    except (ValueError, TypeError):
        return ("Unknown", "gray")
    
    if score >= 0.7:
        return ("Positive", "green")
    elif score >= 0.3:
        return ("Neutral", "blue")
    else:
        return ("Negative", "red")

def format_risk_level(risk_score: Union[int, float]) -> tuple[str, str]:
    """Format risk score and return (level, color)"""
    if risk_score is None:
        return ("Unknown", "gray")
    
    try:
        risk_score = float(risk_score)
    except (ValueError, TypeError):
        return ("Unknown", "gray")
    
    if risk_score >= 0.8:
        return ("Critical", "red")
    elif risk_score >= 0.6:
        return ("High", "orange")
    elif risk_score >= 0.4:
        return ("Medium", "yellow")
    elif risk_score >= 0.2:
        return ("Low", "green")
    else:
        return ("Minimal", "blue")