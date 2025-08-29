#!/usr/bin/env python3
"""
Disaster Recovery Test Runner
Executes comprehensive disaster recovery testing suite
"""

import asyncio
import sys
import time
import json
from datetime import datetime
from pathlib import Path
import subprocess

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from tests.disaster_recovery.test_backup_restore import (
    TestAutomatedBackupProcedures,
    TestDataIntegrityValidation,
    TestRestoreProcedures,
    TestRTORPOCompliance,
    TestDisasterRecoveryDrills
)

from tests.disaster_recovery.test_failover_procedures import (
    TestDataReplication,
    TestFailoverProcedures,
    TestBackupAndRestore,
    TestDisasterRecoveryDrill,
    TestIntegratedDisasterRecovery
)


class DisasterRecoveryTestRunner:
    """Comprehensive disaster recovery test runner"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = None
        self.end_time = None
    
    async def run_all_tests(self):
        """Run all disaster recovery tests"""
        print("="*80)
        print("PROJECT DHARMA - DISASTER RECOVERY TEST SUITE")
        print("="*80)
        print(f"Started at: {datetime.utcnow().isoformat()}")
        print("="*80)
        
        self.start_time = time.time()
        
        # Test categories to run
        test_categories = [
            ("Backup and Restore Procedures", self.run_backup_restore_tests),
            ("Data Replication Tests", self.run_replication_tests),
            ("Failover Procedures", self.run_failover_tests),
            ("RTO/RPO Compliance", self.run_rto_rpo_tests),
            ("Complete DR Drill", self.run_complete_dr_drill),
            ("Integration Tests", self.run_integration_tests)
        ]
        
        for category_name, test_function in test_categories:
            print(f"\n{'='*60}")
            print(f"RUNNING: {category_name}")
            print(f"{'='*60}")
            
            try:
                category_results = await test_function()
                self.test_results[category_name] = {
                    "status": "PASSED",
                    "results": category_results
                }
                print(f"✓ {category_name}: PASSED")
            
            except Exception as e:
                self.test_results[category_name] = {
                    "status": "FAILED",
                    "error": str(e)
                }
                print(f"✗ {category_name}: FAILED - {str(e)}")
        
        self.end_time = time.time()
        
        # Generate final report
        await self.generate_final_report()
    
    async def run_backup_restore_tests(self):
        """Run backup and restore tests"""
        results = {}
        
        # Mock clients for testing
        mock_clients = await self.create_mock_clients()
        
        try:
            # Test automated backup procedures
            backup_tester = TestAutomatedBackupProcedures()
            results["mongodb_backup"] = await backup_tester.test_mongodb_backup_creation(mock_clients)
            results["postgresql_backup"] = await backup_tester.test_postgresql_backup_creation(mock_clients)
            results["redis_backup"] = await backup_tester.test_redis_backup_creation(mock_clients)
            
            # Test data integrity
            integrity_tester = TestDataIntegrityValidation()
            results["data_consistency"] = await integrity_tester.test_backup_data_consistency(mock_clients)
            results["checksum_validation"] = await integrity_tester.test_backup_checksum_validation(mock_clients)
            
            # Test restore procedures
            restore_tester = TestRestoreProcedures()
            results["mongodb_restore"] = await restore_tester.test_mongodb_restore_procedure(mock_clients)
            results["postgresql_restore"] = await restore_tester.test_postgresql_restore_procedure(mock_clients)
            
        finally:
            await self.cleanup_mock_clients(mock_clients)
        
        return results
    
    async def run_replication_tests(self):
        """Run data replication tests"""
        results = {}
        
        mock_clients = await self.create_mock_clients()
        
        try:
            replication_tester = TestDataReplication()
            results["mongodb_replication"] = await replication_tester.test_mongodb_replication(mock_clients)
            results["postgresql_replication"] = await replication_tester.test_postgresql_replication(mock_clients)
            results["redis_replication"] = await replication_tester.test_redis_replication(mock_clients)
        
        finally:
            await self.cleanup_mock_clients(mock_clients)
        
        return results
    
    async def run_failover_tests(self):
        """Run failover procedure tests"""
        results = {}
        
        mock_clients = await self.create_mock_clients()
        
        try:
            failover_tester = TestFailoverProcedures()
            results["service_failover"] = await failover_tester.test_service_failover(mock_clients)
            results["database_failover"] = await failover_tester.test_database_failover(mock_clients)
        
        finally:
            await self.cleanup_mock_clients(mock_clients)
        
        return results
    
    async def run_rto_rpo_tests(self):
        """Run RTO/RPO compliance tests"""
        results = {}
        
        mock_clients = await self.create_mock_clients()
        
        try:
            rto_rpo_tester = TestRTORPOCompliance()
            results["rto_compliance"] = await rto_rpo_tester.test_rto_compliance(mock_clients)
            results["rpo_compliance"] = await rto_rpo_tester.test_rpo_compliance(mock_clients)
        
        finally:
            await self.cleanup_mock_clients(mock_clients)
        
        return results
    
    async def run_complete_dr_drill(self):
        """Run complete disaster recovery drill"""
        results = {}
        
        mock_clients = await self.create_mock_clients()
        
        try:
            drill_tester = TestDisasterRecoveryDrills()
            results["complete_drill"] = await drill_tester.test_complete_dr_drill(mock_clients)
            results["lessons_learned"] = await drill_tester.test_lessons_learned_documentation(mock_clients)
        
        finally:
            await self.cleanup_mock_clients(mock_clients)
        
        return results
    
    async def run_integration_tests(self):
        """Run integration disaster recovery tests"""
        results = {}
        
        mock_clients = await self.create_mock_clients()
        
        try:
            integration_tester = TestIntegratedDisasterRecovery()
            results["end_to_end_dr"] = await integration_tester.test_end_to_end_disaster_recovery(mock_clients)
        
        finally:
            await self.cleanup_mock_clients(mock_clients)
        
        return results
    
    async def create_mock_clients(self):
        """Create mock clients for testing"""
        # In a real scenario, these would be actual database connections
        # For testing, we'll create mock objects
        
        class MockClient:
            def __init__(self, client_type):
                self.client_type = client_type
            
            async def close(self):
                pass
            
            def close(self):
                pass
        
        class MockHTTPSession:
            async def get(self, url, **kwargs):
                class MockResponse:
                    status = 200
                    headers = {"X-Response-Time": "50ms"}
                return MockResponse()
            
            async def close(self):
                pass
        
        return {
            'http': MockHTTPSession(),
            'primary_mongodb': MockClient('mongodb'),
            'secondary_mongodb': MockClient('mongodb'),
            'restore_mongodb': MockClient('mongodb'),
            'primary_postgresql': MockClient('postgresql'),
            'secondary_postgresql': MockClient('postgresql'),
            'primary_redis': MockClient('redis'),
            'secondary_redis': MockClient('redis'),
            'restore_redis': MockClient('redis'),
            'docker': MockClient('docker')
        }
    
    async def cleanup_mock_clients(self, clients):
        """Cleanup mock clients"""
        for client in clients.values():
            if hasattr(client, 'close'):
                if asyncio.iscoroutinefunction(client.close):
                    await client.close()
                else:
                    client.close()
    
    async def generate_final_report(self):
        """Generate comprehensive test report"""
        total_time = self.end_time - self.start_time
        
        # Calculate test statistics
        total_categories = len(self.test_results)
        passed_categories = sum(1 for result in self.test_results.values() if result["status"] == "PASSED")
        failed_categories = total_categories - passed_categories
        
        success_rate = (passed_categories / total_categories) * 100 if total_categories > 0 else 0
        
        # Generate report
        report = {
            "test_run_info": {
                "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
                "end_time": datetime.fromtimestamp(self.end_time).isoformat(),
                "total_duration_seconds": total_time,
                "test_runner": "DisasterRecoveryTestRunner"
            },
            "test_statistics": {
                "total_categories": total_categories,
                "passed_categories": passed_categories,
                "failed_categories": failed_categories,
                "success_rate_percent": success_rate
            },
            "test_results": self.test_results,
            "overall_status": "PASSED" if failed_categories == 0 else "FAILED",
            "dr_readiness": {
                "ready_for_production": success_rate >= 80,
                "readiness_score": success_rate,
                "critical_issues": failed_categories,
                "recommendations": self.generate_recommendations()
            }
        }
        
        # Save report
        report_file = f"dr_test_report_{int(time.time())}.json"
        report_path = Path(__file__).parent / report_file
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print(f"\n{'='*80}")
        print("DISASTER RECOVERY TEST SUMMARY")
        print(f"{'='*80}")
        print(f"Total Test Categories: {total_categories}")
        print(f"Passed: {passed_categories}")
        print(f"Failed: {failed_categories}")
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"Total Duration: {total_time:.2f} seconds")
        print(f"Overall Status: {report['overall_status']}")
        print(f"DR Ready: {'✓ YES' if report['dr_readiness']['ready_for_production'] else '✗ NO'}")
        print(f"Report saved to: {report_path}")
        print(f"{'='*80}")
        
        if report["dr_readiness"]["recommendations"]:
            print("\nRECOMMENDATIONS:")
            for i, rec in enumerate(report["dr_readiness"]["recommendations"], 1):
                print(f"  {i}. {rec}")
            print()
        
        return report
    
    def generate_recommendations(self):
        """Generate recommendations based on test results"""
        recommendations = []
        
        failed_tests = [
            category for category, result in self.test_results.items()
            if result["status"] == "FAILED"
        ]
        
        if "Backup and Restore Procedures" in failed_tests:
            recommendations.append("Implement and test automated backup procedures")
        
        if "Data Replication Tests" in failed_tests:
            recommendations.append("Configure and validate data replication between regions")
        
        if "Failover Procedures" in failed_tests:
            recommendations.append("Implement and test automated failover procedures")
        
        if "RTO/RPO Compliance" in failed_tests:
            recommendations.append("Optimize recovery procedures to meet RTO/RPO requirements")
        
        if "Complete DR Drill" in failed_tests:
            recommendations.append("Conduct regular disaster recovery drills and document lessons learned")
        
        if "Integration Tests" in failed_tests:
            recommendations.append("Ensure all DR components work together in integrated scenarios")
        
        if not recommendations:
            recommendations.append("All disaster recovery tests passed - maintain current procedures")
        
        return recommendations


async def main():
    """Main test runner function"""
    runner = DisasterRecoveryTestRunner()
    
    try:
        await runner.run_all_tests()
        
        # Return appropriate exit code
        failed_categories = sum(
            1 for result in runner.test_results.values()
            if result["status"] == "FAILED"
        )
        
        sys.exit(0 if failed_categories == 0 else 1)
    
    except Exception as e:
        print(f"Test runner failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())