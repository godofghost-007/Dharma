"""
API Key management and secure storage for Project Dharma
Handles API key generation, rotation, and secure storage
"""

import os
import secrets
import string
import hashlib
import hmac
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
from .encryption import EncryptionManager

logger = logging.getLogger(__name__)


class APIKeyManager:
    """Manages API keys with rotation and secure storage"""
    
    def __init__(self, encryption_manager: EncryptionManager, storage_path: str = "/etc/dharma/keys"):
        """
        Initialize API key manager
        
        Args:
            encryption_manager: Encryption manager for secure storage
            storage_path: Path to store encrypted key files
        """
        self.encryption_manager = encryption_manager
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.key_metadata = {}
        self._load_key_metadata()
    
    def generate_api_key(self, 
                        service_name: str,
                        key_type: str = "standard",
                        length: int = 32) -> str:
        """
        Generate a new API key
        
        Args:
            service_name: Name of the service
            key_type: Type of key (standard, admin, readonly)
            length: Length of the key
            
        Returns:
            Generated API key
        """
        # Generate random key
        alphabet = string.ascii_letters + string.digits
        api_key = ''.join(secrets.choice(alphabet) for _ in range(length))
        
        # Add prefix for identification
        prefix = f"dharma_{service_name}_{key_type}"
        full_key = f"{prefix}_{api_key}"
        
        # Store key metadata
        key_id = self._generate_key_id(full_key)
        self.key_metadata[key_id] = {
            'service_name': service_name,
            'key_type': key_type,
            'created_at': datetime.utcnow().isoformat(),
            'last_used': None,
            'usage_count': 0,
            'is_active': True,
            'expires_at': None
        }
        
        # Store encrypted key
        self._store_encrypted_key(key_id, full_key)
        self._save_key_metadata()
        
        logger.info(f"Generated API key for service: {service_name}, type: {key_type}")
        return full_key
    
    def generate_temporary_key(self, 
                             service_name: str,
                             expires_in_hours: int = 24,
                             length: int = 32) -> str:
        """
        Generate a temporary API key with expiration
        
        Args:
            service_name: Name of the service
            expires_in_hours: Hours until expiration
            length: Length of the key
            
        Returns:
            Generated temporary API key
        """
        api_key = self.generate_api_key(service_name, "temporary", length)
        key_id = self._generate_key_id(api_key)
        
        # Set expiration
        expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
        self.key_metadata[key_id]['expires_at'] = expires_at.isoformat()
        self._save_key_metadata()
        
        return api_key
    
    def validate_api_key(self, api_key: str) -> Dict[str, Any]:
        """
        Validate an API key and return metadata
        
        Args:
            api_key: API key to validate
            
        Returns:
            Dictionary with validation result and metadata
        """
        key_id = self._generate_key_id(api_key)
        
        if key_id not in self.key_metadata:
            return {'valid': False, 'reason': 'Key not found'}
        
        metadata = self.key_metadata[key_id]
        
        # Check if key is active
        if not metadata['is_active']:
            return {'valid': False, 'reason': 'Key is inactive'}
        
        # Check expiration
        if metadata['expires_at']:
            expires_at = datetime.fromisoformat(metadata['expires_at'])
            if datetime.utcnow() > expires_at:
                return {'valid': False, 'reason': 'Key has expired'}
        
        # Verify stored key matches
        try:
            stored_key = self._retrieve_encrypted_key(key_id)
            if not hmac.compare_digest(stored_key, api_key):
                return {'valid': False, 'reason': 'Key mismatch'}
        except Exception as e:
            logger.error(f"Error retrieving key {key_id}: {e}")
            return {'valid': False, 'reason': 'Key retrieval error'}
        
        # Update usage statistics
        metadata['last_used'] = datetime.utcnow().isoformat()
        metadata['usage_count'] += 1
        self._save_key_metadata()
        
        return {
            'valid': True,
            'service_name': metadata['service_name'],
            'key_type': metadata['key_type'],
            'created_at': metadata['created_at'],
            'usage_count': metadata['usage_count']
        }
    
    def rotate_api_key(self, old_key: str) -> str:
        """
        Rotate an API key (generate new, deactivate old)
        
        Args:
            old_key: Existing API key to rotate
            
        Returns:
            New API key
        """
        # Validate old key
        validation = self.validate_api_key(old_key)
        if not validation['valid']:
            raise ValueError(f"Cannot rotate invalid key: {validation['reason']}")
        
        # Generate new key with same service and type
        service_name = validation['service_name']
        key_type = validation['key_type']
        new_key = self.generate_api_key(service_name, key_type)
        
        # Deactivate old key
        old_key_id = self._generate_key_id(old_key)
        self.key_metadata[old_key_id]['is_active'] = False
        self.key_metadata[old_key_id]['rotated_at'] = datetime.utcnow().isoformat()
        self._save_key_metadata()
        
        logger.info(f"Rotated API key for service: {service_name}")
        return new_key
    
    def revoke_api_key(self, api_key: str) -> bool:
        """
        Revoke an API key
        
        Args:
            api_key: API key to revoke
            
        Returns:
            True if successfully revoked
        """
        key_id = self._generate_key_id(api_key)
        
        if key_id in self.key_metadata:
            self.key_metadata[key_id]['is_active'] = False
            self.key_metadata[key_id]['revoked_at'] = datetime.utcnow().isoformat()
            self._save_key_metadata()
            
            logger.info(f"Revoked API key: {key_id}")
            return True
        
        return False
    
    def list_api_keys(self, service_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List API keys with metadata
        
        Args:
            service_name: Filter by service name (optional)
            
        Returns:
            List of API key metadata
        """
        keys = []
        
        for key_id, metadata in self.key_metadata.items():
            if service_name and metadata['service_name'] != service_name:
                continue
            
            key_info = metadata.copy()
            key_info['key_id'] = key_id
            # Don't include the actual key in listings
            keys.append(key_info)
        
        return keys
    
    def cleanup_expired_keys(self) -> int:
        """
        Remove expired keys from storage
        
        Returns:
            Number of keys cleaned up
        """
        cleaned_count = 0
        current_time = datetime.utcnow()
        
        expired_keys = []
        for key_id, metadata in self.key_metadata.items():
            if metadata['expires_at']:
                expires_at = datetime.fromisoformat(metadata['expires_at'])
                if current_time > expires_at:
                    expired_keys.append(key_id)
        
        for key_id in expired_keys:
            self._remove_encrypted_key(key_id)
            del self.key_metadata[key_id]
            cleaned_count += 1
        
        if cleaned_count > 0:
            self._save_key_metadata()
            logger.info(f"Cleaned up {cleaned_count} expired keys")
        
        return cleaned_count
    
    def _generate_key_id(self, api_key: str) -> str:
        """Generate a unique ID for an API key"""
        return hashlib.sha256(api_key.encode()).hexdigest()[:16]
    
    def _store_encrypted_key(self, key_id: str, api_key: str):
        """Store encrypted API key to file"""
        encrypted_key = self.encryption_manager.encrypt_string(api_key)
        key_file = self.storage_path / f"{key_id}.key"
        
        with open(key_file, 'w') as f:
            f.write(encrypted_key)
        
        # Set restrictive permissions
        os.chmod(key_file, 0o600)
    
    def _retrieve_encrypted_key(self, key_id: str) -> str:
        """Retrieve and decrypt API key from file"""
        key_file = self.storage_path / f"{key_id}.key"
        
        if not key_file.exists():
            raise FileNotFoundError(f"Key file not found: {key_id}")
        
        with open(key_file, 'r') as f:
            encrypted_key = f.read()
        
        return self.encryption_manager.decrypt_string(encrypted_key)
    
    def _remove_encrypted_key(self, key_id: str):
        """Remove encrypted key file"""
        key_file = self.storage_path / f"{key_id}.key"
        if key_file.exists():
            key_file.unlink()
    
    def _load_key_metadata(self):
        """Load key metadata from file"""
        metadata_file = self.storage_path / "key_metadata.json"
        
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    encrypted_metadata = f.read()
                
                decrypted_data = self.encryption_manager.decrypt_string(encrypted_metadata)
                self.key_metadata = json.loads(decrypted_data)
            except Exception as e:
                logger.error(f"Error loading key metadata: {e}")
                self.key_metadata = {}
    
    def _save_key_metadata(self):
        """Save key metadata to encrypted file"""
        metadata_file = self.storage_path / "key_metadata.json"
        
        try:
            metadata_json = json.dumps(self.key_metadata, indent=2)
            encrypted_metadata = self.encryption_manager.encrypt_string(metadata_json)
            
            with open(metadata_file, 'w') as f:
                f.write(encrypted_metadata)
            
            # Set restrictive permissions
            os.chmod(metadata_file, 0o600)
        except Exception as e:
            logger.error(f"Error saving key metadata: {e}")


class SecureStorage:
    """Secure storage for sensitive configuration and credentials"""
    
    def __init__(self, encryption_manager: EncryptionManager, storage_path: str = "/etc/dharma/secure"):
        """
        Initialize secure storage
        
        Args:
            encryption_manager: Encryption manager for secure storage
            storage_path: Path to store encrypted files
        """
        self.encryption_manager = encryption_manager
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def store_credentials(self, service_name: str, credentials: Dict[str, Any]):
        """
        Store encrypted service credentials
        
        Args:
            service_name: Name of the service
            credentials: Dictionary of credentials to store
        """
        encrypted_creds = self.encryption_manager.encrypt_dict(credentials)
        creds_file = self.storage_path / f"{service_name}_credentials.enc"
        
        with open(creds_file, 'w') as f:
            f.write(encrypted_creds)
        
        # Set restrictive permissions
        os.chmod(creds_file, 0o600)
        
        logger.info(f"Stored encrypted credentials for service: {service_name}")
    
    def retrieve_credentials(self, service_name: str) -> Dict[str, Any]:
        """
        Retrieve and decrypt service credentials
        
        Args:
            service_name: Name of the service
            
        Returns:
            Decrypted credentials dictionary
        """
        creds_file = self.storage_path / f"{service_name}_credentials.enc"
        
        if not creds_file.exists():
            raise FileNotFoundError(f"Credentials not found for service: {service_name}")
        
        with open(creds_file, 'r') as f:
            encrypted_creds = f.read()
        
        return self.encryption_manager.decrypt_dict(encrypted_creds)
    
    def store_config(self, config_name: str, config_data: Dict[str, Any]):
        """
        Store encrypted configuration
        
        Args:
            config_name: Name of the configuration
            config_data: Configuration data to store
        """
        encrypted_config = self.encryption_manager.encrypt_dict(config_data)
        config_file = self.storage_path / f"{config_name}_config.enc"
        
        with open(config_file, 'w') as f:
            f.write(encrypted_config)
        
        # Set restrictive permissions
        os.chmod(config_file, 0o600)
        
        logger.info(f"Stored encrypted configuration: {config_name}")
    
    def retrieve_config(self, config_name: str) -> Dict[str, Any]:
        """
        Retrieve and decrypt configuration
        
        Args:
            config_name: Name of the configuration
            
        Returns:
            Decrypted configuration dictionary
        """
        config_file = self.storage_path / f"{config_name}_config.enc"
        
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration not found: {config_name}")
        
        with open(config_file, 'r') as f:
            encrypted_config = f.read()
        
        return self.encryption_manager.decrypt_dict(encrypted_config)
    
    def list_stored_items(self) -> Dict[str, List[str]]:
        """
        List all stored credentials and configurations
        
        Returns:
            Dictionary with lists of credentials and configurations
        """
        credentials = []
        configurations = []
        
        for file_path in self.storage_path.glob("*.enc"):
            filename = file_path.stem
            if filename.endswith("_credentials"):
                service_name = filename.replace("_credentials", "")
                credentials.append(service_name)
            elif filename.endswith("_config"):
                config_name = filename.replace("_config", "")
                configurations.append(config_name)
        
        return {
            'credentials': credentials,
            'configurations': configurations
        }
    
    def remove_credentials(self, service_name: str) -> bool:
        """
        Remove stored credentials for a service
        
        Args:
            service_name: Name of the service
            
        Returns:
            True if successfully removed
        """
        creds_file = self.storage_path / f"{service_name}_credentials.enc"
        
        if creds_file.exists():
            creds_file.unlink()
            logger.info(f"Removed credentials for service: {service_name}")
            return True
        
        return False
    
    def remove_config(self, config_name: str) -> bool:
        """
        Remove stored configuration
        
        Args:
            config_name: Name of the configuration
            
        Returns:
            True if successfully removed
        """
        config_file = self.storage_path / f"{config_name}_config.enc"
        
        if config_file.exists():
            config_file.unlink()
            logger.info(f"Removed configuration: {config_name}")
            return True
        
        return False