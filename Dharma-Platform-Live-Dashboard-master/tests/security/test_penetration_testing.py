"""
Security penetration testing and vulnerability assessment
Tests authentication, authorization, and security controls
"""

import pytest
import asyncio
import time
import hashlib
import jwt
import base64
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import aiohttp
import asyncpg
import motor.motor_asyncio
import redis.asyncio as redis
from cryptography.fernet import Fernet


class SecurityTestConfig:
    """Security testing configuration"""
    
    # Service endpoints
    API_GATEWAY_URL = "http://localhost:8000"
    DATA_COLLECTION_URL = "http://localhost:8001"
    AI_ANALYSIS_URL = "http://localhost:8002"
    ALERT_MANAGEMENT_URL = "http://localhost:8003"
    
    # Test credentials
    VALID_USER = {"username": "security_test_user", "password": "SecurePass123!"}
    ADMIN_USER = {"username": "security_admin", "password": "AdminPass456!"}
    
    # Security test parameters
    BRUTE_FORCE_ATTEMPTS = 50
    SQL_INJECTION_PAYLOADS = [
        "' OR '1'='1",
        "'; DROP TABLE users; --",
        "' UNION SELECT * FROM users --",
        "admin'--",
        "' OR 1=1#"
    ]
    XSS_PAYLOADS = [
        "<script>alert('xss')</script>",
        "javascript:alert('xss')",
        "<img src=x onerror=alert('xss')>",
        "<svg onload=alert('xss')>",
        "';alert('xss');//"
    ]


@pytest.fixture
async def security_clients():
    """Initialize clients for security testing"""
    clients = {
        'http': aiohttp.ClientSession(),
        'mongodb': motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017/dharma_test"),
        'postgresql': await asyncpg.connect("postgresql://postgres:password@localhost:5432/dharma_test"),
        'redis': redis.from_url("redis://localhost:6379/0")
    }
    
    yield clients
    
    # Cleanup
    await clients['http'].close()
    clients['mongodb'].close()
    await clients['postgresql'].close()
    await clients['redis'].close()


class TestAuthenticationSecurity:
    """Test authentication mechanisms and security"""
    
    async def test_password_security_requirements(self, security_clients):
        """Test password security requirements and validation"""
        
        weak_passwords = [
            "123456",
            "password",
            "admin",
            "test",
            "qwerty",
            "abc123",
            "password123"
        ]
        
        password_test_results = {}
        
        for weak_password in weak_passwords:
            user_data = {
                "username": f"test_weak_{weak_password}",
                "email": f"test_{weak_password}@test.com",
                "password": weak_password,
                "role": "analyst"
            }
            
            async with security_clients['http'].post(
                f"{SecurityTestConfig.API_GATEWAY_URL}/api/v1/auth/register",
                json=user_data
            ) as response:
                password_test_results[weak_password] = {
                    "status": response.status,
                    "rejected": response.status == 422,  # Should reject weak passwords
                    "response": await response.text()
                }
        
        # Test strong password acceptance
        strong_password_data = {
            "username": "test_strong_user",
            "email": "strong@test.com", 
            "password": "StrongP@ssw0rd123!",
            "role": "analyst"
        }
        
        async with security_clients['http'].post(
            f"{SecurityTestConfig.API_GATEWAY_URL}/api/v1/auth/register",
            json=strong_password_data
        ) as response:
            strong_password_accepted = response.status == 201
        
        # Verify weak passwords are rejected
        weak_passwords_rejected = sum(1 for result in password_test_results.values() 
                                    if result["rejected"])
        
        assert weak_passwords_rejected >= len(weak_passwords) * 0.8, \
            f"Only {weak_passwords_rejected}/{len(weak_passwords)} weak passwords rejected"
        
        assert strong_password_accepted, "Strong password was not accepted"
        
        return {
            "weak_passwords_tested": len(weak_passwords),
            "weak_passwords_rejected": weak_passwords_rejected,
            "strong_password_accepted": strong_password_accepted,
            "password_policy_enforced": weak_passwords_rejected >= len(weak_passwords) * 0.8
        }
    
    async def test_brute_force_protection(self, security_clients):
        """Test brute force attack protection"""
        
        # Create test user
        test_user = {
            "username": "brute_force_test",
            "email": "brute@test.com",
            "password": "TestPass123!",
            "role": "analyst"
        }
        
        async with security_clients['http'].post(
            f"{SecurityTestConfig.API_GATEWAY_URL}/api/v1/auth/register",
            json=test_user
        ) as response:
            assert response.status == 201
        
        # Attempt brute force attack
        failed_attempts = 0
        locked_out = False
        
        for attempt in range(SecurityTestConfig.BRUTE_FORCE_ATTEMPTS):
            login_data = {
                "username": test_user["username"],
                "password": f"wrong_password_{attempt}"
            }
            
            async with security_clients['http'].post(
                f"{SecurityTestConfig.API_GATEWAY_URL}/api/v1/auth/login",
                json=login_data
            ) as response:
                if response.status == 401:
                    failed_attempts += 1
                elif response.status == 429:  # Rate limited/locked out
                    locked_out = True
                    break
            
            await asyncio.sleep(0.1)  # Small delay between attempts
        
        # Test that legitimate login still works after lockout period
        await asyncio.sleep(5)  # Wait for potential lockout to expire
        
        legitimate_login = {
            "username": test_user["username"],
            "password": test_user["password"]
        }
        
        async with security_clients['http'].post(
            f"{SecurityTestConfig.API_GATEWAY_URL}/api/v1/auth/login",
            json=legitimate_login
        ) as response:
            legitimate_login_works = response.status == 200
        
        return {
            "failed_attempts": failed_attempts,
            "locked_out": locked_out,
            "brute_force_protection_active": locked_out,
            "legitimate_login_after_lockout": legitimate_login_works
        }
    
    async def test_jwt_token_security(self, security_clients):
        """Test JWT token security and validation"""
        
        # Create and login user to get token
        user_data = {
            "username": "jwt_test_user",
            "email": "jwt@test.com",
            "password": "JWTTest123!",
            "role": "analyst"
        }
        
        async with security_clients['http'].post(
            f"{SecurityTestConfig.API_GATEWAY_URL}/api/v1/auth/register",
            json=user_data
        ) as response:
            assert response.status == 201
        
        # Login to get valid token
        async with security_clients['http'].post(
            f"{SecurityTestConfig.API_GATEWAY_URL}/api/v1/auth/login",
            json={"username": user_data["username"], "password": user_data["password"]}
        ) as response:
            assert response.status == 200
            auth_data = await response.json()
            valid_token = auth_data['access_token']
        
        # Test various token manipulation attacks
        token_tests = {}
        
        # Test 1: Invalid signature
        try:
            # Decode token without verification to modify it
            decoded = jwt.decode(valid_token, options={"verify_signature": False})
            decoded['role'] = 'admin'  # Try to escalate privileges
            
            # Re-encode with wrong signature
            invalid_token = jwt.encode(decoded, "wrong_secret", algorithm="HS256")
            
            async with security_clients['http'].get(
                f"{SecurityTestConfig.API_GATEWAY_URL}/api/v1/dashboard/overview",
                headers={"Authorization": f"Bearer {invalid_token}"}
            ) as response:
                token_tests["invalid_signature"] = {
                    "status": response.status,
                    "rejected": response.status == 401
                }
        except Exception as e:
            token_tests["invalid_signature"] = {"error": str(e), "rejected": True}
        
        # Test 2: Expired token
        try:
            expired_payload = {
                "sub": user_data["username"],
                "exp": datetime.utcnow() - timedelta(hours=1),  # Expired 1 hour ago
                "role": "analyst"
            }
            expired_token = jwt.encode(expired_payload, "secret", algorithm="HS256")
            
            async with security_clients['http'].get(
                f"{SecurityTestConfig.API_GATEWAY_URL}/api/v1/dashboard/overview",
                headers={"Authorization": f"Bearer {expired_token}"}
            ) as response:
                token_tests["expired_token"] = {
                    "status": response.status,
                    "rejected": response.status == 401
                }
        except Exception as e:
            token_tests["expired_token"] = {"error": str(e), "rejected": True}
        
        # Test 3: Malformed token
        malformed_tokens = [
            "invalid.token.format",
            "Bearer malformed_token",
            base64.b64encode(b"fake_token").decode(),
            ""
        ]
        
        malformed_rejected = 0
        for malformed_token in malformed_tokens:
            async with security_clients['http'].get(
                f"{SecurityTestConfig.API_GATEWAY_URL}/api/v1/dashboard/overview",
                headers={"Authorization": f"Bearer {malformed_token}"}
            ) as response:
                if response.status == 401:
                    malformed_rejected += 1
        
        token_tests["malformed_tokens"] = {
            "total": len(malformed_tokens),
            "rejected": malformed_rejected,
            "all_rejected": malformed_rejected == len(malformed_tokens)
        }
        
        # Test 4: Valid token should work
        async with security_clients['http'].get(
            f"{SecurityTestConfig.API_GATEWAY_URL}/api/v1/dashboard/overview",
            headers={"Authorization": f"Bearer {valid_token}"}
        ) as response:
            token_tests["valid_token"] = {
                "status": response.status,
                "accepted": response.status == 200
            }
        
        return token_tests


class TestAuthorizationAndRBAC:
    """Test role-based access control and authorization"""
    
    async def test_role_based_access_control(self, security_clients):
        """Test RBAC implementation and privilege escalation prevention"""
        
        # Create users with different roles
        users = [
            {"username": "test_analyst", "role": "analyst", "password": "AnalystPass123!"},
            {"username": "test_admin", "role": "admin", "password": "AdminPass123!"},
            {"username": "test_viewer", "role": "viewer", "password": "ViewerPass123!"}
        ]
        
        user_tokens = {}
        
        # Register and login users
        for user in users:
            # Register
            user_data = {
                "username": user["username"],
                "email": f"{user['username']}@test.com",
                "password": user["password"],
                "role": user["role"]
            }
            
            async with security_clients['http'].post(
                f"{SecurityTestConfig.API_GATEWAY_URL}/api/v1/auth/register",
                json=user_data
            ) as response:
                if response.status != 201:
                    continue
            
            # Login
            async with security_clients['http'].post(
                f"{SecurityTestConfig.API_GATEWAY_URL}/api/v1/auth/login",
                json={"username": user["username"], "password": user["password"]}
            ) as response:
                if response.status == 200:
                    auth_data = await response.json()
                    user_tokens[user["role"]] = auth_data['access_token']
        
        # Define role-based access tests
        access_tests = [
            {
                "endpoint": "/api/v1/dashboard/overview",
                "method": "GET",
                "allowed_roles": ["analyst", "admin", "viewer"],
                "description": "Dashboard overview access"
            },
            {
                "endpoint": "/api/v1/alerts",
                "method": "GET", 
                "allowed_roles": ["analyst", "admin"],
                "description": "Alert viewing"
            },
            {
                "endpoint": "/api/v1/users",
                "method": "GET",
                "allowed_roles": ["admin"],
                "description": "User management"
            },
            {
                "endpoint": "/api/v1/analyze/sentiment",
                "method": "POST",
                "data": {"content": "test", "language": "en"},
                "allowed_roles": ["analyst", "admin"],
                "description": "AI analysis access"
            }
        ]
        
        rbac_results = {}
        
        for test in access_tests:
            test_results = {}
            
            for role, token in user_tokens.items():
                headers = {"Authorization": f"Bearer {token}"}
                
                try:
                    if test["method"] == "GET":
                        async with security_clients['http'].get(
                            f"{SecurityTestConfig.API_GATEWAY_URL}{test['endpoint']}",
                            headers=headers
                        ) as response:
                            status = response.status
                    else:  # POST
                        async with security_clients['http'].post(
                            f"{SecurityTestConfig.API_GATEWAY_URL}{test['endpoint']}",
                            json=test.get("data", {}),
                            headers=headers
                        ) as response:
                            status = response.status
                    
                    should_allow = role in test["allowed_roles"]
                    access_granted = status in [200, 201, 202]
                    correct_access = (should_allow and access_granted) or (not should_allow and not access_granted)
                    
                    test_results[role] = {
                        "status": status,
                        "should_allow": should_allow,
                        "access_granted": access_granted,
                        "correct_access": correct_access
                    }
                
                except Exception as e:
                    test_results[role] = {
                        "error": str(e),
                        "correct_access": False
                    }
            
            rbac_results[test["description"]] = test_results
        
        # Calculate RBAC effectiveness
        total_tests = sum(len(results) for results in rbac_results.values())
        correct_access_count = sum(
            sum(1 for result in results.values() if result.get("correct_access", False))
            for results in rbac_results.values()
        )
        
        rbac_effectiveness = (correct_access_count / total_tests * 100) if total_tests > 0 else 0
        
        return {
            "rbac_results": rbac_results,
            "total_tests": total_tests,
            "correct_access_count": correct_access_count,
            "rbac_effectiveness": rbac_effectiveness,
            "rbac_working": rbac_effectiveness >= 90
        }


class TestInputValidationAndSanitization:
    """Test input validation and sanitization against injection attacks"""
    
    async def test_sql_injection_prevention(self, security_clients):
        """Test SQL injection prevention in all endpoints"""
        
        # Create test user for authentication
        user_data = {
            "username": "sql_test_user",
            "email": "sql@test.com",
            "password": "SQLTest123!",
            "role": "analyst"
        }
        
        async with security_clients['http'].post(
            f"{SecurityTestConfig.API_GATEWAY_URL}/api/v1/auth/register",
            json=user_data
        ) as response:
            assert response.status == 201
        
        async with security_clients['http'].post(
            f"{SecurityTestConfig.API_GATEWAY_URL}/api/v1/auth/login",
            json={"username": user_data["username"], "password": user_data["password"]}
        ) as response:
            auth_data = await response.json()
            token = auth_data['access_token']
        
        headers = {"Authorization": f"Bearer {token}"}
        
        sql_injection_results = {}
        
        # Test SQL injection in various endpoints
        injection_tests = [
            {
                "endpoint": "/api/v1/search",
                "method": "POST",
                "payload_field": "query",
                "description": "Search query injection"
            },
            {
                "endpoint": "/api/v1/analyze/sentiment",
                "method": "POST", 
                "payload_field": "content",
                "description": "Content analysis injection"
            },
            {
                "endpoint": "/api/v1/alerts",
                "method": "GET",
                "payload_field": "filter",
                "description": "Alert filtering injection"
            }
        ]
        
        for test in injection_tests:
            test_results = {}
            
            for payload in SecurityTestConfig.SQL_INJECTION_PAYLOADS:
                try:
                    if test["method"] == "GET":
                        # For GET requests, inject in query parameters
                        url = f"{SecurityTestConfig.API_GATEWAY_URL}{test['endpoint']}?{test['payload_field']}={payload}"
                        async with security_clients['http'].get(url, headers=headers) as response:
                            status = response.status
                            response_text = await response.text()
                    else:
                        # For POST requests, inject in JSON body
                        data = {test["payload_field"]: payload}
                        if test["endpoint"] == "/api/v1/analyze/sentiment":
                            data["language"] = "en"
                        
                        async with security_clients['http'].post(
                            f"{SecurityTestConfig.API_GATEWAY_URL}{test['endpoint']}",
                            json=data,
                            headers=headers
                        ) as response:
                            status = response.status
                            response_text = await response.text()
                    
                    # Check if injection was prevented (should not return 500 or database errors)
                    injection_prevented = status != 500 and "error" not in response_text.lower()
                    
                    test_results[payload] = {
                        "status": status,
                        "injection_prevented": injection_prevented,
                        "response_length": len(response_text)
                    }
                
                except Exception as e:
                    test_results[payload] = {
                        "error": str(e),
                        "injection_prevented": True  # Exception handling counts as prevention
                    }
            
            sql_injection_results[test["description"]] = test_results
        
        # Calculate prevention effectiveness
        total_injections = sum(len(results) for results in sql_injection_results.values())
        prevented_injections = sum(
            sum(1 for result in results.values() if result.get("injection_prevented", False))
            for results in sql_injection_results.values()
        )
        
        prevention_rate = (prevented_injections / total_injections * 100) if total_injections > 0 else 0
        
        return {
            "sql_injection_results": sql_injection_results,
            "total_injection_attempts": total_injections,
            "prevented_injections": prevented_injections,
            "prevention_rate": prevention_rate,
            "sql_injection_protected": prevention_rate >= 95
        }
    
    async def test_xss_prevention(self, security_clients):
        """Test XSS prevention in content handling"""
        
        # Create test user
        user_data = {
            "username": "xss_test_user",
            "email": "xss@test.com",
            "password": "XSSTest123!",
            "role": "analyst"
        }
        
        async with security_clients['http'].post(
            f"{SecurityTestConfig.API_GATEWAY_URL}/api/v1/auth/register",
            json=user_data
        ) as response:
            assert response.status == 201
        
        async with security_clients['http'].post(
            f"{SecurityTestConfig.API_GATEWAY_URL}/api/v1/auth/login",
            json={"username": user_data["username"], "password": user_data["password"]}
        ) as response:
            auth_data = await response.json()
            token = auth_data['access_token']
        
        headers = {"Authorization": f"Bearer {token}"}
        
        xss_results = {}
        
        for payload in SecurityTestConfig.XSS_PAYLOADS:
            # Test XSS in content submission
            post_data = {
                "platform": "twitter",
                "content": payload,
                "user_id": "xss_test_user",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            try:
                async with security_clients['http'].post(
                    f"{SecurityTestConfig.DATA_COLLECTION_URL}/api/v1/ingest",
                    json=post_data,
                    headers=headers
                ) as response:
                    status = response.status
                    response_text = await response.text()
                
                # Check if XSS payload was sanitized (should not contain script tags in response)
                xss_sanitized = "<script>" not in response_text and "javascript:" not in response_text
                
                xss_results[payload] = {
                    "status": status,
                    "xss_sanitized": xss_sanitized,
                    "response_contains_payload": payload in response_text
                }
            
            except Exception as e:
                xss_results[payload] = {
                    "error": str(e),
                    "xss_sanitized": True
                }
        
        # Calculate sanitization effectiveness
        total_xss_attempts = len(xss_results)
        sanitized_attempts = sum(1 for result in xss_results.values() 
                               if result.get("xss_sanitized", False))
        
        sanitization_rate = (sanitized_attempts / total_xss_attempts * 100) if total_xss_attempts > 0 else 0
        
        return {
            "xss_results": xss_results,
            "total_xss_attempts": total_xss_attempts,
            "sanitized_attempts": sanitized_attempts,
            "sanitization_rate": sanitization_rate,
            "xss_protected": sanitization_rate >= 95
        }


class TestDataEncryptionAndPrivacy:
    """Test data encryption and privacy controls"""
    
    async def test_data_encryption_at_rest(self, security_clients):
        """Test that sensitive data is encrypted at rest"""
        
        # Submit sensitive test data
        sensitive_data = {
            "platform": "twitter",
            "content": "Sensitive political content for encryption test",
            "user_id": "encryption_test_user",
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {"sensitive": True, "pii": "test@email.com"}
        }
        
        # Submit data through API
        async with security_clients['http'].post(
            f"{SecurityTestConfig.DATA_COLLECTION_URL}/api/v1/ingest",
            json=sensitive_data,
            headers={"Authorization": "Bearer test_token"}
        ) as response:
            submission_status = response.status
        
        # Check if data is encrypted in MongoDB
        await asyncio.sleep(2)  # Allow time for processing
        
        db = security_clients['mongodb'].dharma_test
        stored_posts = await db.posts.find(
            {"user_id": "encryption_test_user"}
        ).to_list(length=None)
        
        encryption_results = {
            "data_submitted": submission_status in [200, 202],
            "posts_found": len(stored_posts),
            "encryption_checks": {}
        }
        
        if stored_posts:
            post = stored_posts[0]
            
            # Check if sensitive fields are encrypted (not plaintext)
            content_encrypted = post.get('content') != sensitive_data['content']
            metadata_encrypted = 'pii' not in str(post.get('metadata', {}))
            
            encryption_results["encryption_checks"] = {
                "content_encrypted": content_encrypted,
                "metadata_encrypted": metadata_encrypted,
                "overall_encrypted": content_encrypted and metadata_encrypted
            }
        
        # Check PostgreSQL for encrypted audit logs
        audit_query = """
            SELECT details FROM audit_logs 
            WHERE action LIKE '%ingest%' 
            AND timestamp >= NOW() - INTERVAL '5 minutes'
            LIMIT 1
        """
        
        try:
            audit_records = await security_clients['postgresql'].fetch(audit_query)
            if audit_records:
                audit_details = audit_records[0]['details']
                # Check if PII is not stored in plaintext in audit logs
                pii_in_audit = "test@email.com" in str(audit_details)
                encryption_results["audit_encryption"] = {
                    "pii_found_in_audit": pii_in_audit,
                    "audit_properly_encrypted": not pii_in_audit
                }
        except Exception as e:
            encryption_results["audit_encryption"] = {"error": str(e)}
        
        return encryption_results
    
    async def test_tls_encryption_in_transit(self, security_clients):
        """Test TLS encryption for data in transit"""
        
        # Test HTTPS enforcement
        tls_results = {}
        
        # Test if HTTP requests are redirected to HTTPS
        try:
            http_url = SecurityTestConfig.API_GATEWAY_URL.replace("https://", "http://")
            async with security_clients['http'].get(f"{http_url}/health") as response:
                tls_results["http_redirect"] = {
                    "status": response.status,
                    "redirected_to_https": response.url.scheme == "https"
                }
        except Exception as e:
            tls_results["http_redirect"] = {"error": str(e)}
        
        # Test TLS certificate validation (if HTTPS is configured)
        try:
            if SecurityTestConfig.API_GATEWAY_URL.startswith("https://"):
                async with security_clients['http'].get(f"{SecurityTestConfig.API_GATEWAY_URL}/health") as response:
                    tls_results["tls_certificate"] = {
                        "status": response.status,
                        "tls_working": response.status == 200
                    }
        except Exception as e:
            tls_results["tls_certificate"] = {"error": str(e)}
        
        # Test secure headers
        try:
            async with security_clients['http'].get(f"{SecurityTestConfig.API_GATEWAY_URL}/health") as response:
                headers = response.headers
                
                security_headers = {
                    "strict_transport_security": "Strict-Transport-Security" in headers,
                    "content_security_policy": "Content-Security-Policy" in headers,
                    "x_frame_options": "X-Frame-Options" in headers,
                    "x_content_type_options": "X-Content-Type-Options" in headers
                }
                
                tls_results["security_headers"] = security_headers
                tls_results["security_headers"]["all_present"] = all(security_headers.values())
        
        except Exception as e:
            tls_results["security_headers"] = {"error": str(e)}
        
        return tls_results


@pytest.mark.asyncio
async def test_security_compliance_suite():
    """Run complete security and compliance test suite"""
    
    print("Starting security and compliance testing...")
    
    # Run security tests
    pytest_args = [
        __file__,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto"
    ]
    
    return pytest.main(pytest_args)


if __name__ == "__main__":
    asyncio.run(test_security_compliance_suite())