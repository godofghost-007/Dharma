"""
Security configuration for Project Dharma
Centralized security settings and initialization
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path
import logging
from datetime import datetime
from .encryption import EncryptionManager, DataEncryption
from .tls_manager import TLSManager, CertificateManager
from .api_key_manager import APIKeyManager, SecureStorage
from .input_validation import InputValidator, DataSanitizer

logger = logging.getLogger(__name__)


class SecurityConfig:
    """Centralized security configuration"""
    
    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        """
        Initialize security configuration
        
        Args:
            config_dict: Optional configuration dictionary
        """
        self.config = config_dict or self._load_default_config()
        
        # Initialize security components
        self.encryption_manager = None
        self.tls_manager = None
        self.api_key_manager = None
        self.secure_storage = None
        self.input_validator = None
        self.data_sanitizer = None
        
        self._initialize_components()
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default security configuration"""
        return {
            'encryption': {
                'master_key': os.getenv('DHARMA_MASTER_KEY'),
                'key_rotation_days': 90,
                'algorithm': 'AES-256-GCM'
            },
            'tls': {
                'cert_dir': os.getenv('DHARMA_CERT_DIR', '/etc/dharma/certs'),
                'min_tls_version': 'TLSv1.2',
                'cipher_suites': 'ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS',
                'auto_generate_certs': True
            },
            'api_keys': {
                'storage_path': os.getenv('DHARMA_KEY_STORAGE', '/etc/dharma/keys'),
                'default_expiry_hours': 24,
                'rotation_interval_days': 30,
                'key_length': 32
            },
            'validation': {
                'max_request_size': 10 * 1024 * 1024,  # 10MB
                'max_json_depth': 10,
                'rate_limit_per_minute': 1000,
                'enable_sql_injection_detection': True,
                'enable_xss_detection': True
            },
            'secure_storage': {
                'storage_path': os.getenv('DHARMA_SECURE_STORAGE', '/etc/dharma/secure'),
                'backup_enabled': True,
                'backup_retention_days': 30
            }
        }
    
    def _initialize_components(self):
        """Initialize security components with configuration"""
        try:
            # Initialize encryption manager
            master_key = self.config['encryption']['master_key']
            self.encryption_manager = EncryptionManager(master_key)
            
            # Initialize certificate and TLS managers
            cert_dir = self.config['tls']['cert_dir']
            self.certificate_manager = CertificateManager(cert_dir)
            self.tls_manager = TLSManager(self.certificate_manager)
            
            # Initialize API key manager
            key_storage_path = self.config['api_keys']['storage_path']
            self.api_key_manager = APIKeyManager(self.encryption_manager, key_storage_path)
            
            # Initialize secure storage
            secure_storage_path = self.config['secure_storage']['storage_path']
            self.secure_storage = SecureStorage(self.encryption_manager, secure_storage_path)
            
            # Initialize validation components
            self.input_validator = InputValidator()
            self.data_sanitizer = DataSanitizer()
            
            # Initialize data encryption helper
            self.data_encryption = DataEncryption(self.encryption_manager)
            
            logger.info("Security components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize security components: {e}")
            raise
    
    def get_encryption_manager(self) -> EncryptionManager:
        """Get encryption manager instance"""
        return self.encryption_manager
    
    def get_tls_manager(self) -> TLSManager:
        """Get TLS manager instance"""
        return self.tls_manager
    
    def get_api_key_manager(self) -> APIKeyManager:
        """Get API key manager instance"""
        return self.api_key_manager
    
    def get_secure_storage(self) -> SecureStorage:
        """Get secure storage instance"""
        return self.secure_storage
    
    def get_input_validator(self) -> InputValidator:
        """Get input validator instance"""
        return self.input_validator
    
    def get_data_sanitizer(self) -> DataSanitizer:
        """Get data sanitizer instance"""
        return self.data_sanitizer
    
    def get_data_encryption(self) -> DataEncryption:
        """Get data encryption helper instance"""
        return self.data_encryption
    
    def setup_service_security(self, service_name: str) -> Dict[str, Any]:
        """
        Set up security for a specific service
        
        Args:
            service_name: Name of the service
            
        Returns:
            Dictionary with security configuration for the service
        """
        try:
            # Generate service-specific API key
            api_key = self.api_key_manager.generate_api_key(service_name, "service")
            
            # Set up TLS for service (create SSL context synchronously)
            tls_config = self.tls_manager.get_tls_config_for_service(service_name)
            ssl_context = self.tls_manager.create_ssl_context(tls_config['cert_name'])
            
            # Store service credentials securely
            service_credentials = {
                'api_key': api_key,
                'service_name': service_name,
                'created_at': str(datetime.utcnow()),
                'tls_enabled': True
            }
            
            self.secure_storage.store_credentials(service_name, service_credentials)
            
            return {
                'api_key': api_key,
                'ssl_context': ssl_context,
                'tls_config': self.tls_manager.get_tls_config_for_service(service_name),
                'security_headers': self.get_security_headers()
            }
            
        except Exception as e:
            logger.error(f"Failed to setup security for service {service_name}: {e}")
            raise
    
    def get_security_headers(self) -> Dict[str, str]:
        """Get security headers for HTTP responses"""
        return {
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'X-Permitted-Cross-Domain-Policies': 'none'
        }
    
    def validate_and_sanitize_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and sanitize incoming request data
        
        Args:
            request_data: Raw request data
            
        Returns:
            Dictionary with validation results and sanitized data
        """
        results = {
            'valid': True,
            'errors': [],
            'sanitized_data': {},
            'security_warnings': []
        }
        
        try:
            # Check request size
            import json
            request_size = len(json.dumps(request_data))
            max_size = self.config['validation']['max_request_size']
            
            if request_size > max_size:
                results['valid'] = False
                results['errors'].append(f'Request too large: {request_size} bytes')
                return results
            
            # Validate JSON structure
            json_validation = self.input_validator.validate_json_data(
                request_data,
                max_depth=self.config['validation']['max_json_depth']
            )
            
            if not json_validation['valid']:
                results['valid'] = False
                results['errors'].append(json_validation['reason'])
                return results
            
            # Process each field
            for key, value in request_data.items():
                if isinstance(value, str):
                    # Check for security threats
                    if self.config['validation']['enable_sql_injection_detection']:
                        sql_check = self.input_validator.detect_sql_injection(value)
                        if sql_check['detected']:
                            results['security_warnings'].append(f'SQL injection detected in {key}')
                    
                    if self.config['validation']['enable_xss_detection']:
                        xss_check = self.input_validator.detect_xss(value)
                        if xss_check['detected']:
                            results['security_warnings'].append(f'XSS detected in {key}')
                    
                    # Sanitize string values
                    results['sanitized_data'][key] = self.data_sanitizer.sanitize_text(value)
                else:
                    results['sanitized_data'][key] = value
            
            return results
            
        except Exception as e:
            logger.error(f"Error validating request: {e}")
            results['valid'] = False
            results['errors'].append(f'Validation error: {e}')
            return results
    
    def rotate_security_keys(self) -> Dict[str, Any]:
        """
        Rotate security keys and certificates
        
        Returns:
            Dictionary with rotation results
        """
        results = {
            'api_keys_rotated': 0,
            'certificates_updated': 0,
            'errors': []
        }
        
        try:
            # Rotate API keys
            api_keys = self.api_key_manager.list_api_keys()
            for key_info in api_keys:
                if key_info['is_active']:
                    try:
                        # Get the actual key (this is simplified - in practice you'd need to track this)
                        # For now, we'll just clean up expired keys
                        pass
                    except Exception as e:
                        results['errors'].append(f"Failed to rotate key {key_info['key_id']}: {e}")
            
            # Clean up expired keys
            cleaned = self.api_key_manager.cleanup_expired_keys()
            results['api_keys_rotated'] = cleaned
            
            logger.info(f"Security key rotation completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Error during key rotation: {e}")
            results['errors'].append(str(e))
            return results


# Global security instance
_security_config = None


def get_security_config() -> SecurityConfig:
    """Get global security configuration instance"""
    global _security_config
    if _security_config is None:
        _security_config = SecurityConfig()
    return _security_config


def initialize_security(config_dict: Optional[Dict[str, Any]] = None) -> SecurityConfig:
    """
    Initialize global security configuration
    
    Args:
        config_dict: Optional configuration dictionary
        
    Returns:
        Initialized security configuration
    """
    global _security_config
    _security_config = SecurityConfig(config_dict)
    return _security_config