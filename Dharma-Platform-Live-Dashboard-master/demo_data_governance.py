"""
Demonstration of Data Governance and Retention System

This script demonstrates the comprehensive data governance capabilities
including anonymization, classification, retention, and compliance reporting.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any

from shared.governance.data_anonymizer import (
    DataAnonymizer, AnonymizationConfig, AnonymizationRule, 
    AnonymizationMethod, PersonalDataDetector
)
from shared.governance.data_classifier import (
    DataClassifier, SensitivityLevel, DataType, ClassificationRule
)
from shared.governance.retention_manager import (
    RetentionManager, RetentionPolicy, DataCategory, RetentionAction
)
from shared.governance.compliance_reporter import (
    ComplianceReporter, ComplianceRegulation
)


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def print_subsection(title: str):
    """Print a formatted subsection header"""
    print(f"\n{'-'*40}")
    print(f" {title}")
    print(f"{'-'*40}")


async def demo_data_anonymization():
    """Demonstrate data anonymization capabilities"""
    print_section("DATA ANONYMIZATION DEMONSTRATION")
    
    # Create sample documents with sensitive data
    sample_documents = [
        {
            "_id": "post_001",
            "platform": "twitter",
            "user_id": "john_doe_123",
            "username": "john.doe",
            "email": "john.doe@example.com",
            "content": "Contact me at john.doe@gmail.com or call +91-9876543210. My Aadhaar is 1234 5678 9012.",
            "phone": "+91-9876543210",
            "location": "Mumbai, Maharashtra",
            "created_at": datetime.utcnow() - timedelta(days=10)
        },
        {
            "_id": "post_002",
            "platform": "youtube",
            "user_id": "jane_smith_456",
            "username": "jane.smith",
            "email": "jane.smith@company.com",
            "content": "My PAN number is ABCDE1234F and credit card ending in 3456.",
            "ip_address": "192.168.1.100",
            "created_at": datetime.utcnow() - timedelta(days=5)
        }
    ]
    
    print("Original Documents:")
    for i, doc in enumerate(sample_documents, 1):
        print(f"\nDocument {i}:")
        print(json.dumps(doc, indent=2, default=str))
    
    # Configure anonymization rules
    anonymization_config = AnonymizationConfig(
        rules=[
            AnonymizationRule("email", AnonymizationMethod.REDACTION, "[EMAIL_REDACTED]"),
            AnonymizationRule("user_id", AnonymizationMethod.PSEUDONYMIZATION),
            AnonymizationRule("username", AnonymizationMethod.PSEUDONYMIZATION),
            AnonymizationRule("phone", AnonymizationMethod.REDACTION, "[PHONE_REDACTED]"),
            AnonymizationRule("ip_address", AnonymizationMethod.GENERALIZATION)
        ],
        preserve_structure=True,
        audit_trail=True
    )
    
    # Create anonymizer
    anonymizer = DataAnonymizer(anonymization_config)
    
    print_subsection("Anonymization Process")
    
    # Anonymize documents
    anonymized_documents = await anonymizer.anonymize_batch(sample_documents)
    
    print("Anonymized Documents:")
    for i, doc in enumerate(anonymized_documents, 1):
        print(f"\nAnonymized Document {i}:")
        print(json.dumps(doc, indent=2, default=str))
    
    # Generate anonymization report
    report = anonymizer.create_anonymization_report(
        len(sample_documents), len(anonymized_documents)
    )
    
    print_subsection("Anonymization Report")
    print(json.dumps(report, indent=2, default=str))
    
    # Demonstrate personal data detection
    print_subsection("Personal Data Detection")
    
    detector = PersonalDataDetector()
    
    for i, doc in enumerate(sample_documents, 1):
        content = doc.get('content', '')
        detected = detector.detect_personal_data(content)
        sensitivity_score = detector.calculate_sensitivity_score(content)
        
        print(f"\nDocument {i} Analysis:")
        print(f"Content: {content}")
        print(f"Detected Personal Data: {detected}")
        print(f"Sensitivity Score: {sensitivity_score:.2f}")


async def demo_data_classification():
    """Demonstrate data classification capabilities"""
    print_section("DATA CLASSIFICATION DEMONSTRATION")
    
    # Create sample documents for classification
    test_documents = [
        {
            "_id": "doc_001",
            "content": "This is public information about our company.",
            "source": "website"
        },
        {
            "_id": "doc_002",
            "content": "Employee email: employee@company.com, Phone: 9876543210",
            "source": "internal_system"
        },
        {
            "_id": "doc_003",
            "content": "Customer Aadhaar: 1234 5678 9012, PAN: ABCDE1234F, Credit Card: 1234 5678 9012 3456",
            "source": "customer_database"
        },
        {
            "_id": "doc_004",
            "content": "API Key: sk_live_abc123def456ghi789, Database password: secret123",
            "source": "configuration"
        }
    ]
    
    # Create classifier
    classifier = DataClassifier()
    
    print("Classifying Documents:")
    
    # Classify each document
    classification_results = []
    for doc in test_documents:
        result = await classifier.classify_document(doc)
        classification_results.append(result)
        
        print(f"\nDocument ID: {doc['_id']}")
        print(f"Content: {doc['content']}")
        print(f"Sensitivity Level: {result.sensitivity_level.value}")
        print(f"Data Types: {[dt.value for dt in result.data_types]}")
        print(f"Confidence Score: {result.confidence_score:.2f}")
        print(f"Detected Patterns: {result.detected_patterns}")
        print(f"Recommendations: {result.recommendations}")
    
    # Generate classification statistics
    print_subsection("Classification Statistics")
    
    stats = classifier.get_classification_statistics(classification_results)
    print(json.dumps(stats, indent=2, default=str))
    
    # Demonstrate custom classification rule
    print_subsection("Custom Classification Rule")
    
    custom_rule = ClassificationRule(
        name="database_credentials",
        data_type=DataType.TECHNICAL,
        sensitivity_level=SensitivityLevel.RESTRICTED,
        patterns=[r'\bpassword\s*[:=]\s*\w+', r'\bsecret\s*[:=]\s*\w+'],
        keywords=['password', 'secret', 'credential'],
        weight=2.0
    )
    
    classifier.add_rule(custom_rule)
    print(f"Added custom rule: {custom_rule.name}")
    
    # Re-classify with custom rule
    result = await classifier.classify_document(test_documents[3])
    print(f"Re-classification result: {result.sensitivity_level.value} (confidence: {result.confidence_score:.2f})")


async def demo_retention_policies():
    """Demonstrate retention policy management"""
    print_section("DATA RETENTION POLICY DEMONSTRATION")
    
    # Mock database clients for demonstration
    class MockMongoClient:
        def __init__(self):
            self.dharma_platform = MockDatabase()
    
    class MockDatabase:
        def __init__(self):
            self.posts = MockCollection("posts", 1000)
            self.users = MockCollection("users", 500)
            self.analysis_results = MockCollection("analysis_results", 2000)
    
    class MockCollection:
        def __init__(self, name, count):
            self.name = name
            self.count = count
        
        async def count_documents(self, query):
            # Simulate old documents
            if 'created_at' in query and '$lt' in query['created_at']:
                return self.count // 4  # 25% are old
            return self.count
        
        async def delete_many(self, query):
            deleted = self.count // 4
            return type('Result', (), {'deleted_count': deleted})()
    
    class MockPostgreSQLPool:
        async def acquire(self):
            return MockConnection()
    
    class MockConnection:
        async def __aenter__(self):
            return self
        
        async def __aexit__(self, *args):
            pass
        
        async def fetchval(self, query, *args):
            return 100
        
        async def execute(self, query, *args):
            return "DELETE 25"
    
    class MockElasticsearch:
        async def count(self, **kwargs):
            return {"count": 500}
        
        async def delete_by_query(self, **kwargs):
            return {"deleted": 125}
    
    # Create mock clients
    mock_mongodb = MockMongoClient()
    mock_postgresql = MockPostgreSQLPool()
    mock_elasticsearch = MockElasticsearch()
    
    # Create retention manager
    retention_manager = RetentionManager(mock_mongodb, mock_postgresql, mock_elasticsearch)
    
    print("Creating Retention Policies:")
    
    # Create sample retention policies
    policies = [
        RetentionPolicy(
            name="social_media_posts_1_year",
            data_category=DataCategory.SOCIAL_MEDIA_POSTS,
            retention_period=timedelta(days=365),
            action=RetentionAction.ARCHIVE,
            conditions={"platform": {"$in": ["twitter", "youtube"]}}
        ),
        RetentionPolicy(
            name="analysis_results_6_months",
            data_category=DataCategory.ANALYSIS_RESULTS,
            retention_period=timedelta(days=180),
            action=RetentionAction.COMPRESS
        ),
        RetentionPolicy(
            name="system_logs_90_days",
            data_category=DataCategory.SYSTEM_LOGS,
            retention_period=timedelta(days=90),
            action=RetentionAction.DELETE
        ),
        RetentionPolicy(
            name="inactive_users_2_years",
            data_category=DataCategory.USER_PROFILES,
            retention_period=timedelta(days=730),
            action=RetentionAction.ANONYMIZE,
            conditions={"status": "inactive"}
        )
    ]
    
    # Add policies to manager
    for policy in policies:
        retention_manager.add_policy(policy)
        print(f"Added policy: {policy.name} ({policy.action.value} after {policy.retention_period.days} days)")
    
    print_subsection("Retention Status")
    
    # Get retention status
    status = retention_manager.get_retention_status()
    print(json.dumps(status, indent=2, default=str))
    
    print_subsection("Executing Retention Policies (Simulated)")
    
    # Simulate policy execution
    await retention_manager._execute_retention_policies()
    
    # Show updated status
    updated_status = retention_manager.get_retention_status()
    print("Updated Status:")
    print(json.dumps(updated_status, indent=2, default=str))
    
    print_subsection("Default Policies")
    
    # Show default policies
    default_policies = retention_manager.create_default_policies()
    print(f"Created {len(default_policies)} default retention policies:")
    for policy in default_policies[-5:]:  # Show last 5
        print(f"- {policy.name}: {policy.data_category.value} -> {policy.action.value}")


async def demo_compliance_reporting():
    """Demonstrate compliance reporting capabilities"""
    print_section("COMPLIANCE REPORTING DEMONSTRATION")
    
    # Mock database clients
    class MockMongoClient:
        def __init__(self):
            self.dharma_platform = MockDatabase()
    
    class MockDatabase:
        def __init__(self):
            self.posts = MockCollection()
            self.users = MockCollection()
    
    class MockCollection:
        async def count_documents(self, query):
            # Simulate compliance issues
            if 'content' in query and '$regex' in query['content']:
                return 50  # Unclassified personal data
            if '_classification' in query:
                return 25  # Missing classifications
            return 100
    
    class MockPostgreSQLPool:
        async def acquire(self):
            return MockConnection()
    
    class MockConnection:
        async def __aenter__(self):
            return self
        
        async def __aexit__(self, *args):
            pass
        
        async def fetchval(self, query, *args):
            return 10
        
        async def fetch(self, query, *args):
            return [{'audit_date': datetime.utcnow().date(), 'log_count': 5}]
    
    class MockElasticsearch:
        pass
    
    # Create compliance reporter
    compliance_reporter = ComplianceReporter(
        MockMongoClient(),
        MockPostgreSQLPool(),
        MockElasticsearch()
    )
    
    # Generate compliance reports
    start_date = datetime.utcnow() - timedelta(days=30)
    end_date = datetime.utcnow()
    
    print(f"Generating compliance reports for period: {start_date.date()} to {end_date.date()}")
    
    print_subsection("GDPR Compliance Report")
    
    gdpr_report = await compliance_reporter._generate_gdpr_report(start_date, end_date)
    
    print(f"Status: {gdpr_report.status.value}")
    print(f"Score: {gdpr_report.score:.1f}%")
    print(f"Issues Found: {len(gdpr_report.issues)}")
    
    for issue in gdpr_report.issues:
        print(f"- {issue.severity.upper()}: {issue.description}")
        print(f"  Affected Records: {issue.affected_records}")
        print(f"  Recommendation: {issue.recommendation}")
    
    print(f"\nRecommendations:")
    for rec in gdpr_report.recommendations:
        print(f"- {rec}")
    
    print_subsection("Data Retention Compliance Report")
    
    retention_report = await compliance_reporter._generate_retention_report(start_date, end_date)
    
    print(f"Status: {retention_report.status.value}")
    print(f"Score: {retention_report.score:.1f}%")
    print(f"Issues Found: {len(retention_report.issues)}")
    
    for issue in retention_report.issues:
        print(f"- {issue.severity.upper()}: {issue.description}")
    
    print_subsection("Security Compliance Report")
    
    security_report = await compliance_reporter._generate_security_report(start_date, end_date)
    
    print(f"Status: {security_report.status.value}")
    print(f"Score: {security_report.score:.1f}%")
    print(f"Issues Found: {len(security_report.issues)}")
    
    print_subsection("Comprehensive Compliance Report")
    
    # Generate comprehensive report (mocked)
    comprehensive_report = {
        'summary': {
            'overall_score': (gdpr_report.score + retention_report.score + security_report.score) / 3,
            'total_issues': len(gdpr_report.issues) + len(retention_report.issues) + len(security_report.issues),
            'report_period': {'start_date': start_date, 'end_date': end_date}
        },
        'regulation_reports': {
            'gdpr': {'status': gdpr_report.status.value, 'score': gdpr_report.score},
            'data_retention': {'status': retention_report.status.value, 'score': retention_report.score},
            'security': {'status': security_report.status.value, 'score': security_report.score}
        }
    }
    
    print(json.dumps(comprehensive_report, indent=2, default=str))


async def main():
    """Run all demonstrations"""
    print("PROJECT DHARMA - DATA GOVERNANCE SYSTEM DEMONSTRATION")
    print("=" * 80)
    
    try:
        await demo_data_anonymization()
        await demo_data_classification()
        await demo_retention_policies()
        await demo_compliance_reporting()
        
        print_section("DEMONSTRATION COMPLETED SUCCESSFULLY")
        print("All data governance components have been demonstrated:")
        print("✓ Data Anonymization and Personal Data Detection")
        print("✓ Data Classification and Sensitivity Labeling")
        print("✓ Automated Retention Policy Management")
        print("✓ Comprehensive Compliance Reporting")
        print("\nThe system is ready for production deployment!")
        
    except Exception as e:
        print(f"\nError during demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())