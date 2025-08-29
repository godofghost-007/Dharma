"""
Comprehensive test suite for Alert Management Interface.

Tests all components of task 6.3: Build alert management interface
- Alert inbox with filtering and search capabilities
- Alert acknowledgment and assignment features
- Alert resolution tracking and reporting
- Alert escalation workflows and automation
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
import json

from shared.models.alert import (
    Alert, AlertCreate, AlertSummary, AlertType, SeverityLevel, 
    AlertStatus, EscalationLevel, AlertContext
)
from app.interface.web_interface import create_app
from app.core.alert_manager import AlertManager
from app.core.search_service import AlertSearchService
from app.core.reporting_service import ReportingService
from app.core.escalation_engine import EscalationEngine


class TestAlertManagementInterface:
    """Test suite for alert management interface functionality."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)
    
    @pytest.fixture
    def mock_alert_manager(self):
        """Mock alert manager."""
        return Mock(spec=AlertManager)
    
    @pytest.fixture
    def mock_search_service(self):
        """Mock search service."""
        return Mock(spec=AlertSearchService)
    
    @pytest.fixture
    def mock_reporting_service(self):
        """Mock reporting service."""
        return Mock(spec=ReportingService)
    
    @pytest.fixture
    def mock_escalation_engine(self):
        """Mock escalation engine."""
        return Mock(spec=EscalationEngine)
    
    @pytest.fixture
    def sample_alert(self):
        """Create sample alert for testing."""
        return Alert(
            alert_id="test_alert_001",
            title="Test High Risk Content Alert",
            description="Test alert for high risk content detection",
            alert_type=AlertType.HIGH_RISK_CONTENT,
            severity=SeverityLevel.HIGH,
            status=AlertStatus.NEW,
            context=AlertContext(
                source_platform="twitter",
                content_samples=["Test content sample"],
                risk_score=0.85,
                confidence_score=0.92
            ),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    @pytest.fixture
    def sample_alert_summary(self):
        """Create sample alert summary for testing."""
        return AlertSummary(
            alert_id="test_alert_001",
            title="Test High Risk Content Alert",
            alert_type=AlertType.HIGH_RISK_CONTENT,
            severity=SeverityLevel.HIGH,
            status=AlertStatus.NEW,
            created_at=datetime.utcnow()
        )


class TestAlertInboxInterface(TestAlertManagementInterface):
    """Test alert inbox functionality."""
    
    def test_inbox_page_loads(self, client):
        """Test that inbox page loads successfully."""
        response = client.get("/inbox")
        assert response.status_code == 200
        assert "Alert Inbox" in response.text
    
    def test_inbox_with_filters(self, client):
        """Test inbox with various filters."""
        # Test status filter
        response = client.get("/inbox?status=new&status=acknowledged")
        assert response.status_code == 200
        
        # Test severity filter
        response = client.get("/inbox?severity=critical&severity=high")
        assert response.status_code == 200
        
        # Test alert type filter
        response = client.get("/inbox?alert_type=high_risk_content")
        assert response.status_code == 200
        
        # Test assignment filter
        response = client.get("/inbox?assigned_to=analyst_1")
        assert response.status_code == 200
    
    def test_inbox_pagination(self, client):
        """Test inbox pagination."""
        # Test first page
        response = client.get("/inbox?page=1&limit=10")
        assert response.status_code == 200
        
        # Test second page
        response = client.get("/inbox?page=2&limit=10")
        assert response.status_code == 200
    
    @patch('app.interface.web_interface.AlertManager')
    def test_inbox_with_mock_data(self, mock_manager_class, client, sample_alert_summary):
        """Test inbox with mocked alert data."""
        mock_manager = Mock()
        mock_manager.get_alerts = AsyncMock(return_value=[sample_alert_summary])
        mock_manager_class.return_value = mock_manager
        
        response = client.get("/inbox")
        assert response.status_code == 200
        assert "Test High Risk Content Alert" in response.text


class TestAlertDetailsInterface(TestAlertManagementInterface):
    """Test alert details functionality."""
    
    @patch('app.interface.web_interface.AlertManager')
    def test_alert_details_page(self, mock_manager_class, client, sample_alert):
        """Test alert details page."""
        mock_manager = Mock()
        mock_manager.get_alert_by_id = AsyncMock(return_value=sample_alert)
        mock_manager_class.return_value = mock_manager
        
        response = client.get("/alert/test_alert_001")
        assert response.status_code == 200
        assert "Test High Risk Content Alert" in response.text
    
    @patch('app.interface.web_interface.AlertManager')
    def test_alert_not_found(self, mock_manager_class, client):
        """Test alert not found scenario."""
        mock_manager = Mock()
        mock_manager.get_alert_by_id = AsyncMock(return_value=None)
        mock_manager_class.return_value = mock_manager
        
        response = client.get("/alert/nonexistent_alert")
        assert response.status_code == 404


class TestAlertAcknowledgment(TestAlertManagementInterface):
    """Test alert acknowledgment functionality."""
    
    @patch('app.interface.web_interface.AlertManager')
    def test_acknowledge_alert_success(self, mock_manager_class, client):
        """Test successful alert acknowledgment."""
        mock_manager = Mock()
        mock_manager.acknowledge_alert = AsyncMock(return_value=True)
        mock_manager_class.return_value = mock_manager
        
        response = client.post(
            "/api/alerts/test_alert_001/acknowledge",
            data={
                "user_id": "analyst_1",
                "notes": "Acknowledged for investigation"
            }
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert "acknowledged successfully" in result["message"]
    
    @patch('app.interface.web_interface.AlertManager')
    def test_acknowledge_alert_failure(self, mock_manager_class, client):
        """Test failed alert acknowledgment."""
        mock_manager = Mock()
        mock_manager.acknowledge_alert = AsyncMock(return_value=False)
        mock_manager_class.return_value = mock_manager
        
        response = client.post(
            "/api/alerts/test_alert_001/acknowledge",
            data={
                "user_id": "analyst_1",
                "notes": "Test acknowledgment"
            }
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is False
    
    @patch('app.interface.web_interface.AlertManager')
    def test_acknowledge_alert_exception(self, mock_manager_class, client):
        """Test alert acknowledgment with exception."""
        mock_manager = Mock()
        mock_manager.acknowledge_alert = AsyncMock(side_effect=Exception("Database error"))
        mock_manager_class.return_value = mock_manager
        
        response = client.post(
            "/api/alerts/test_alert_001/acknowledge",
            data={
                "user_id": "analyst_1",
                "notes": "Test acknowledgment"
            }
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is False
        assert "Database error" in result["message"]


class TestAlertAssignment(TestAlertManagementInterface):
    """Test alert assignment functionality."""
    
    @patch('app.interface.web_interface.AlertManager')
    def test_assign_alert_success(self, mock_manager_class, client):
        """Test successful alert assignment."""
        mock_manager = Mock()
        mock_manager.assign_alert = AsyncMock(return_value=True)
        mock_manager_class.return_value = mock_manager
        
        response = client.post(
            "/api/alerts/test_alert_001/assign",
            data={
                "assigned_to": "analyst_2",
                "assigned_by": "supervisor_1",
                "notes": "Assigning to specialist"
            }
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert "assigned to analyst_2" in result["message"]
    
    @patch('app.interface.web_interface.AlertManager')
    def test_assign_alert_failure(self, mock_manager_class, client):
        """Test failed alert assignment."""
        mock_manager = Mock()
        mock_manager.assign_alert = AsyncMock(return_value=False)
        mock_manager_class.return_value = mock_manager
        
        response = client.post(
            "/api/alerts/test_alert_001/assign",
            data={
                "assigned_to": "analyst_2",
                "assigned_by": "supervisor_1"
            }
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is False


class TestAlertResolution(TestAlertManagementInterface):
    """Test alert resolution functionality."""
    
    @patch('app.interface.web_interface.AlertManager')
    def test_resolve_alert_success(self, mock_manager_class, client):
        """Test successful alert resolution."""
        mock_manager = Mock()
        mock_manager.resolve_alert = AsyncMock(return_value=True)
        mock_manager_class.return_value = mock_manager
        
        response = client.post(
            "/api/alerts/test_alert_001/resolve",
            data={
                "resolved_by": "analyst_1",
                "resolution_type": "False Positive",
                "resolution_notes": "Content was misclassified by AI model"
            }
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert "resolved successfully" in result["message"]
    
    @patch('app.interface.web_interface.AlertManager')
    def test_resolve_alert_failure(self, mock_manager_class, client):
        """Test failed alert resolution."""
        mock_manager = Mock()
        mock_manager.resolve_alert = AsyncMock(return_value=False)
        mock_manager_class.return_value = mock_manager
        
        response = client.post(
            "/api/alerts/test_alert_001/resolve",
            data={
                "resolved_by": "analyst_1",
                "resolution_type": "Resolved",
                "resolution_notes": "Issue addressed"
            }
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is False


class TestAlertEscalation(TestAlertManagementInterface):
    """Test alert escalation functionality."""
    
    @patch('app.interface.web_interface.EscalationEngine')
    def test_escalate_alert_success(self, mock_engine_class, client):
        """Test successful alert escalation."""
        mock_engine = Mock()
        mock_engine.escalate_alert = AsyncMock(return_value=True)
        mock_engine_class.return_value = mock_engine
        
        response = client.post(
            "/api/alerts/test_alert_001/escalate",
            data={
                "escalated_by": "analyst_1",
                "escalation_level": "level_2",
                "reason": "Requires supervisor attention",
                "notes": "Complex case needs expert review"
            }
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert "escalated to level_2" in result["message"]
    
    @patch('app.interface.web_interface.EscalationEngine')
    def test_escalate_alert_failure(self, mock_engine_class, client):
        """Test failed alert escalation."""
        mock_engine = Mock()
        mock_engine.escalate_alert = AsyncMock(return_value=False)
        mock_engine_class.return_value = mock_engine
        
        response = client.post(
            "/api/alerts/test_alert_001/escalate",
            data={
                "escalated_by": "analyst_1",
                "escalation_level": "level_2",
                "reason": "Test escalation"
            }
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is False


class TestBulkOperations(TestAlertManagementInterface):
    """Test bulk operations functionality."""
    
    @patch('app.interface.web_interface.AlertManager')
    def test_bulk_operations_success(self, mock_manager_class, client):
        """Test successful bulk operations."""
        mock_manager = Mock()
        mock_manager.bulk_operation = AsyncMock(return_value={
            "successful": ["alert_001", "alert_002"],
            "failed": [],
            "total": 2
        })
        mock_manager_class.return_value = mock_manager
        
        response = client.post(
            "/api/bulk-operations",
            data={
                "operation": "acknowledge",
                "alert_ids": json.dumps(["alert_001", "alert_002"]),
                "user_id": "analyst_1",
                "parameters": json.dumps({"notes": "Bulk acknowledged"})
            }
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert "Bulk acknowledge completed" in result["message"]
    
    @patch('app.interface.web_interface.AlertManager')
    def test_bulk_operations_with_failures(self, mock_manager_class, client):
        """Test bulk operations with some failures."""
        mock_manager = Mock()
        mock_manager.bulk_operation = AsyncMock(return_value={
            "successful": ["alert_001"],
            "failed": [{"alert_id": "alert_002", "reason": "Already resolved"}],
            "total": 2
        })
        mock_manager_class.return_value = mock_manager
        
        response = client.post(
            "/api/bulk-operations",
            data={
                "operation": "resolve",
                "alert_ids": json.dumps(["alert_001", "alert_002"]),
                "user_id": "analyst_1",
                "parameters": json.dumps({
                    "resolution_type": "Resolved",
                    "resolution_notes": "Bulk resolved"
                })
            }
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert len(result["results"]["failed"]) == 1


class TestSearchInterface(TestAlertManagementInterface):
    """Test search interface functionality."""
    
    def test_search_page_loads(self, client):
        """Test that search page loads successfully."""
        response = client.get("/search")
        assert response.status_code == 200
        assert "Advanced Search" in response.text
    
    @patch('app.interface.web_interface.AlertSearchService')
    def test_search_with_query(self, mock_search_class, client):
        """Test search with text query."""
        mock_search = Mock()
        mock_search.advanced_search = AsyncMock(return_value={
            "alerts": [],
            "total_hits": 0,
            "facets": {}
        })
        mock_search_class.return_value = mock_search
        
        response = client.post(
            "/search",
            data={
                "query": "high risk content",
                "alert_types": ["high_risk_content"],
                "severities": ["high", "critical"]
            }
        )
        
        assert response.status_code == 200
        assert "Search Results" in response.text
    
    @patch('app.interface.web_interface.AlertSearchService')
    def test_search_suggestions_api(self, mock_search_class, client):
        """Test search suggestions API."""
        mock_search = Mock()
        mock_search.get_search_suggestions = AsyncMock(return_value=[
            "bot network", "misinformation", "viral content"
        ])
        mock_search_class.return_value = mock_search
        
        response = client.get("/api/search/suggestions?query=bot")
        assert response.status_code == 200
        
        result = response.json()
        assert "suggestions" in result
        assert len(result["suggestions"]) > 0


class TestAnalyticsInterface(TestAlertManagementInterface):
    """Test analytics and reporting interface."""
    
    def test_analytics_page_loads(self, client):
        """Test that analytics page loads successfully."""
        response = client.get("/analytics")
        assert response.status_code == 200
        assert "Analytics Dashboard" in response.text
    
    def test_analytics_with_period(self, client):
        """Test analytics with different time periods."""
        response = client.get("/analytics?period=7")
        assert response.status_code == 200
        
        response = client.get("/analytics?period=30")
        assert response.status_code == 200
        
        response = client.get("/analytics?period=90")
        assert response.status_code == 200
    
    def test_alert_stats_api(self, client):
        """Test alert statistics API."""
        response = client.get("/api/alerts/stats")
        assert response.status_code == 200
        
        result = response.json()
        assert "total_alerts" in result
        assert "active_alerts" in result


class TestEscalationInterface(TestAlertManagementInterface):
    """Test escalation management interface."""
    
    def test_escalation_page_loads(self, client):
        """Test that escalation page loads successfully."""
        response = client.get("/escalation")
        assert response.status_code == 200
        assert "Escalation Management" in response.text
    
    @patch('app.interface.web_interface.EscalationEngine')
    def test_create_escalation_rule(self, mock_engine_class, client):
        """Test creating escalation rule."""
        mock_engine = Mock()
        mock_engine.configure_auto_escalation = AsyncMock(return_value=True)
        mock_engine_class.return_value = mock_engine
        
        response = client.post(
            "/api/escalation/rules",
            data={
                "alert_type": "high_risk_content",
                "severity": "critical",
                "escalation_delay_minutes": 15,
                "escalation_level": "level_2",
                "max_unacknowledged_time": 30,
                "max_investigation_time": 120,
                "configured_by": "supervisor_1"
            }
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True


class TestIntegrationScenarios(TestAlertManagementInterface):
    """Test complete workflow scenarios."""
    
    @patch('app.interface.web_interface.AlertManager')
    @patch('app.interface.web_interface.EscalationEngine')
    def test_complete_alert_workflow(self, mock_engine_class, mock_manager_class, client, sample_alert):
        """Test complete alert workflow from creation to resolution."""
        # Setup mocks
        mock_manager = Mock()
        mock_engine = Mock()
        
        mock_manager.get_alert_by_id = AsyncMock(return_value=sample_alert)
        mock_manager.acknowledge_alert = AsyncMock(return_value=True)
        mock_manager.assign_alert = AsyncMock(return_value=True)
        mock_manager.resolve_alert = AsyncMock(return_value=True)
        mock_engine.escalate_alert = AsyncMock(return_value=True)
        
        mock_manager_class.return_value = mock_manager
        mock_engine_class.return_value = mock_engine
        
        # 1. View alert details
        response = client.get("/alert/test_alert_001")
        assert response.status_code == 200
        
        # 2. Acknowledge alert
        response = client.post(
            "/api/alerts/test_alert_001/acknowledge",
            data={"user_id": "analyst_1", "notes": "Starting investigation"}
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
        
        # 3. Assign alert
        response = client.post(
            "/api/alerts/test_alert_001/assign",
            data={
                "assigned_to": "analyst_2",
                "assigned_by": "analyst_1",
                "notes": "Transferring to specialist"
            }
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
        
        # 4. Escalate alert
        response = client.post(
            "/api/alerts/test_alert_001/escalate",
            data={
                "escalated_by": "analyst_2",
                "escalation_level": "level_2",
                "reason": "Requires supervisor review"
            }
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
        
        # 5. Resolve alert
        response = client.post(
            "/api/alerts/test_alert_001/resolve",
            data={
                "resolved_by": "supervisor_1",
                "resolution_type": "Resolved",
                "resolution_notes": "Issue addressed and mitigated"
            }
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    @patch('app.interface.web_interface.AlertManager')
    def test_bulk_workflow_scenario(self, mock_manager_class, client):
        """Test bulk operations workflow."""
        mock_manager = Mock()
        mock_manager.bulk_operation = AsyncMock(return_value={
            "successful": ["alert_001", "alert_002", "alert_003"],
            "failed": [],
            "total": 3
        })
        mock_manager_class.return_value = mock_manager
        
        # Bulk acknowledge
        response = client.post(
            "/api/bulk-operations",
            data={
                "operation": "acknowledge",
                "alert_ids": json.dumps(["alert_001", "alert_002", "alert_003"]),
                "user_id": "supervisor_1",
                "parameters": json.dumps({"notes": "Bulk processing"})
            }
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["results"]["total"] == 3
        assert len(result["results"]["successful"]) == 3


class TestErrorHandling(TestAlertManagementInterface):
    """Test error handling scenarios."""
    
    def test_invalid_alert_id(self, client):
        """Test handling of invalid alert IDs."""
        response = client.post(
            "/api/alerts/invalid_id/acknowledge",
            data={"user_id": "analyst_1"}
        )
        # Should handle gracefully
        assert response.status_code == 200
    
    def test_malformed_bulk_request(self, client):
        """Test handling of malformed bulk requests."""
        response = client.post(
            "/api/bulk-operations",
            data={
                "operation": "acknowledge",
                "alert_ids": "invalid_json",
                "user_id": "analyst_1",
                "parameters": "{}"
            }
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is False
    
    def test_missing_required_fields(self, client):
        """Test handling of missing required fields."""
        response = client.post(
            "/api/alerts/test_alert_001/resolve",
            data={
                "resolved_by": "analyst_1"
                # Missing resolution_type and resolution_notes
            }
        )
        
        # Should handle missing fields gracefully
        assert response.status_code in [200, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])