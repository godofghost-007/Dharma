"""
Input validation and sanitization utilities for Project Dharma
Provides comprehensive input validation and data sanitization
"""

import re
import html
import urllib.parse
from typing import Any, Dict, List, Optional, Union, Callable
import bleach
import validators
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class InputValidator:
    """Comprehensive input validation for API requests and user data"""
    
    def __init__(self):
        """Initialize input validator with security rules"""
        self.email_pattern = re.compile(r'^[a-zA-Z0-9]([a-zA-Z0-9._%-]*[a-zA-Z0-9])?@[a-zA-Z0-9]([a-zA-Z0-9.-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,}$')
        self.phone_pattern = re.compile(r'^\+?[1-9]\d{1,14}$')  # E.164 format
        self.username_pattern = re.compile(r'^[a-zA-Z0-9_-]{3,30}$')
        self.api_key_pattern = re.compile(r'^dharma_[a-zA-Z0-9_-]+_[a-zA-Z0-9]{32}$')
        
        # SQL injection patterns
        self.sql_injection_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
            r"(--|#|/\*|\*/)",
            r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
            r"(\'\s*(OR|AND)\s*\'\w*\'\s*=\s*\'\w*\')",
        ]
        
        # XSS patterns
        self.xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>.*?</iframe>",
        ]
    
    def validate_email(self, email: str) -> Dict[str, Any]:
        """Validate email address format"""
        if not isinstance(email, str):
            return {'valid': False, 'reason': 'Email must be a string'}
        
        if len(email) > 254:  # RFC 5321 limit
            return {'valid': False, 'reason': 'Email too long'}
        
        # Use validators library for more accurate email validation
        if not validators.email(email):
            return {'valid': False, 'reason': 'Invalid email format'}
        
        return {'valid': True, 'sanitized': email.lower().strip()}
    
    def validate_phone(self, phone: str) -> Dict[str, Any]:
        """Validate phone number format"""
        if not isinstance(phone, str):
            return {'valid': False, 'reason': 'Phone must be a string'}
        
        # Remove common formatting characters
        cleaned_phone = re.sub(r'[\s\-\(\)]', '', phone)
        
        if not self.phone_pattern.match(cleaned_phone):
            return {'valid': False, 'reason': 'Invalid phone format'}
        
        return {'valid': True, 'sanitized': cleaned_phone}
    
    def validate_username(self, username: str) -> Dict[str, Any]:
        """Validate username format"""
        if not isinstance(username, str):
            return {'valid': False, 'reason': 'Username must be a string'}
        
        if not self.username_pattern.match(username):
            return {'valid': False, 'reason': 'Username must be 3-30 chars, alphanumeric, underscore, or dash'}
        
        return {'valid': True, 'sanitized': username.lower().strip()}
    
    def validate_password(self, password: str) -> Dict[str, Any]:
        """Validate password strength"""
        if not isinstance(password, str):
            return {'valid': False, 'reason': 'Password must be a string'}
        
        if len(password) < 8:
            return {'valid': False, 'reason': 'Password must be at least 8 characters'}
        
        if len(password) > 128:
            return {'valid': False, 'reason': 'Password too long'}
        
        # Check for required character types
        has_upper = bool(re.search(r'[A-Z]', password))
        has_lower = bool(re.search(r'[a-z]', password))
        has_digit = bool(re.search(r'\d', password))
        has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
        
        if not all([has_upper, has_lower, has_digit, has_special]):
            return {
                'valid': False, 
                'reason': 'Password must contain uppercase, lowercase, digit, and special character'
            }
        
        return {'valid': True}
    
    def validate_url(self, url: str) -> Dict[str, Any]:
        """Validate URL format and safety"""
        if not isinstance(url, str):
            return {'valid': False, 'reason': 'URL must be a string'}
        
        if len(url) > 2048:  # Common URL length limit
            return {'valid': False, 'reason': 'URL too long'}
        
        if not validators.url(url):
            return {'valid': False, 'reason': 'Invalid URL format'}
        
        # Check for dangerous protocols
        dangerous_protocols = ['javascript:', 'data:', 'vbscript:', 'file:']
        url_lower = url.lower()
        
        for protocol in dangerous_protocols:
            if url_lower.startswith(protocol):
                return {'valid': False, 'reason': f'Dangerous protocol: {protocol}'}
        
        return {'valid': True, 'sanitized': url.strip()}
    
    def validate_api_key(self, api_key: str) -> Dict[str, Any]:
        """Validate API key format"""
        if not isinstance(api_key, str):
            return {'valid': False, 'reason': 'API key must be a string'}
        
        if not self.api_key_pattern.match(api_key):
            return {'valid': False, 'reason': 'Invalid API key format'}
        
        return {'valid': True}
    
    def validate_json_data(self, data: Any, max_depth: int = 10, max_size: int = 1024*1024) -> Dict[str, Any]:
        """Validate JSON data structure and size"""
        import json
        import sys
        
        try:
            # Check serialization size
            json_str = json.dumps(data)
            if len(json_str) > max_size:
                return {'valid': False, 'reason': f'JSON data too large: {len(json_str)} bytes'}
            
            # Check nesting depth
            def check_depth(obj, current_depth=0):
                if current_depth > max_depth:
                    return False
                
                if isinstance(obj, dict):
                    return all(check_depth(v, current_depth + 1) for v in obj.values())
                elif isinstance(obj, list):
                    return all(check_depth(item, current_depth + 1) for item in obj)
                
                return True
            
            if not check_depth(data):
                return {'valid': False, 'reason': f'JSON nesting too deep (max: {max_depth})'}
            
            return {'valid': True}
            
        except (TypeError, ValueError) as e:
            return {'valid': False, 'reason': f'Invalid JSON data: {e}'}
    
    def detect_sql_injection(self, text: str) -> Dict[str, Any]:
        """Detect potential SQL injection attempts"""
        if not isinstance(text, str):
            return {'detected': False}
        
        text_upper = text.upper()
        
        for pattern in self.sql_injection_patterns:
            if re.search(pattern, text_upper, re.IGNORECASE):
                return {
                    'detected': True,
                    'pattern': pattern,
                    'reason': 'Potential SQL injection detected'
                }
        
        return {'detected': False}
    
    def detect_xss(self, text: str) -> Dict[str, Any]:
        """Detect potential XSS attempts"""
        if not isinstance(text, str):
            return {'detected': False}
        
        for pattern in self.xss_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return {
                    'detected': True,
                    'pattern': pattern,
                    'reason': 'Potential XSS detected'
                }
        
        return {'detected': False}


class DataSanitizer:
    """Data sanitization utilities for user input"""
    
    def __init__(self):
        """Initialize data sanitizer with safe configurations"""
        # Allowed HTML tags and attributes for rich text
        self.allowed_tags = [
            'p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote'
        ]
        
        self.allowed_attributes = {
            '*': ['class'],
            'a': ['href', 'title'],
            'img': ['src', 'alt', 'width', 'height']
        }
    
    def sanitize_html(self, html_content: str, strip_tags: bool = False) -> str:
        """Sanitize HTML content to prevent XSS"""
        if not isinstance(html_content, str):
            return str(html_content)
        
        if strip_tags:
            # Strip all HTML tags
            return bleach.clean(html_content, tags=[], strip=True)
        else:
            # Allow safe HTML tags only
            return bleach.clean(
                html_content,
                tags=self.allowed_tags,
                attributes=self.allowed_attributes,
                strip=True
            )
    
    def sanitize_text(self, text: str, max_length: Optional[int] = None) -> str:
        """Sanitize plain text input"""
        if not isinstance(text, str):
            text = str(text)
        
        # HTML escape
        sanitized = html.escape(text)
        
        # Remove control characters except newlines and tabs
        sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', sanitized)
        
        # Normalize whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        # Truncate if needed
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length].rstrip()
        
        return sanitized
    
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe storage"""
        if not isinstance(filename, str):
            filename = str(filename)
        
        # Remove path separators and dangerous characters
        sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', filename)
        
        # Remove leading/trailing dots and spaces
        sanitized = sanitized.strip('. ')
        
        # Limit length
        if len(sanitized) > 255:
            name, ext = os.path.splitext(sanitized)
            sanitized = name[:255-len(ext)] + ext
        
        # Ensure not empty
        if not sanitized:
            sanitized = 'unnamed_file'
        
        return sanitized
    
    def sanitize_sql_identifier(self, identifier: str) -> str:
        """Sanitize SQL identifiers (table/column names)"""
        if not isinstance(identifier, str):
            identifier = str(identifier)
        
        # Only allow alphanumeric and underscore
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '', identifier)
        
        # Ensure starts with letter or underscore
        if sanitized and sanitized[0].isdigit():
            sanitized = '_' + sanitized
        
        # Limit length
        if len(sanitized) > 63:  # PostgreSQL limit
            sanitized = sanitized[:63]
        
        return sanitized
    
    def sanitize_search_query(self, query: str) -> str:
        """Sanitize search query input"""
        if not isinstance(query, str):
            query = str(query)
        
        # Remove special regex characters that could cause issues
        sanitized = re.sub(r'[.*+?^${}()|[\]\\]', '', query)
        
        # Normalize whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        # Limit length
        if len(sanitized) > 200:
            sanitized = sanitized[:200].rstrip()
        
        return sanitized


class ValidationRules:
    """Predefined validation rules for common data types"""
    
    @staticmethod
    def create_string_validator(min_length: int = 0, 
                              max_length: int = 1000,
                              pattern: Optional[str] = None,
                              required: bool = True) -> Callable:
        """Create a string validator with custom rules"""
        def validator(value: Any) -> Dict[str, Any]:
            if value is None:
                if required:
                    return {'valid': False, 'reason': 'Field is required'}
                return {'valid': True, 'sanitized': None}
            
            if not isinstance(value, str):
                return {'valid': False, 'reason': 'Value must be a string'}
            
            if len(value) < min_length:
                return {'valid': False, 'reason': f'Minimum length is {min_length}'}
            
            if len(value) > max_length:
                return {'valid': False, 'reason': f'Maximum length is {max_length}'}
            
            if pattern and not re.match(pattern, value):
                return {'valid': False, 'reason': 'Value does not match required pattern'}
            
            return {'valid': True, 'sanitized': value.strip()}
        
        return validator
    
    @staticmethod
    def create_integer_validator(min_value: Optional[int] = None,
                               max_value: Optional[int] = None,
                               required: bool = True) -> Callable:
        """Create an integer validator with custom rules"""
        def validator(value: Any) -> Dict[str, Any]:
            if value is None:
                if required:
                    return {'valid': False, 'reason': 'Field is required'}
                return {'valid': True, 'sanitized': None}
            
            try:
                int_value = int(value)
            except (ValueError, TypeError):
                return {'valid': False, 'reason': 'Value must be an integer'}
            
            if min_value is not None and int_value < min_value:
                return {'valid': False, 'reason': f'Minimum value is {min_value}'}
            
            if max_value is not None and int_value > max_value:
                return {'valid': False, 'reason': f'Maximum value is {max_value}'}
            
            return {'valid': True, 'sanitized': int_value}
        
        return validator
    
    @staticmethod
    def create_list_validator(item_validator: Callable,
                            min_items: int = 0,
                            max_items: int = 100,
                            required: bool = True) -> Callable:
        """Create a list validator with item validation"""
        def validator(value: Any) -> Dict[str, Any]:
            if value is None:
                if required:
                    return {'valid': False, 'reason': 'Field is required'}
                return {'valid': True, 'sanitized': None}
            
            if not isinstance(value, list):
                return {'valid': False, 'reason': 'Value must be a list'}
            
            if len(value) < min_items:
                return {'valid': False, 'reason': f'Minimum {min_items} items required'}
            
            if len(value) > max_items:
                return {'valid': False, 'reason': f'Maximum {max_items} items allowed'}
            
            sanitized_items = []
            for i, item in enumerate(value):
                item_result = item_validator(item)
                if not item_result['valid']:
                    return {'valid': False, 'reason': f'Item {i}: {item_result["reason"]}'}
                sanitized_items.append(item_result.get('sanitized', item))
            
            return {'valid': True, 'sanitized': sanitized_items}
        
        return validator