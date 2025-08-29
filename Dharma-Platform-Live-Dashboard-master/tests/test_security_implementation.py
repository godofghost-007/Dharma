"""
Comprehensive tests for security implementation
Tests encryption, TLS, API key management, and input validation
"""

import pytest
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import Mock, patch
import asyncio

# Import security modules
from shared.security.encryption import EncryptionManager, DataEncryption
from shared.security.tls_manager import TLSManager, CertificateManager
from shared.security.api_key_manager import APIKeyManager, SecureStorage
from shared.security.input_validation import InputValidator, DataSanitizer
from shared.security.config import SecurityConfig


class TestEncryptionManager:
    """Test encryption functionality"""
    
    def setup_method(self):
        """Set up test encryption manager"""
        self.encryption_manager = EncryptionManager()
    
    def test_string_encryption_decryption(self):
        """Test basic string encryption and decryption"""
        plaintext = "This is a test message"
        
        # Encrypt
        encrypted = self.encryption_manager.encrypt_string(plaintext)
        assert encrypted != plaintext
        assert len(encrypted) > 0
        
        # Decrypt
        decrypted = self.encryption_manager.decrypt_string(encrypted)
        assert decrypted == plaintext
    
    def test_dict_encryption_decryption(self):
        """Test dictionary encryption and decryption"""
        test_dict = {
            "username": "test_user",
            "email": "test@example.com",
            "api_key": "secret_key_123"
        }
        
        # Encrypt
        encrypted = self.encryption_manager.encrypt_dict(test_dict)
        assert encrypted != json.dumps(test_dict)
        
        # Decrypt
        decrypted = self.encryption_manager.decrypt_dict(encrypted)
        assert decrypted == test_dict
    
    def test_password_hashing_verification(self):
        """Test password hashing and verification"""
        password = "SecurePassword123!"
        
        # Hash password
        hashed, salt = self.encryption_manager.hash_password(password)
        assert hashed != password
        assert len(salt) > 0
        
        # Verify correct password
        assert self.encryption_manager.verify_password(password, hashed, salt)
        
        # Verify incorrect password
        assert not self.encryption_manager.verify_password("WrongPassword", hashed, salt)
    
    def test_data_encryption_record_processing(self):
        """Test data encryption for database records"""
        data_encryption = DataEncryption(self.encryption_manager)
        
        test_record = {
            "id": 1,
            "username": "test_user",
            "email": "test@example.com",
            "phone": "+1234567890",
            "public_info": "This is public"
        }
        
        # Encrypt sensitive fields
        encrypted_record = data_encryption.encrypt_record(test_record)
        
        # Check that sensitive fields are encrypted
        assert encrypted_record["email"] != test_record["email"]
        assert encrypted_record["phone"] != test_record["phone"]
        assert encrypted_record["email_encrypted"] is True
        assert encrypted_record["phone_encrypted"] is True
        
        # Check that non-sensitive fields are unchanged
        assert encrypted_record["id"] == test_record["id"]
        assert encrypted_record["public_info"] == test_record["public_info"]
        
        # Decrypt record
        decrypted_record = data_encryption.decrypt_record(encrypted_record)
        assert decrypted_record["email"] == test_record["email"]
        assert decrypted_record["phone"] == test_record["phone"]
        assert "email_encrypted" not in decrypted_record
        assert "phone_encrypted" not in decrypted_record


class TestCertificateManager:
    """Test certificate and TLS management"""
    
    def setup_method(self):
        """Set up test certificate manager"""
        self.temp_dir = tempfile.mkdtemp()
        self.cert_manager = CertificateManager(self.temp_dir)
    
    def teardown_method(self):
        """Clean up temporary directory"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_private_key_generation(self):
        """Test RSA private key generation"""
        private_key = self.cert_manager.generate_private_key()
        assert private_key is not None
        assert private_key.key_size == 2048
    
    def test_self_signed_certificate_generation(self):
        """Test self-signed certificate generation"""
        common_name = "test.dharma.local"
        san_list = ["api.dharma.local", "dashboard.dharma.local"]
        
        cert_pem, key_pem = self.cert_manager.generate_self_signed_cert(
            common_name, san_list
        )
        
        assert cert_pem is not None
        assert key_pem is not None
        assert b"BEGIN CERTIFICATE" in cert_pem
        assert b"BEGIN PRIVATE KEY" in key_pem
    
    def test_certificate_save_and_load(self):
        """Test certificate saving and loading"""
        cert_name = "test_cert"
        common_name = "test.dharma.local"
        
        # Generate certificate
        cert_pem, key_pem = self.cert_manager.generate_self_signed_cert(common_name)
        
        # Save certificate
        self.cert_manager.save_certificate(cert_name, cert_pem, key_pem)
        
        # Load certificate
        cert_path, key_path = self.cert_manager.load_certificate(cert_name)
        
        assert os.path.exists(cert_path)
        assert os.path.exists(key_path)
        
        # Verify file permissions
        key_stat = os.stat(key_path)
        assert oct(key_stat.st_mode)[-3:] == '600'  # Owner read/write only
    
    def test_certificate_validation(self):
        """Test certificate validation"""
        cert_name = "validation_test"
        common_name = "test.dharma.local"
        
        # Generate and save certificate
        cert_pem, key_pem = self.cert_manager.generate_self_signed_cert(common_name)
        self.cert_manager.save_certificate(cert_name, cert_pem, key_pem)
        
        # Validate certificate
        cert_path, _ = self.cert_manager.load_certificate(cert_name)
        cert_info = self.cert_manager.validate_certificate(cert_path)
        
        assert cert_info['subject'] is not None
        assert cert_info['issuer'] is not None
        assert not cert_info['is_expired']
        assert cert_info['days_until_expiry'] > 0


class TestAPIKeyManager:
    """Test API key management"""
    
    def setup_method(self):
        """Set up test API key manager"""
        self.temp_dir = tempfile.mkdtemp()
        self.encryption_manager = EncryptionManager()
        self.api_key_manager = APIKeyManager(self.encryption_manager, self.temp_dir)
    
    def teardown_method(self):
        """Clean up temporary directory"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_api_key_generation(self):
        """Test API key generation"""
        service_name = "test_service"
        key_type = "standard"
        
        api_key = self.api_key_manager.generate_api_key(service_name, key_type)
        
        assert api_key.startswith(f"dharma_{service_name}_{key_type}")
        assert len(api_key) > 50  # Should be reasonably long
    
    def test_api_key_validation(self):
        """Test API key validation"""
        service_name = "validation_test"
        
        # Generate key
        api_key = self.api_key_manager.generate_api_key(service_name)
        
        # Validate key
        validation_result = self.api_key_manager.validate_api_key(api_key)
        
        assert validation_result['valid'] is True
        assert validation_result['service_name'] == service_name
        assert validation_result['usage_count'] == 1
    
    def test_api_key_rotation(self):
        """Test API key rotation"""
        service_name = "rotation_test"
        
        # Generate original key
        original_key = self.api_key_manager.generate_api_key(service_name)
        
        # Rotate key
        new_key = self.api_key_manager.rotate_api_key(original_key)
        
        assert new_key != original_key
        assert new_key.startswith(f"dharma_{service_name}")
        
        # Original key should be inactive
        original_validation = self.api_key_manager.validate_api_key(original_key)
        assert original_validation['valid'] is False
        assert original_validation['reason'] == 'Key is inactive'
        
        # New key should be valid
        new_validation = self.api_key_manager.validate_api_key(new_key)
        assert new_validation['valid'] is True
    
    def test_temporary_key_expiration(self):
        """Test temporary key with expiration"""
        service_name = "temp_test"
        
        # Generate temporary key (expires in 0 hours for testing)
        temp_key = self.api_key_manager.generate_temporary_key(service_name, expires_in_hours=0)
        
        # Key should be expired immediately
        validation_result = self.api_key_manager.validate_api_key(temp_key)
        assert validation_result['valid'] is False
        assert validation_result['reason'] == 'Key has expired'
    
    def test_api_key_revocation(self):
        """Test API key revocation"""
        service_name = "revocation_test"
        
        # Generate key
        api_key = self.api_key_manager.generate_api_key(service_name)
        
        # Revoke key
        revoked = self.api_key_manager.revoke_api_key(api_key)
        assert revoked is True
        
        # Key should be invalid
        validation_result = self.api_key_manager.validate_api_key(api_key)
        assert validation_result['valid'] is False
        assert validation_result['reason'] == 'Key is inactive'


class TestInputValidation:
    """Test input validation and sanitization"""
    
    def setup_method(self):
        """Set up test validator and sanitizer"""
        self.validator = InputValidator()
        self.sanitizer = DataSanitizer()
    
    def test_email_validation(self):
        """Test email validation"""
        # Valid emails
        valid_emails = [
            "test@example.com",
            "user.name+tag@domain.co.uk",
            "test123@test-domain.org"
        ]
        
        for email in valid_emails:
            result = self.validator.validate_email(email)
            assert result['valid'] is True
            assert result['sanitized'] == email.lower().strip()
        
        # Invalid emails
        invalid_emails = [
            "invalid-email",
            "@domain.com",
            "test@",
            "test..test@domain.com"
        ]
        
        for email in invalid_emails:
            result = self.validator.validate_email(email)
            assert result['valid'] is False
    
    def test_password_validation(self):
        """Test password strength validation"""
        # Valid passwords
        valid_passwords = [
            "SecurePass123!",
            "MyP@ssw0rd2024",
            "C0mpl3x!P@ssw0rd"
        ]
        
        for password in valid_passwords:
            result = self.validator.validate_password(password)
            assert result['valid'] is True
        
        # Invalid passwords
        invalid_passwords = [
            "weak",  # Too short
            "nouppercase123!",  # No uppercase
            "NOLOWERCASE123!",  # No lowercase
            "NoNumbers!",  # No digits
            "NoSpecialChars123"  # No special characters
        ]
        
        for password in invalid_passwords:
            result = self.validator.validate_password(password)
            assert result['valid'] is False
    
    def test_sql_injection_detection(self):
        """Test SQL injection detection"""
        # Malicious inputs
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "1 OR 1=1",
            "admin'--",
            "UNION SELECT * FROM passwords"
        ]
        
        for malicious_input in malicious_inputs:
            result = self.validator.detect_sql_injection(malicious_input)
            assert result['detected'] is True
        
        # Safe inputs
        safe_inputs = [
            "normal text",
            "user@example.com",
            "Product name with numbers 123"
        ]
        
        for safe_input in safe_inputs:
            result = self.validator.detect_sql_injection(safe_input)
            assert result['detected'] is False
    
    def test_xss_detection(self):
        """Test XSS detection"""
        # Malicious inputs
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "<iframe src='javascript:alert(1)'></iframe>"
        ]
        
        for malicious_input in malicious_inputs:
            result = self.validator.detect_xss(malicious_input)
            assert result['detected'] is True
        
        # Safe inputs
        safe_inputs = [
            "Normal text content",
            "Email: user@example.com",
            "Price: $19.99"
        ]
        
        for safe_input in safe_inputs:
            result = self.validator.detect_xss(safe_input)
            assert result['detected'] is False
    
    def test_html_sanitization(self):
        """Test HTML content sanitization"""
        # Test with malicious HTML
        malicious_html = """
        <p>Safe content</p>
        <script>alert('xss')</script>
        <img src=x onerror=alert('xss')>
        <strong>Bold text</strong>
        """
        
        sanitized = self.sanitizer.sanitize_html(malicious_html)
        
        # Should keep safe tags
        assert "<p>Safe content</p>" in sanitized
        assert "<strong>Bold text</strong>" in sanitized
        
        # Should remove dangerous content
        assert "<script>" not in sanitized
        assert "onerror" not in sanitized
        assert "alert" not in sanitized
    
    def test_text_sanitization(self):
        """Test text sanitization"""
        # Test with various inputs
        test_inputs = [
            ("Normal text", "Normal text"),
            ("  Whitespace  text  ", "Whitespace text"),
            ("<script>alert('xss')</script>", "&lt;script&gt;alert('xss')&lt;/script&gt;"),
            ("Text\x00with\x01control\x02chars", "Textwithcontrolchars")
        ]
        
        for input_text, expected in test_inputs:
            sanitized = self.sanitizer.sanitize_text(input_text)
            assert sanitized == expected
    
    def test_filename_sanitization(self):
        """Test filename sanitization"""
        # Test with various filenames
        test_filenames = [
            ("normal_file.txt", "normal_file.txt"),
            ("file with spaces.pdf", "file with spaces.pdf"),
            ("../../../etc/passwd", "etcpasswd"),
            ("file<>:\"/\\|?*.txt", "file.txt"),
            ("", "unnamed_file")
        ]
        
        for input_filename, expected in test_filenames:
            sanitized = self.sanitizer.sanitize_filename(input_filename)
            assert sanitized == expected


class TestSecurityConfig:
    """Test security configuration and integration"""
    
    def setup_method(self):
        """Set up test security configuration"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test configuration
        test_config = {
            'encryption': {
                'master_key': 'test_master_key_for_testing_only',
                'key_rotation_days': 90
            },
            'tls': {
                'cert_dir': os.path.join(self.temp_dir, 'certs'),
                'auto_generate_certs': True
            },
            'api_keys': {
                'storage_path': os.path.join(self.temp_dir, 'keys'),
                'default_expiry_hours': 24
            },
            'secure_storage': {
                'storage_path': os.path.join(self.temp_dir, 'secure')
            },
            'validation': {
                'max_request_size': 1024 * 1024,
                'enable_sql_injection_detection': True,
                'enable_xss_detection': True
            }
        }
        
        self.security_config = SecurityConfig(test_config)
    
    def teardown_method(self):
        """Clean up temporary directory"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_security_components_initialization(self):
        """Test that all security components are properly initialized"""
        assert self.security_config.encryption_manager is not None
        assert self.security_config.tls_manager is not None
        assert self.security_config.api_key_manager is not None
        assert self.security_config.secure_storage is not None
        assert self.security_config.input_validator is not None
        assert self.security_config.data_sanitizer is not None
    
    def test_service_security_setup(self):
        """Test security setup for a service"""
        service_name = "test_service"
        
        security_setup = self.security_config.setup_service_security(service_name)
        
        assert 'api_key' in security_setup
        assert 'ssl_context' in security_setup
        assert 'tls_config' in security_setup
        assert 'security_headers' in security_setup
        
        # Verify API key format
        api_key = security_setup['api_key']
        assert api_key.startswith(f"dharma_{service_name}")
    
    def test_request_validation_and_sanitization(self):
        """Test request validation and sanitization"""
        # Test with valid request
        valid_request = {
            "username": "test_user",
            "email": "test@example.com",
            "message": "This is a normal message"
        }
        
        result = self.security_config.validate_and_sanitize_request(valid_request)
        
        assert result['valid'] is True
        assert len(result['errors']) == 0
        assert 'sanitized_data' in result
        
        # Test with malicious request
        malicious_request = {
            "username": "'; DROP TABLE users; --",
            "message": "<script>alert('xss')</script>"
        }
        
        result = self.security_config.validate_and_sanitize_request(malicious_request)
        
        # Should detect security issues
        assert len(result['security_warnings']) > 0
        
        # Should still sanitize the data
        assert 'sanitized_data' in result
    
    def test_security_headers(self):
        """Test security headers generation"""
        headers = self.security_config.get_security_headers()
        
        required_headers = [
            'Strict-Transport-Security',
            'X-Content-Type-Options',
            'X-Frame-Options',
            'X-XSS-Protection',
            'Content-Security-Policy'
        ]
        
        for header in required_headers:
            assert header in headers
            assert len(headers[header]) > 0


@pytest.mark.asyncio
async def test_tls_connection_verification():
    """Test TLS connection verification"""
    temp_dir = tempfile.mkdtemp()
    
    try:
        cert_manager = CertificateManager(temp_dir)
        tls_manager = TLSManager(cert_manager)
        
        # Test connection to a known HTTPS service
        result = await tls_manager.verify_tls_connection("httpbin.org", 443, timeout=5)
        
        # Should successfully connect
        assert result['success'] is True
        assert 'certificate' in result
        assert 'cipher' in result
        
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    # Run basic tests
    print("Running security implementation tests...")
    
    # Test encryption
    print("Testing encryption...")
    test_encryption = TestEncryptionManager()
    test_encryption.setup_method()
    test_encryption.test_string_encryption_decryption()
    test_encryption.test_password_hashing_verification()
    print("✓ Encryption tests passed")
    
    # Test input validation
    print("Testing input validation...")
    test_validation = TestInputValidation()
    test_validation.setup_method()
    test_validation.test_email_validation()
    test_validation.test_sql_injection_detection()
    test_validation.test_xss_detection()
    print("✓ Input validation tests passed")
    
    print("All security tests completed successfully!")