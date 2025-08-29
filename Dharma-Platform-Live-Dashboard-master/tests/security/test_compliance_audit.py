"""
Compliance audit and documentation review tests
Tests compliance with security standards and regulations
"""

import pytest
import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
import aiohttp
import asyncpg
import motor.motor_asyncio


class ComplianceTestConfig:
    """Compliance testing configuration"""
    
    # Compliance standards to check
    STANDARDS = {
        "GDPR": "General Data Protection Regulation",
        "SOC2": "Service Organization Control 2",
        "ISO27001": "Information Security Management",
        "NIST": "National Institute of Standards and Technology"
    }
    
    # Required security controls
    REQUIRED_CONTROLS = [
        "access_control",
        "audit_logging", 
        "data_encryption",
        "incident_response",
        "vulnerability_management",
        "backup_recovery",
        "network_security",
        "authentication"
    ]


@pytest.fixture
async def compliance_clients():
    """Initialize clients for compliance testing"""
    clients = {
        'http': aiohttp.ClientSession(),
        'mongodb': motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017/dharma_test"),
        'postgresql': await asyncpg.connect("postgresql://postgres:password@localhost:5432/dharma_test")
    }
    
    yield clients
    
    # Cleanup
    await clients['http'].close()
    clients['mongodb'].close()
    await clients['postgresql'].close()


class TestDataProtectionCompliance:
    """Test data protection and privacy compliance (GDPR-like requirements)"""
    
    async def test_data_retention_policies(self, compliance_clients):
        """Test data retention and deletion policies"""
        
        # Test data retention configuration
        retention_results = {}
        
        # Check if retention policies are configured in database
        try:
            # Check MongoDB for retention policies
            db = compliance_clients['mongodb'].dharma_test
            
            # Look for TTL indexes (automatic expiration)
            collections = await db.list_collection_names()
            ttl_indexes = {}
            
            for collection_name in collections:
                collection = db[collection_name]
                indexes = await collection.list_indexes().to_list(length=None)
                
                for index in indexes:
                    if 'expireAfterSeconds' in index:
                        ttl_indexes[collection_name] = index['expireAfterSeconds']
            
            retention_results["mongodb_ttl"] = {
                "collections_with_ttl": len(ttl_indexes),
                "ttl_policies": ttl_indexes,
                "retention_configured": len(ttl_indexes) > 0
            }
        
        except Exception as e:
            retention_results["mongodb_ttl"] = {"error": str(e)}
        
        # Check PostgreSQL for retention policies
        try:
            retention_query = """
                SELECT schemaname, tablename, 
                       obj_description(c.oid) as table_comment
                FROM pg_tables pt
                JOIN pg_class c ON c.relname = pt.tablename
                WHERE schemaname = 'public'
                AND obj_description(c.oid) LIKE '%retention%'
            """
            
            retention_tables = await compliance_clients['postgresql'].fetch(retention_query)
            
            retention_results["postgresql_retention"] = {
                "tables_with_retention": len(retention_tables),
                "retention_configured": len(retention_tables) > 0
            }
        
        except Exception as e:
            retention_results["postgresql_retention"] = {"error": str(e)}
        
        # Test data anonymization capabilities
        try:
            # Check if anonymization functions exist
            anonymization_query = """
                SELECT routine_name, routine_type
                FROM information_schema.routines
                WHERE routine_schema = 'public'
                AND routine_name LIKE '%anonymize%' OR routine_name LIKE '%mask%'
            """
            
            anonymization_functions = await compliance_clients['postgresql'].fetch(anonymization_query)
            
            retention_results["anonymization"] = {
                "anonymization_functions": len(anonymization_functions),
                "anonymization_available": len(anonymization_functions) > 0
            }
        
        except Exception as e:
            retention_results["anonymization"] = {"error": str(e)}
        
        return retention_results
    
    async def test_data_subject_rights(self, compliance_clients):
        """Test data subject rights implementation (GDPR Article 15-22)"""
        
        rights_results = {}
        
        # Test right to access (Article 15)
        try:
            async with compliance_clients['http'].get(
                "http://localhost:8000/api/v1/data-subject/access",
                headers={"Authorization": "Bearer test_token"}
            ) as response:
                rights_results["right_to_access"] = {
                    "endpoint_exists": response.status != 404,
                    "status": response.status,
                    "implemented": response.status in [200, 401, 403]  # Exists but may require auth
                }
        except Exception as e:
            rights_results["right_to_access"] = {"error": str(e), "implemented": False}
        
        # Test right to rectification (Article 16)
        try:
            async with compliance_clients['http'].put(
                "http://localhost:8000/api/v1/data-subject/rectify",
                json={"corrections": {}},
                headers={"Authorization": "Bearer test_token"}
            ) as response:
                rights_results["right_to_rectification"] = {
                    "endpoint_exists": response.status != 404,
                    "status": response.status,
                    "implemented": response.status in [200, 401, 403, 422]
                }
        except Exception as e:
            rights_results["right_to_rectification"] = {"error": str(e), "implemented": False}
        
        # Test right to erasure (Article 17)
        try:
            async with compliance_clients['http'].delete(
                "http://localhost:8000/api/v1/data-subject/erase",
                headers={"Authorization": "Bearer test_token"}
            ) as response:
                rights_results["right_to_erasure"] = {
                    "endpoint_exists": response.status != 404,
                    "status": response.status,
                    "implemented": response.status in [200, 401, 403]
                }
        except Exception as e:
            rights_results["right_to_erasure"] = {"error": str(e), "implemented": False}
        
        # Test right to data portability (Article 20)
        try:
            async with compliance_clients['http'].get(
                "http://localhost:8000/api/v1/data-subject/export",
                headers={"Authorization": "Bearer test_token"}
            ) as response:
                rights_results["right_to_portability"] = {
                    "endpoint_exists": response.status != 404,
                    "status": response.status,
                    "implemented": response.status in [200, 401, 403]
                }
        except Exception as e:
            rights_results["right_to_portability"] = {"error": str(e), "implemented": False}
        
        # Calculate compliance score
        total_rights = len(rights_results)
        implemented_rights = sum(1 for result in rights_results.values() 
                               if result.get("implemented", False))
        
        compliance_score = (implemented_rights / total_rights * 100) if total_rights > 0 else 0
        
        return {
            "rights_results": rights_results,
            "total_rights": total_rights,
            "implemented_rights": implemented_rights,
            "compliance_score": compliance_score,
            "gdpr_compliant": compliance_score >= 75
        }
    
    async def test_consent_management(self, compliance_clients):
        """Test consent management implementation"""
        
        consent_results = {}
        
        # Test consent recording
        try:
            consent_data = {
                "user_id": "test_user_consent",
                "consent_type": "data_processing",
                "granted": True,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            async with compliance_clients['http'].post(
                "http://localhost:8000/api/v1/consent/record",
                json=consent_data,
                headers={"Authorization": "Bearer test_token"}
            ) as response:
                consent_results["consent_recording"] = {
                    "endpoint_exists": response.status != 404,
                    "status": response.status,
                    "implemented": response.status in [200, 201, 401, 403]
                }
        except Exception as e:
            consent_results["consent_recording"] = {"error": str(e), "implemented": False}
        
        # Test consent withdrawal
        try:
            async with compliance_clients['http'].post(
                "http://localhost:8000/api/v1/consent/withdraw",
                json={"user_id": "test_user_consent", "consent_type": "data_processing"},
                headers={"Authorization": "Bearer test_token"}
            ) as response:
                consent_results["consent_withdrawal"] = {
                    "endpoint_exists": response.status != 404,
                    "status": response.status,
                    "implemented": response.status in [200, 401, 403]
                }
        except Exception as e:
            consent_results["consent_withdrawal"] = {"error": str(e), "implemented": False}
        
        # Check consent audit trail in database
        try:
            consent_audit_query = """
                SELECT COUNT(*) as consent_records
                FROM audit_logs
                WHERE action LIKE '%consent%'
                AND timestamp >= NOW() - INTERVAL '24 hours'
            """
            
            consent_records = await compliance_clients['postgresql'].fetchval(consent_audit_query)
            
            consent_results["consent_audit_trail"] = {
                "records_found": consent_records > 0,
                "record_count": consent_records,
                "audit_implemented": consent_records is not None
            }
        
        except Exception as e:
            consent_results["consent_audit_trail"] = {"error": str(e), "audit_implemented": False}
        
        return consent_results


class TestAuditAndLoggingCompliance:
    """Test audit logging and monitoring compliance"""
    
    async def test_comprehensive_audit_logging(self, compliance_clients):
        """Test comprehensive audit logging implementation"""
        
        audit_results = {}
        
        # Check audit log structure and completeness
        try:
            audit_structure_query = """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'audit_logs'
                ORDER BY ordinal_position
            """
            
            audit_columns = await compliance_clients['postgresql'].fetch(audit_structure_query)
            
            required_fields = [
                'user_id', 'action', 'resource_type', 'resource_id', 
                'timestamp', 'ip_address', 'user_agent', 'details'
            ]
            
            existing_fields = [col['column_name'] for col in audit_columns]
            missing_fields = [field for field in required_fields if field not in existing_fields]
            
            audit_results["audit_structure"] = {
                "total_columns": len(audit_columns),
                "required_fields": required_fields,
                "existing_fields": existing_fields,
                "missing_fields": missing_fields,
                "structure_complete": len(missing_fields) == 0
            }
        
        except Exception as e:
            audit_results["audit_structure"] = {"error": str(e)}
        
        # Test audit log retention
        try:
            retention_query = """
                SELECT 
                    MIN(timestamp) as oldest_log,
                    MAX(timestamp) as newest_log,
                    COUNT(*) as total_logs,
                    COUNT(CASE WHEN timestamp >= NOW() - INTERVAL '90 days' THEN 1 END) as recent_logs
                FROM audit_logs
            """
            
            retention_stats = await compliance_clients['postgresql'].fetchrow(retention_query)
            
            audit_results["audit_retention"] = {
                "oldest_log": retention_stats['oldest_log'].isoformat() if retention_stats['oldest_log'] else None,
                "newest_log": retention_stats['newest_log'].isoformat() if retention_stats['newest_log'] else None,
                "total_logs": retention_stats['total_logs'],
                "recent_logs": retention_stats['recent_logs'],
                "retention_working": retention_stats['total_logs'] > 0
            }
        
        except Exception as e:
            audit_results["audit_retention"] = {"error": str(e)}
        
        # Test audit log integrity
        try:
            integrity_query = """
                SELECT 
                    COUNT(*) as total_logs,
                    COUNT(CASE WHEN user_id IS NOT NULL THEN 1 END) as logs_with_user,
                    COUNT(CASE WHEN action IS NOT NULL THEN 1 END) as logs_with_action,
                    COUNT(CASE WHEN timestamp IS NOT NULL THEN 1 END) as logs_with_timestamp
                FROM audit_logs
                WHERE timestamp >= NOW() - INTERVAL '24 hours'
            """
            
            integrity_stats = await compliance_clients['postgresql'].fetchrow(integrity_query)
            
            if integrity_stats['total_logs'] > 0:
                completeness_score = (
                    (integrity_stats['logs_with_user'] + 
                     integrity_stats['logs_with_action'] + 
                     integrity_stats['logs_with_timestamp']) / 
                    (integrity_stats['total_logs'] * 3) * 100
                )
            else:
                completeness_score = 0
            
            audit_results["audit_integrity"] = {
                "total_logs": integrity_stats['total_logs'],
                "completeness_score": completeness_score,
                "integrity_maintained": completeness_score >= 95
            }
        
        except Exception as e:
            audit_results["audit_integrity"] = {"error": str(e)}
        
        return audit_results
    
    async def test_security_monitoring_compliance(self, compliance_clients):
        """Test security monitoring and alerting compliance"""
        
        monitoring_results = {}
        
        # Test security event detection
        security_events = [
            "failed_login_attempt",
            "privilege_escalation",
            "unauthorized_access",
            "data_breach_attempt",
            "suspicious_activity"
        ]
        
        for event_type in security_events:
            try:
                event_query = """
                    SELECT COUNT(*) as event_count
                    FROM audit_logs
                    WHERE action LIKE %s
                    AND timestamp >= NOW() - INTERVAL '30 days'
                """
                
                event_count = await compliance_clients['postgresql'].fetchval(
                    event_query, f"%{event_type}%"
                )
                
                monitoring_results[event_type] = {
                    "events_logged": event_count > 0,
                    "event_count": event_count,
                    "monitoring_active": event_count is not None
                }
            
            except Exception as e:
                monitoring_results[event_type] = {"error": str(e)}
        
        # Test alert generation for security events
        try:
            security_alerts_query = """
                SELECT COUNT(*) as security_alerts
                FROM alerts
                WHERE type LIKE '%security%' OR type LIKE '%breach%'
                AND created_at >= NOW() - INTERVAL '30 days'
            """
            
            security_alerts = await compliance_clients['postgresql'].fetchval(security_alerts_query)
            
            monitoring_results["security_alerting"] = {
                "alerts_generated": security_alerts > 0,
                "alert_count": security_alerts,
                "alerting_active": security_alerts is not None
            }
        
        except Exception as e:
            monitoring_results["security_alerting"] = {"error": str(e)}
        
        return monitoring_results


class TestAccessControlCompliance:
    """Test access control and authorization compliance"""
    
    async def test_role_based_access_compliance(self, compliance_clients):
        """Test RBAC compliance with security standards"""
        
        rbac_results = {}
        
        # Test role definition and management
        try:
            roles_query = """
                SELECT role, COUNT(*) as user_count
                FROM users
                GROUP BY role
                ORDER BY user_count DESC
            """
            
            roles = await compliance_clients['postgresql'].fetch(roles_query)
            
            # Check for proper role separation
            expected_roles = ['admin', 'analyst', 'viewer', 'auditor']
            existing_roles = [role['role'] for role in roles]
            
            rbac_results["role_management"] = {
                "total_roles": len(roles),
                "existing_roles": existing_roles,
                "expected_roles": expected_roles,
                "proper_separation": len(set(existing_roles) & set(expected_roles)) >= 3
            }
        
        except Exception as e:
            rbac_results["role_management"] = {"error": str(e)}
        
        # Test privilege escalation prevention
        try:
            # Check for users with multiple high-privilege roles
            privilege_query = """
                SELECT user_id, COUNT(DISTINCT role) as role_count
                FROM (
                    SELECT id as user_id, role FROM users
                    WHERE role IN ('admin', 'root', 'superuser')
                ) privileged_users
                GROUP BY user_id
                HAVING COUNT(DISTINCT role) > 1
            """
            
            multi_role_users = await compliance_clients['postgresql'].fetch(privilege_query)
            
            rbac_results["privilege_escalation"] = {
                "multi_role_users": len(multi_role_users),
                "escalation_prevented": len(multi_role_users) == 0
            }
        
        except Exception as e:
            rbac_results["privilege_escalation"] = {"error": str(e)}
        
        # Test access control audit trail
        try:
            access_audit_query = """
                SELECT COUNT(*) as access_events
                FROM audit_logs
                WHERE action IN ('login', 'logout', 'access_granted', 'access_denied')
                AND timestamp >= NOW() - INTERVAL '24 hours'
            """
            
            access_events = await compliance_clients['postgresql'].fetchval(access_audit_query)
            
            rbac_results["access_audit"] = {
                "access_events_logged": access_events > 0,
                "event_count": access_events,
                "audit_comprehensive": access_events > 10  # Reasonable activity threshold
            }
        
        except Exception as e:
            rbac_results["access_audit"] = {"error": str(e)}
        
        return rbac_results


class TestDocumentationCompliance:
    """Test documentation and policy compliance"""
    
    async def test_security_documentation_completeness(self, compliance_clients):
        """Test completeness of security documentation"""
        
        doc_results = {}
        
        # Check for required documentation files
        required_docs = [
            "docs/security/security-policy.md",
            "docs/security/incident-response-plan.md", 
            "docs/security/data-protection-policy.md",
            "docs/security/access-control-policy.md",
            "docs/operations/backup-recovery-procedures.md",
            "docs/operations/disaster-recovery-plan.md",
            "docs/compliance/audit-procedures.md",
            "docs/compliance/privacy-policy.md"
        ]
        
        project_root = Path("project-dharma")
        
        for doc_path in required_docs:
            full_path = project_root / doc_path
            doc_exists = full_path.exists()
            
            if doc_exists:
                # Check if document has content
                try:
                    content = full_path.read_text()
                    has_content = len(content.strip()) > 100  # Minimum content threshold
                    
                    doc_results[doc_path] = {
                        "exists": True,
                        "has_content": has_content,
                        "content_length": len(content),
                        "compliant": has_content
                    }
                except Exception as e:
                    doc_results[doc_path] = {
                        "exists": True,
                        "error": str(e),
                        "compliant": False
                    }
            else:
                doc_results[doc_path] = {
                    "exists": False,
                    "compliant": False
                }
        
        # Calculate documentation completeness
        total_docs = len(required_docs)
        compliant_docs = sum(1 for result in doc_results.values() 
                           if result.get("compliant", False))
        
        completeness_score = (compliant_docs / total_docs * 100) if total_docs > 0 else 0
        
        return {
            "documentation_results": doc_results,
            "total_required_docs": total_docs,
            "compliant_docs": compliant_docs,
            "completeness_score": completeness_score,
            "documentation_compliant": completeness_score >= 80
        }
    
    async def test_policy_implementation_compliance(self, compliance_clients):
        """Test that documented policies are actually implemented"""
        
        policy_results = {}
        
        # Test password policy implementation
        try:
            # Check if password policy is enforced in code
            weak_password_test = {
                "username": "policy_test_user",
                "email": "policy@test.com",
                "password": "123456",  # Weak password
                "role": "analyst"
            }
            
            async with compliance_clients['http'].post(
                "http://localhost:8000/api/v1/auth/register",
                json=weak_password_test
            ) as response:
                policy_results["password_policy"] = {
                    "weak_password_rejected": response.status == 422,
                    "policy_enforced": response.status == 422
                }
        
        except Exception as e:
            policy_results["password_policy"] = {"error": str(e)}
        
        # Test data retention policy implementation
        try:
            # Check if old data is actually being deleted
            old_data_query = """
                SELECT COUNT(*) as old_records
                FROM audit_logs
                WHERE timestamp < NOW() - INTERVAL '2 years'
            """
            
            old_records = await compliance_clients['postgresql'].fetchval(old_data_query)
            
            policy_results["data_retention"] = {
                "old_records_exist": old_records > 0,
                "retention_policy_active": old_records == 0 or old_records is None
            }
        
        except Exception as e:
            policy_results["data_retention"] = {"error": str(e)}
        
        # Test access control policy implementation
        try:
            # Test unauthorized access prevention
            async with compliance_clients['http'].get(
                "http://localhost:8000/api/v1/admin/users"
            ) as response:
                policy_results["access_control"] = {
                    "unauthorized_access_blocked": response.status in [401, 403],
                    "policy_enforced": response.status in [401, 403]
                }
        
        except Exception as e:
            policy_results["access_control"] = {"error": str(e)}
        
        return policy_results


@pytest.mark.asyncio
async def test_compliance_audit_suite():
    """Run complete compliance audit test suite"""
    
    print("Starting compliance audit...")
    
    # Run compliance tests
    pytest_args = [
        __file__,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto"
    ]
    
    return pytest.main(pytest_args)


if __name__ == "__main__":
    asyncio.run(test_compliance_audit_suite())