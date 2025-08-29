"""
TLS/SSL management for Project Dharma
Handles certificate generation, validation, and TLS configuration
"""

import os
import ssl
import socket
import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
import logging
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import aiohttp
import asyncio

logger = logging.getLogger(__name__)


class CertificateManager:
    """Manages SSL/TLS certificates for the platform"""
    
    def __init__(self, cert_dir: str = "/etc/dharma/certs"):
        """
        Initialize certificate manager
        
        Args:
            cert_dir: Directory to store certificates
        """
        self.cert_dir = Path(cert_dir)
        self.cert_dir.mkdir(parents=True, exist_ok=True)
        self.backend = default_backend()
    
    def generate_private_key(self, key_size: int = 2048) -> rsa.RSAPrivateKey:
        """
        Generate RSA private key
        
        Args:
            key_size: Key size in bits (default 2048)
            
        Returns:
            RSA private key
        """
        return rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=self.backend
        )
    
    def generate_self_signed_cert(self, 
                                 common_name: str,
                                 san_list: Optional[List[str]] = None,
                                 validity_days: int = 365) -> tuple[bytes, bytes]:
        """
        Generate self-signed certificate
        
        Args:
            common_name: Common name for certificate
            san_list: Subject Alternative Names
            validity_days: Certificate validity in days
            
        Returns:
            Tuple of (certificate_pem, private_key_pem)
        """
        # Generate private key
        private_key = self.generate_private_key()
        
        # Create certificate subject
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "IN"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Delhi"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "New Delhi"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Project Dharma"),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])
        
        # Create certificate
        cert_builder = x509.CertificateBuilder()
        cert_builder = cert_builder.subject_name(subject)
        cert_builder = cert_builder.issuer_name(issuer)
        cert_builder = cert_builder.public_key(private_key.public_key())
        cert_builder = cert_builder.serial_number(x509.random_serial_number())
        cert_builder = cert_builder.not_valid_before(datetime.datetime.utcnow())
        cert_builder = cert_builder.not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=validity_days)
        )
        
        # Add Subject Alternative Names if provided
        if san_list:
            san_names = [x509.DNSName(name) for name in san_list]
            cert_builder = cert_builder.add_extension(
                x509.SubjectAlternativeName(san_names),
                critical=False,
            )
        
        # Add basic constraints
        cert_builder = cert_builder.add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        
        # Add key usage
        cert_builder = cert_builder.add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                content_commitment=False,
                data_encipherment=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        
        # Sign certificate
        certificate = cert_builder.sign(private_key, hashes.SHA256(), self.backend)
        
        # Serialize to PEM format
        cert_pem = certificate.public_bytes(serialization.Encoding.PEM)
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        return cert_pem, key_pem
    
    def save_certificate(self, cert_name: str, cert_pem: bytes, key_pem: bytes):
        """
        Save certificate and private key to files
        
        Args:
            cert_name: Name for certificate files
            cert_pem: Certificate in PEM format
            key_pem: Private key in PEM format
        """
        cert_file = self.cert_dir / f"{cert_name}.crt"
        key_file = self.cert_dir / f"{cert_name}.key"
        
        # Save certificate
        with open(cert_file, 'wb') as f:
            f.write(cert_pem)
        
        # Save private key with restricted permissions
        with open(key_file, 'wb') as f:
            f.write(key_pem)
        os.chmod(key_file, 0o600)  # Read-only for owner
        
        logger.info(f"Certificate saved: {cert_file}")
        logger.info(f"Private key saved: {key_file}")
    
    def load_certificate(self, cert_name: str) -> tuple[str, str]:
        """
        Load certificate and private key from files
        
        Args:
            cert_name: Name of certificate files
            
        Returns:
            Tuple of (cert_path, key_path)
        """
        cert_file = self.cert_dir / f"{cert_name}.crt"
        key_file = self.cert_dir / f"{cert_name}.key"
        
        if not cert_file.exists() or not key_file.exists():
            raise FileNotFoundError(f"Certificate files not found for {cert_name}")
        
        return str(cert_file), str(key_file)
    
    def validate_certificate(self, cert_path: str) -> Dict[str, Any]:
        """
        Validate certificate and return information
        
        Args:
            cert_path: Path to certificate file
            
        Returns:
            Dictionary with certificate information
        """
        with open(cert_path, 'rb') as f:
            cert_data = f.read()
        
        certificate = x509.load_pem_x509_certificate(cert_data, self.backend)
        
        return {
            'subject': certificate.subject.rfc4514_string(),
            'issuer': certificate.issuer.rfc4514_string(),
            'serial_number': str(certificate.serial_number),
            'not_valid_before': certificate.not_valid_before,
            'not_valid_after': certificate.not_valid_after,
            'is_expired': certificate.not_valid_after < datetime.datetime.utcnow(),
            'days_until_expiry': (certificate.not_valid_after - datetime.datetime.utcnow()).days
        }


class TLSManager:
    """Manages TLS/SSL configuration for services"""
    
    def __init__(self, cert_manager: CertificateManager):
        """
        Initialize TLS manager
        
        Args:
            cert_manager: Certificate manager instance
        """
        self.cert_manager = cert_manager
        self.tls_configs = {}
    
    def create_ssl_context(self, 
                          cert_name: str,
                          server_side: bool = True,
                          verify_mode: ssl.VerifyMode = ssl.CERT_NONE) -> ssl.SSLContext:
        """
        Create SSL context for service
        
        Args:
            cert_name: Name of certificate to use
            server_side: Whether this is a server-side context
            verify_mode: Certificate verification mode
            
        Returns:
            Configured SSL context
        """
        try:
            cert_path, key_path = self.cert_manager.load_certificate(cert_name)
        except FileNotFoundError:
            # Generate self-signed certificate if not found
            logger.warning(f"Certificate {cert_name} not found, generating self-signed")
            cert_pem, key_pem = self.cert_manager.generate_self_signed_cert(cert_name)
            self.cert_manager.save_certificate(cert_name, cert_pem, key_pem)
            cert_path, key_path = self.cert_manager.load_certificate(cert_name)
        
        # Create SSL context using modern approach
        if server_side:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        else:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        
        context.verify_mode = verify_mode
        
        # Load certificate and key
        context.load_cert_chain(cert_path, key_path)
        
        # Set secure ciphers (use default secure ciphers if custom ones fail)
        try:
            context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
        except ssl.SSLError:
            # Fall back to default secure ciphers
            logger.warning("Custom cipher suite failed, using default secure ciphers")
        
        # Disable weak protocols (check if options exist)
        if hasattr(ssl, 'OP_NO_SSLv2'):
            context.options |= ssl.OP_NO_SSLv2
        if hasattr(ssl, 'OP_NO_SSLv3'):
            context.options |= ssl.OP_NO_SSLv3
        if hasattr(ssl, 'OP_NO_TLSv1'):
            context.options |= ssl.OP_NO_TLSv1
        if hasattr(ssl, 'OP_NO_TLSv1_1'):
            context.options |= ssl.OP_NO_TLSv1_1
        
        self.tls_configs[cert_name] = context
        return context
    
    def create_client_ssl_context(self, verify_ssl: bool = True) -> ssl.SSLContext:
        """
        Create SSL context for client connections
        
        Args:
            verify_ssl: Whether to verify server certificates
            
        Returns:
            Configured client SSL context
        """
        context = ssl.create_default_context()
        
        if not verify_ssl:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        
        return context
    
    async def verify_tls_connection(self, hostname: str, port: int, timeout: int = 10) -> Dict[str, Any]:
        """
        Verify TLS connection to a service
        
        Args:
            hostname: Target hostname
            port: Target port
            timeout: Connection timeout
            
        Returns:
            Dictionary with connection information
        """
        try:
            # Create SSL context for verification
            context = ssl.create_default_context()
            
            # Connect and get certificate info
            with socket.create_connection((hostname, port), timeout=timeout) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    cipher = ssock.cipher()
                    
                    return {
                        'success': True,
                        'certificate': cert,
                        'cipher': cipher,
                        'protocol': ssock.version(),
                        'hostname': hostname,
                        'port': port
                    }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'hostname': hostname,
                'port': port
            }
    
    def get_tls_config_for_service(self, service_name: str) -> Dict[str, Any]:
        """
        Get TLS configuration for a specific service
        
        Args:
            service_name: Name of the service
            
        Returns:
            TLS configuration dictionary
        """
        service_configs = {
            'api-gateway': {
                'cert_name': 'api-gateway',
                'port': 8443,
                'verify_client': False,
                'protocols': ['TLSv1.2', 'TLSv1.3']
            },
            'dashboard': {
                'cert_name': 'dashboard',
                'port': 8444,
                'verify_client': False,
                'protocols': ['TLSv1.2', 'TLSv1.3']
            },
            'mongodb': {
                'cert_name': 'mongodb',
                'port': 27017,
                'verify_client': True,
                'protocols': ['TLSv1.2', 'TLSv1.3']
            },
            'postgresql': {
                'cert_name': 'postgresql',
                'port': 5432,
                'verify_client': True,
                'protocols': ['TLSv1.2', 'TLSv1.3']
            },
            'elasticsearch': {
                'cert_name': 'elasticsearch',
                'port': 9200,
                'verify_client': False,
                'protocols': ['TLSv1.2', 'TLSv1.3']
            },
            'redis': {
                'cert_name': 'redis',
                'port': 6379,
                'verify_client': True,
                'protocols': ['TLSv1.2', 'TLSv1.3']
            }
        }
        
        return service_configs.get(service_name, {
            'cert_name': service_name,
            'port': 443,
            'verify_client': False,
            'protocols': ['TLSv1.2', 'TLSv1.3']
        })
    
    async def setup_service_tls(self, service_name: str) -> ssl.SSLContext:
        """
        Set up TLS for a specific service
        
        Args:
            service_name: Name of the service
            
        Returns:
            Configured SSL context for the service
        """
        config = self.get_tls_config_for_service(service_name)
        cert_name = config['cert_name']
        
        # Create SSL context
        verify_mode = ssl.CERT_REQUIRED if config.get('verify_client') else ssl.CERT_NONE
        context = self.create_ssl_context(cert_name, server_side=True, verify_mode=verify_mode)
        
        logger.info(f"TLS configured for service: {service_name}")
        return context


class NetworkSecurityManager:
    """Manages network security configurations"""
    
    def __init__(self, tls_manager: TLSManager):
        self.tls_manager = tls_manager
    
    async def create_secure_aiohttp_session(self, 
                                          verify_ssl: bool = True,
                                          timeout: int = 30) -> aiohttp.ClientSession:
        """
        Create secure aiohttp session with TLS
        
        Args:
            verify_ssl: Whether to verify SSL certificates
            timeout: Request timeout
            
        Returns:
            Configured aiohttp session
        """
        ssl_context = self.tls_manager.create_client_ssl_context(verify_ssl)
        
        timeout_config = aiohttp.ClientTimeout(total=timeout)
        
        session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=ssl_context),
            timeout=timeout_config
        )
        
        return session
    
    def get_secure_headers(self) -> Dict[str, str]:
        """
        Get security headers for HTTP responses
        
        Returns:
            Dictionary of security headers
        """
        return {
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }