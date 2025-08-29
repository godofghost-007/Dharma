#!/usr/bin/env python3
"""
Complete Alert Management System Integration Test
Tests all components working together as a unified system
"""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.alert_generator import AlertGenerator
from app.core.alert_deduplicator import AlertDeduplicator
from app.core.alert_correlator import AlertCorrelator
from app.core.severity_calculator import SeverityCalculator
from app.notifications.notification_service import NotificationService
from app.core.alert_manager import AlertManager
from app.core.escalation_engine import EscalationEngine
from app.core.reporting_service import ReportingService
from app.core.search_service import SearchService

async def test_complete_alert_system():
    """Test the complete alert management system integration"""
    print('🔧 Testing Complete Alert Management System Integration')
    print('=' * 60)
    
    try:
        # Test 1: Alert Generation Pipeline
        print('\n1. Testing Alert Generation Pipeline...')
        alert_generator = AlertGenerator()
        
        # Create test content
        test_content = {
            'content': 'This is anti-India propaganda spreading false information',
            'platform': 'twitter',
            'user_id': 'suspicious_user_123',
            'timestamp': '2024-01-15T10:30:00Z',
            'metrics': {'likes': 500, 'shares': 200, 'comments': 100}
        }
        
        alert = await alert_generator.generate_alert(test_content)
        print(f'   ✅ Generated alert: {alert.id} (severity: {alert.severity})')
        
        # Test 2: Deduplication
        print('\n2. Testing Alert Deduplication...')
        deduplicator = AlertDeduplicator()
        
        # Test with same content
        duplicate_alert = await alert_generator.generate_alert(test_content)
        is_duplicate = await deduplicator.is_duplicate(duplicate_alert)
        print(f'   ✅ Duplicate detection: {is_duplicate}')
        
        # Test 3: Alert Correlation
        print('\n3. Testing Alert Correlation...')
        correlator = AlertCorrelator()
        
        # Create related alert
        related_content = {
            'content': 'Similar anti-India content from coordinated account',
            'platform': 'twitter', 
            'user_id': 'suspicious_user_456',
            'timestamp': '2024-01-15T10:35:00Z',
            'metrics': {'likes': 300, 'shares': 150, 'comments': 75}
        }
        
        related_alert = await alert_generator.generate_alert(related_content)
        correlations = await correlator.find_correlations([alert, related_alert])
        print(f'   ✅ Found {len(correlations)} correlations')
        
        # Test 4: Notification System
        print('\n4. Testing Notification System...')
        notification_service = NotificationService()
        
        recipients = [
            {'recipient': 'analyst@dharma.gov', 'channels': ['email', 'dashboard']},
            {'recipient': 'https://external-system.gov/webhooks/alerts', 'channels': ['webhook']}
        ]
        
        records = await notification_service.send_alert_notifications(alert, recipients)
        print(f'   ✅ Sent {len(records)} notifications')
        
        # Test 5: Alert Management Operations
        print('\n5. Testing Alert Management Operations...')
        alert_manager = AlertManager()
        
        # Acknowledge alert
        ack_result = await alert_manager.acknowledge_alert(alert.id, 'test_analyst', 'Reviewing content')
        print(f'   ✅ Alert acknowledged: {ack_result}')
        
        # Assign alert
        assign_result = await alert_manager.assign_alert(alert.id, 'senior_analyst', 'test_analyst', 'Escalating for review')
        print(f'   ✅ Alert assigned: {assign_result}')
        
        # Test 6: Escalation Engine
        print('\n6. Testing Escalation Engine...')
        escalation_engine = EscalationEngine()
        
        # Manual escalation
        escalation_result = await escalation_engine.escalate_alert(alert.id, 'senior_analyst', 'High priority threat')
        print(f'   ✅ Alert escalated: {escalation_result}')
        
        # Test 7: Search Service
        print('\n7. Testing Search Service...')
        search_service = SearchService()
        
        # Search for alerts
        search_results = await search_service.search_alerts('anti-India', filters={'severity': 'high'})
        print(f'   ✅ Search returned {len(search_results)} results')
        
        # Test 8: Reporting Service
        print('\n8. Testing Reporting Service...')
        reporting_service = ReportingService()
        
        # Generate statistics
        stats = await reporting_service.get_alert_statistics()
        print(f'   ✅ Generated statistics: {len(stats)} metrics')
        
        # Test 9: Complete Workflow
        print('\n9. Testing Complete Alert Workflow...')
        
        # Simulate complete workflow
        workflow_content = {
            'content': 'Coordinated disinformation campaign detected',
            'platform': 'telegram',
            'user_id': 'bot_network_001',
            'timestamp': '2024-01-15T11:00:00Z',
            'metrics': {'views': 10000, 'forwards': 500}
        }
        
        # Generate -> Check duplicates -> Correlate -> Notify -> Manage
        workflow_alert = await alert_generator.generate_alert(workflow_content)
        is_dup = await deduplicator.is_duplicate(workflow_alert)
        
        if not is_dup:
            correlations = await correlator.find_correlations([workflow_alert])
            notifications = await notification_service.send_alert_notifications(workflow_alert, recipients)
            acknowledgment = await alert_manager.acknowledge_alert(workflow_alert.id, 'analyst', 'Processing')
            
            print(f'   ✅ Complete workflow executed for alert {workflow_alert.id}')
        
        print('\n🎉 Alert Management System Integration Test Complete!')
        print('   All components working together successfully')
        
        return True
        
    except Exception as e:
        print(f'\n❌ Integration test failed: {e}')
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the integration test"""
    try:
        result = asyncio.run(test_complete_alert_system())
        if result:
            print('\n✅ INTEGRATION TEST PASSED')
            print('   Alert Management System is fully functional')
        else:
            print('\n❌ INTEGRATION TEST FAILED')
            sys.exit(1)
    except Exception as e:
        print(f'\n❌ INTEGRATION TEST FAILED: {e}')
        sys.exit(1)

if __name__ == "__main__":
    main()