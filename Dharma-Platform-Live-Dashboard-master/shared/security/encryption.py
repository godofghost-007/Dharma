"""
Data encryption utilities for Project Dharma
Implements AES-256 encryption for data at rest and sensitive information
"""

import os
import base64
import hashlib
from typing import Union, Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import json
import logging

logger = logging.getLogger(__name__)


class EncryptionManager:
    """Manages encryption keys and provides encryption/decryption services"""
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize encryption manager with master key
        
        Args:
            master_key: Master encryption key (if None, generates new key)
        """
        self.backend = default_backend()
        
        if master_key:
            self.master_key = master_key.encode()
        else:
            self.master_key = self._generate_master_key()
        
        self.fernet = self._create_fernet_cipher()
        
    def _generate_master_key(self) -> bytes:
        """Generate a new master encryption key"""
        return os.urandom(32)  # 256-bit key
    
    def _create_fernet_cipher(self) -> Fernet:
        """Create Fernet cipher from master key"""
        # Derive key using PBKDF2
        salt = b'dharma_platform_salt'  # In production, use random salt per key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=self.backend
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key))
        return Fernet(key)
    
    def encrypt_string(self, plaintext: str) -> str:
        """
        Encrypt a string value
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Base64 encoded encrypted string
        """
        try:
            encrypted_bytes = self.fernet.encrypt(plaintext.encode())
            return base64.b64encode(encrypted_bytes).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt_string(self, encrypted_text: str) -> str:
        """
        Decrypt a string value
        
        Args:
            encrypted_text: Base64 encoded encrypted string
            
        Returns:
            Decrypted plaintext string
        """
        try:
            encrypted_bytes = base64.b64decode(encrypted_text.encode())
            decrypted_bytes = self.fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    def encrypt_dict(self, data: Dict[str, Any]) -> str:
        """
        Encrypt a dictionary as JSON
        
        Args:
            data: Dictionary to encrypt
            
        Returns:
            Base64 encoded encrypted JSON string
        """
        json_string = json.dumps(data, sort_keys=True)
        return self.encrypt_string(json_string)
    
    def decrypt_dict(self, encrypted_text: str) -> Dict[str, Any]:
        """
        Decrypt a dictionary from encrypted JSON
        
        Args:
            encrypted_text: Base64 encoded encrypted JSON string
            
        Returns:
            Decrypted dictionary
        """
        json_string = self.decrypt_string(encrypted_text)
        return json.loads(json_string)
    
    def hash_password(self, password: str, salt: Optional[bytes] = None) -> tuple[str, str]:
        """
        Hash a password using PBKDF2
        
        Args:
            password: Password to hash
            salt: Optional salt (generates random if None)
            
        Returns:
            Tuple of (hashed_password, salt) as base64 strings
        """
        if salt is None:
            salt = os.urandom(32)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=self.backend
        )
        
        hashed = kdf.derive(password.encode())
        return (
            base64.b64encode(hashed).decode(),
            base64.b64encode(salt).decode()
        )
    
    def verify_password(self, password: str, hashed_password: str, salt: str) -> bool:
        """
        Verify a password against its hash
        
        Args:
            password: Password to verify
            hashed_password: Base64 encoded hashed password
            salt: Base64 encoded salt
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            salt_bytes = base64.b64decode(salt.encode())
            expected_hash = base64.b64decode(hashed_password.encode())
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt_bytes,
                iterations=100000,
                backend=self.backend
            )
            
            kdf.verify(password.encode(), expected_hash)
            return True
        except Exception:
            return False


class DataEncryption:
    """Handles encryption of sensitive data fields in database records"""
    
    def __init__(self, encryption_manager: EncryptionManager):
        self.encryption_manager = encryption_manager
        self.sensitive_fields = {
            'email', 'phone', 'api_key', 'token', 'password',
            'personal_info', 'location', 'ip_address'
        }
    
    def encrypt_record(self, record: Dict[str, Any], 
                      fields_to_encrypt: Optional[set] = None) -> Dict[str, Any]:
        """
        Encrypt sensitive fields in a database record
        
        Args:
            record: Database record dictionary
            fields_to_encrypt: Specific fields to encrypt (uses default if None)
            
        Returns:
            Record with encrypted sensitive fields
        """
        if fields_to_encrypt is None:
            fields_to_encrypt = self.sensitive_fields
        
        encrypted_record = record.copy()
        
        for field, value in record.items():
            if field in fields_to_encrypt and value is not None:
                if isinstance(value, str):
                    encrypted_record[field] = self.encryption_manager.encrypt_string(value)
                elif isinstance(value, dict):
                    encrypted_record[field] = self.encryption_manager.encrypt_dict(value)
                
                # Mark field as encrypted
                encrypted_record[f"{field}_encrypted"] = True
        
        return encrypted_record
    
    def decrypt_record(self, record: Dict[str, Any],
                      fields_to_decrypt: Optional[set] = None) -> Dict[str, Any]:
        """
        Decrypt sensitive fields in a database record
        
        Args:
            record: Database record with encrypted fields
            fields_to_decrypt: Specific fields to decrypt (uses default if None)
            
        Returns:
            Record with decrypted sensitive fields
        """
        if fields_to_decrypt is None:
            fields_to_decrypt = self.sensitive_fields
        
        decrypted_record = record.copy()
        
        for field in fields_to_decrypt:
            if f"{field}_encrypted" in record and record[f"{field}_encrypted"]:
                try:
                    if field in record and record[field] is not None:
                        # Try to decrypt as dict first, then as string
                        try:
                            decrypted_record[field] = self.encryption_manager.decrypt_dict(record[field])
                        except (json.JSONDecodeError, ValueError):
                            decrypted_record[field] = self.encryption_manager.decrypt_string(record[field])
                        
                        # Remove encryption marker
                        decrypted_record.pop(f"{field}_encrypted", None)
                except Exception as e:
                    logger.error(f"Failed to decrypt field {field}: {e}")
                    # Keep encrypted value if decryption fails
        
        return decrypted_record
    
    def is_field_encrypted(self, record: Dict[str, Any], field: str) -> bool:
        """Check if a field is encrypted in the record"""
        return record.get(f"{field}_encrypted", False)


class FieldLevelEncryption:
    """Provides field-level encryption for specific data types"""
    
    def __init__(self, encryption_manager: EncryptionManager):
        self.encryption_manager = encryption_manager
    
    def encrypt_pii(self, pii_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Encrypt personally identifiable information
        
        Args:
            pii_data: Dictionary containing PII fields
            
        Returns:
            Dictionary with encrypted PII values
        """
        encrypted_pii = {}
        
        for field, value in pii_data.items():
            if value is not None:
                encrypted_pii[field] = self.encryption_manager.encrypt_string(str(value))
        
        return encrypted_pii
    
    def decrypt_pii(self, encrypted_pii: Dict[str, str]) -> Dict[str, str]:
        """
        Decrypt personally identifiable information
        
        Args:
            encrypted_pii: Dictionary with encrypted PII values
            
        Returns:
            Dictionary with decrypted PII values
        """
        decrypted_pii = {}
        
        for field, encrypted_value in encrypted_pii.items():
            if encrypted_value is not None:
                decrypted_pii[field] = self.encryption_manager.decrypt_string(encrypted_value)
        
        return decrypted_pii
    
    def encrypt_api_credentials(self, credentials: Dict[str, str]) -> Dict[str, str]:
        """
        Encrypt API credentials and tokens
        
        Args:
            credentials: Dictionary containing API credentials
            
        Returns:
            Dictionary with encrypted credentials
        """
        return self.encrypt_pii(credentials)
    
    def decrypt_api_credentials(self, encrypted_credentials: Dict[str, str]) -> Dict[str, str]:
        """
        Decrypt API credentials and tokens
        
        Args:
            encrypted_credentials: Dictionary with encrypted credentials
            
        Returns:
            Dictionary with decrypted credentials
        """
        return self.decrypt_pii(encrypted_credentials)