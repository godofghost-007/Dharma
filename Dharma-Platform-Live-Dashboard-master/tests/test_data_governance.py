"""
Comprehensive tests for data governance and retention system
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from pymongo import MongoClient
import asyncpg

from shared.governance.data_anonymizer import (
    DataAnonymizer, AnonymizationConfig, AnonymizationRule, 
    AnonymizationMethod, PersonalDataDetector
)
from shared.governance.retention_manager import (
    RetentionManager, RetentionPolicy, DataCategory, RetentionAction
)
from shared.governance.data_classifier import (
    DataClassifier, SensitivityLevel, DataType, ClassificationRule
)
from shared.governance.governance_dashboard import GovernanceDashboard
from shared.governance.compliance_reporter import (
    ComplianceReporter, ComplianceRegulation, ComplianceStatus
)


class TestDataAnonymizer:
    """Test data anonymization functionality"""
    
    @pytest.fixture
    def anonymization_config(self):
        """Create test anonymization configuration"""
        return AnonymizationConfig(
            rules=[
                AnonymizationRule("email", AnonymizationMethod.REDACTION, "[EMAIL_REDACTED]"),
                AnonymizationRule("user_id", AnonymizationMethod.PSEUDONYMIZATION),
                AnonymizationRule("content", AnonymizationMethod.GENERALIZATION)
            ],
            preserve_structure=True,
            audit_trail=True
        )
    
    @pytest.fixture
    def anonymizer(self, anonymization_config):
        """Create test data anonymizer"""
        return DataAnonymizer(anonymization_config)
    
    @pytest.mark.asyncio
    async def test_anonymize_document(self, anonymizer):
        """Test document anonymization"""
        document = {
            "_id": "test_doc_1",
            "email": "user@example.com",
            "user_id": "user123",
            "content": "This is sensitive content with phone 9876543210",
            "created_at": datetime.utcnow()
        }
        
        result = await anonymizer.anonymize_document(document)
        
        # Check that sensitive data is anonymized
        assert result["email"] == "[EMAIL_REDACTED]"
        assert result["user_id"].startswith("USER_")
        assert "[PHONE]" in result["content"]
        assert "_anonymization_audit" in result
        
    @pytest.mark.asyncio
    async def test_batch_anonymization(self, anonymizer):
        """Test batch document anonymization"""
        documents = [
            {"_id": "doc1", "email": "user1@test.com", "content": "Content 1"},
            {"_id": "doc2", "email": "user2@test.com", "content": "Content 2"}
        ]
        
        results = await anonymizer.anonymize_batch(documents)
        
        assert len(results) == 2
        for result in results:
            assert result["email"] == "[EMAIL_REDACTED]"
            assert "_anonymization_audit" in result
    
    def test_personal_data_detector(self):
        """Test personal data detection"""
        detector = PersonalDataDetector()
        
        content = """
        Contact me at john.doe@example.com or call 9876543210.
        My Aadhaar is 1234 5678 9012 and PAN is ABCDE1234F.
        """
        
        detected = detector.detect_personal_data(content)
        
        assert len(detected['high_sensitivity']) > 0  # Aadhaar, PAN
        assert len(detected['medium_sensitivity']) > 0  # Email, Phone
        
        sensitivity_score = detector.calculate_sensitivity_score(content)
        assert 0 < sensitivity_score <= 1


class TestRetentionManager:
    """Test data retention management"""
    
    @pytest.fixture
    def mock_mongodb(self):
        """Mock MongoDB client"""
        mock_client = Mock()
        mock_db = Mock()
        mock_collection = Mock()
        
        mock_client.dharma_platform = mock_db
        mock_db.posts = mock_collection
        mock_collection.count_documents = AsyncMock(return_value=100)
        mock_collection.delete_many = AsyncMock(return_value=Mock(deleted_count=50))
        
        return mock_client
    
    @pytest.fixture
    def mock_postgresql(self):
        """Mock PostgreSQL pool"""
        mock_pool = Mock()
        mock_conn = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        mock_conn.fetchval = AsyncMock(return_value=25)
        mock_conn.execute = AsyncMock(return_value="DELETE 25")
        
        return mock_pool
    
    @pytest.fixture
    def mock_elasticsearch(self):
        """Mock Elasticsearch client"""
        mock_es = Mock()
        mock_es.count = AsyncMock(return_value={"count": 75})
        mock_es.delete_by_query = AsyncMock(return_value={"deleted": 30})
        
        return mock_es
    
    @pytest.fixture
    def retention_manager(self, mock_mongodb, mock_postgresql, mock_elasticsearch):
        """Create test retention manager"""
        return RetentionManager(mock_mongodb, mock_postgresql, mock_elasticsearch)
    
    def test_add_retention_policy(self, retention_manager):
        """Test adding retention policy"""
        policy = RetentionPolicy(
            name="test_policy",
            data_category=DataCategory.SOCIAL_MEDIA_POSTS,
            retention_period=timedelta(days=365),
            action=RetentionAction.DELETE
        )
        
        retention_manager.add_policy(policy)
        
        assert len(retention_manager.policies) == 1
        assert retention_manager.policies[0].name == "test_policy"
    
    @pytest.mark.asyncio
    async def test_execute_retention_policy(self, retention_manager):
        """Test retention policy execution"""
        policy = RetentionPolicy(
            name="test_policy",
            data_category=DataCategory.SOCIAL_MEDIA_POSTS,
            retention_period=timedelta(days=365),
            action=RetentionAction.DELETE
        )
        
        retention_manager.add_policy(policy)
        
        # Mock the execution
        with patch.object(retention_manager, '_process_social_media_posts') as mock_process:
            mock_process.return_value = None
            
            await retention_manager._execute_retention_policies()
            
            mock_process.assert_called_once()
    
    def test_create_default_policies(self, retention_manager):
        """Test creation of default retention policies"""
        policies = retention_manager.create_default_policies()
        
        assert len(policies) > 0
        assert len(retention_manager.policies) > 0
        
        # Check that different data categories are covered
        categories = {p.data_category for p in policies}
        assert DataCategory.SOCIAL_MEDIA_POSTS in categories
        assert DataCategory.AUDIT_LOGS in categories


class TestDataClassifier:
    """Test data classification functionality"""
    
    @pytest.fixture
    def classifier(self):
        """Create test data classifier"""
        return DataClassifier()
    
    @pytest.mark.asyncio
    async def test_classify_document(self, classifier):
        """Test document classification"""
        document = {
            "_id": "test_doc",
            "content": "Contact john.doe@example.com for details. Aadhaar: 1234 5678 9012",
            "user_data": {
                "phone": "9876543210",
                "location": "Mumbai"
            }
        }
        
        result = await classifier.classify_document(document)
        
        assert result.sensitivity_level in [SensitivityLevel.CONFIDENTIAL, SensitivityLevel.RESTRICTED]
        assert DataType.PERSONAL_IDENTIFIABLE in result.data_types
        assert result.confidence_score > 0
        assert len(result.recommendations) > 0
    
    @pytest.mark.asyncio
    async def test_batch_classification(self, classifier):
        """Test batch document classification"""
        documents = [
            {"_id": "doc1", "content": "Public information"},
            {"_id": "doc2", "content": "Email: user@test.com, Phone: 1234567890"},
            {"_id": "doc3", "content": "Credit card: 1234 5678 9012 3456"}
        ]
        
        results = await classifier.classify_batch(documents)
        
        assert len(results) == 3
        assert results[0].sensitivity_level == SensitivityLevel.PUBLIC
        assert results[1].sensitivity_level in [SensitivityLevel.CONFIDENTIAL, SensitivityLevel.RESTRICTED]
        assert results[2].sensitivity_level == SensitivityLevel.RESTRICTED
    
    def test_add_custom_rule(self, classifier):
        """Test adding custom classification rule"""
        rule = ClassificationRule(
            name="custom_test_rule",
            data_type=DataType.TECHNICAL,
            sensitivity_level=SensitivityLevel.INTERNAL,
            patterns=[r'\bAPI_KEY_\w+'],
            keywords=['api key', 'secret'],
            weight=1.5
        )
        
        initial_count = len(classifier.rules)
        classifier.add_rule(rule)
        
        assert len(classifier.rules) == initial_count + 1
        assert classifier.rules[-1].name == "custom_test_rule"
    
    def test_export_import_rules(self, classifier):
        """Test rule export and import functionality"""
        # Export rules
        exported_rules = classifier.export_classification_rules()
        
        assert len(exported_rules) > 0
        assert all('name' in rule for rule in exported_rules)
        
        # Create new classifier and import rules
        new_classifier = DataClassifier()
        new_classifier.rules = []  # Clear default rules
        new_classifier.import_classification_rules(exported_rules)
        
        assert len(new_classifier.rules) == len(exported_rules)


class TestGovernanceDashboard:
    """Test governance dashboard functionality"""
    
    @pytest.fixture
    def mock_retention_manager(self):
        """Mock retention manager"""
        mock_manager = Mock()
        mock_manager.get_retention_status.return_value = {
            'total_policies': 5,
            'active_policies': 4,
            'recent_jobs': 10,
            'successful_jobs': 8,
            'failed_jobs': 2
        }
        mock_manager.policies = []
        mock_manager.jobs = []
        
        return mock_manager
    
    @pytest.fixture
    def mock_classifier(self):
        """Mock data classifier"""
        return Mock()
    
    @pytest.fixture
    def governance_dashboard(self, mock_mongodb, mock_postgresql, 
                           mock_elasticsearch, mock_retention_manager, mock_classifier):
        """Create test governance dashboard"""
        return GovernanceDashboard(
            mock_mongodb, mock_postgresql, mock_elasticsearch,
            mock_retention_manager, mock_classifier
        )
    
    @pytest.mark.asyncio
    async def test_get_governance_overview(self, governance_dashboard):
        """Test governance overview generation"""
        with patch.object(governance_dashboard, '_calculate_governance_metrics') as mock_metrics:
            mock_metrics.return_value = Mock(
                total_documents=1000,
                classified_documents=800,
                anonymized_documents=200,
                compliance_score=85.5,
                last_updated=datetime.utcnow()
            )
            
            with patch.object(governance_dashboard, '_get_classification_statistics') as mock_stats:
                mock_stats.return_value = {
                    'sensitivity_distribution': {'public': 500, 'confidential': 300},
                    'classification_coverage': 80.0
                }
                
                with patch.object(governance_dashboard, '_get_compliance_status') as mock_compliance:
                    mock_compliance.return_value = []
                    
                    with patch.object(governance_dashboard, '_get_recent_activities') as mock_activities:
                        mock_activities.return_value = []
                        
                        overview = await governance_dashboard.get_governance_overview()
                        
                        assert 'overview' in overview
                        assert 'retention' in overview
                        assert 'classification' in overview
                        assert overview['overview']['total_documents'] == 1000
    
    @pytest.mark.asyncio
    async def test_generate_governance_report(self, governance_dashboard):
        """Test governance report generation"""
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
        
        with patch.object(governance_dashboard, 'get_governance_overview') as mock_overview:
            mock_overview.return_value = {'overview': {'compliance_score': 85.0}}
            
            with patch.object(governance_dashboard, '_get_compliance_trends') as mock_trends:
                mock_trends.return_value = {'current_score': 85.0, 'trend': 'stable'}
                
                with patch.object(governance_dashboard, '_generate_governance_recommendations') as mock_recs:
                    mock_recs.return_value = ['Improve classification coverage']
                    
                    report = await governance_dashboard.generate_governance_report(start_date, end_date)
                    
                    assert 'report_period' in report
                    assert 'overview' in report
                    assert 'recommendations' in report


class TestComplianceReporter:
    """Test compliance reporting functionality"""
    
    @pytest.fixture
    def compliance_reporter(self, mock_mongodb, mock_postgresql, mock_elasticsearch):
        """Create test compliance reporter"""
        return ComplianceReporter(mock_mongodb, mock_postgresql, mock_elasticsearch)
    
    @pytest.mark.asyncio
    async def test_generate_gdpr_report(self, compliance_reporter):
        """Test GDPR compliance report generation"""
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
        
        # Mock database responses
        with patch.object(compliance_reporter.mongodb.dharma_platform.posts, 'count_documents') as mock_count:
            mock_count.return_value = 50  # Unclassified personal data
            
            report = await compliance_reporter._generate_gdpr_report(start_date, end_date)
            
            assert report.regulation == ComplianceRegulation.GDPR
            assert len(report.issues) > 0
            assert report.score >= 0
            assert len(report.recommendations) > 0
    
    @pytest.mark.asyncio
    async def test_comprehensive_compliance_report(self, compliance_reporter):
        """Test comprehensive compliance report generation"""
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
        
        with patch.object(compliance_reporter, 'generate_regulation_report') as mock_reg_report:
            mock_report = Mock()
            mock_report.score = 85.0
            mock_report.status = ComplianceStatus.COMPLIANT
            mock_report.issues = []
            mock_reg_report.return_value = mock_report
            
            report = await compliance_reporter.generate_comprehensive_report(start_date, end_date)
            
            assert 'summary' in report
            assert 'regulation_reports' in report
            assert 'detailed_reports' in report
            assert report['summary']['overall_score'] > 0


@pytest.mark.integration
class TestDataGovernanceIntegration:
    """Integration tests for data governance system"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_governance_workflow(self):
        """Test complete governance workflow"""
        # This would test the integration of all components
        # In a real scenario, this would use test databases
        
        # 1. Classify documents
        classifier = DataClassifier()
        
        test_document = {
            "_id": "integration_test",
            "content": "User email: test@example.com, Phone: 9876543210",
            "created_at": datetime.utcnow()
        }
        
        classification_result = await classifier.classify_document(test_document)
        assert classification_result.sensitivity_level != SensitivityLevel.PUBLIC
        
        # 2. Apply anonymization
        config = AnonymizationConfig(
            rules=[
                AnonymizationRule("content", AnonymizationMethod.REDACTION, "[REDACTED]")
            ]
        )
        anonymizer = DataAnonymizer(config)
        
        anonymized_doc = await anonymizer.anonymize_document(test_document)
        assert "_anonymization_audit" in anonymized_doc
        
        # 3. Test retention policy (mocked)
        # This would normally interact with real databases
        
        print("End-to-end governance workflow test completed successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])