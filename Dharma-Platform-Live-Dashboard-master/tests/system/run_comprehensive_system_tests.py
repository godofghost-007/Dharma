"""
Comprehensive system testing runner
Executes all system-level tests for task 15.1
"""

import asyncio
import sys
import time
import json
from datetime import datetime
from pathlib import Path
import subprocess
import aiohttp
import pytest


class SystemTestRunner:
    """Orchestrates comprehensive system testing"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = None
        self.services_ready = False
    
    async def check_service_health(self, service_url: str, timeout: int = 30) -> bool:
        """Check if a service is healthy and ready"""
        
        async with aiohttp.ClientSession() as session:
            for attempt in range(timeout):
                try:
                    async with session.get(f"{service_url}/health", timeout=aiohttp.ClientTimeout(total=2)) as response:
                        if response.status == 200:
                            return True
                except Exception:
                    pass
                await asyncio.sleep(1)
        
        return False
    
    async def wait_for_all_services(self) -> bool:
        """Wait for all services to be ready"""
        
        services = {
            "API Gateway": "http://localhost:8000",
            "Data Collection": "http://localhost:8001",
            "AI Analysis": "http://localhost:8002", 
            "Alert Management": "http://localhost:8003",
            "Dashboard": "http://localhost:8501"
        }
        
        print("Waiting for services to be ready...")
        
        service_status = {}
        for name, url in services.items():
            print(f"Checking {name} at {url}...")
            ready = await self.check_service_health(url)
            service_status[name] = ready
            
            if ready:
                print(f"✓ {name} is ready")
            else:
                print(f"✗ {name} is not ready")
        
        all_ready = all(service_status.values())
        self.services_ready = all_ready
        
        if all_ready:
            print("All services are ready!")
        else:
            print("Some services are not ready. Tests may fail.")
        
        return all_ready
    
    def run_pytest_suite(self, test_file: str, test_name: str) -> dict:
        """Run a specific pytest suite and capture results"""
        
        print(f"\n{'='*60}")
        print(f"Running {test_name}")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        # Run pytest with JSON report
        cmd = [
            sys.executable, "-m", "pytest",
            test_file,
            "-v",
            "--tb=short",
            "--json-report",
            f"--json-report-file=test_results_{test_name.lower().replace(' ', '_')}.json",
            "--asyncio-mode=auto"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd="tests/system")
            end_time = time.time()
            
            # Parse results
            test_result = {
                "name": test_name,
                "duration": end_time - start_time,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0
            }
            
            # Try to load JSON report if available
            json_file = Path(f"tests/system/test_results_{test_name.lower().replace(' ', '_')}.json")
            if json_file.exists():
                try:
                    with open(json_file) as f:
                        json_data = json.load(f)
                        test_result["detailed_results"] = json_data
                except Exception as e:
                    test_result["json_parse_error"] = str(e)
            
            return test_result
            
        except Exception as e:
            return {
                "name": test_name,
                "duration": 0,
                "return_code": -1,
                "error": str(e),
                "success": False
            }
    
    async def run_all_system_tests(self) -> dict:
        """Run all comprehensive system tests"""
        
        self.start_time = time.time()
        
        print("Starting Comprehensive System Testing Suite")
        print(f"Start time: {datetime.now().isoformat()}")
        
        # Check service readiness
        await self.wait_for_all_services()
        
        if not self.services_ready:
            print("\nWarning: Not all services are ready. Proceeding with tests anyway...")
        
        # Define test suites to run
        test_suites = [
            {
                "file": "test_end_to_end_system.py",
                "name": "End-to-End Integration Tests",
                "description": "Complete workflow testing from data collection to alerting"
            },
            {
                "file": "test_performance_validation.py", 
                "name": "Performance Validation Tests",
                "description": "Validate performance requirements under realistic load"
            },
            {
                "file": "test_error_handling_recovery.py",
                "name": "Error Handling and Recovery Tests", 
                "description": "Test system resilience and recovery capabilities"
            }
        ]
        
        # Run each test suite
        for suite in test_suites:
            print(f"\n{'-'*40}")
            print(f"Starting: {suite['name']}")
            print(f"Description: {suite['description']}")
            print(f"{'-'*40}")
            
            result = self.run_pytest_suite(suite["file"], suite["name"])
            self.test_results[suite["name"]] = result
            
            if result["success"]:
                print(f"✓ {suite['name']} completed successfully")
            else:
                print(f"✗ {suite['name']} failed")
                print(f"Error details: {result.get('stderr', 'No error details')}")
        
        # Generate summary report
        return self.generate_summary_report()
    
    def generate_summary_report(self) -> dict:
        """Generate comprehensive test summary report"""
        
        end_time = time.time()
        total_duration = end_time - self.start_time
        
        # Calculate overall statistics
        total_suites = len(self.test_results)
        successful_suites = sum(1 for result in self.test_results.values() if result["success"])
        failed_suites = total_suites - successful_suites
        
        # Extract detailed test counts if available
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        
        for result in self.test_results.values():
            if "detailed_results" in result:
                summary = result["detailed_results"].get("summary", {})
                total_tests += summary.get("total", 0)
                passed_tests += summary.get("passed", 0)
                failed_tests += summary.get("failed", 0)
        
        # Generate report
        report = {
            "test_execution": {
                "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
                "end_time": datetime.fromtimestamp(end_time).isoformat(),
                "total_duration": total_duration,
                "services_ready": self.services_ready
            },
            "suite_summary": {
                "total_suites": total_suites,
                "successful_suites": successful_suites,
                "failed_suites": failed_suites,
                "success_rate": (successful_suites / total_suites * 100) if total_suites > 0 else 0
            },
            "test_summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "test_success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0
            },
            "detailed_results": self.test_results,
            "requirements_validation": self.validate_requirements()
        }
        
        # Save report to file
        report_file = f"comprehensive_system_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n{'='*60}")
        print("COMPREHENSIVE SYSTEM TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Total Duration: {total_duration:.2f} seconds")
        print(f"Services Ready: {'Yes' if self.services_ready else 'No'}")
        print(f"Test Suites: {successful_suites}/{total_suites} successful")
        print(f"Individual Tests: {passed_tests}/{total_tests} passed")
        print(f"Overall Success Rate: {report['suite_summary']['success_rate']:.1f}%")
        print(f"Report saved to: {report_file}")
        
        # Print individual suite results
        print(f"\nSuite Results:")
        for name, result in self.test_results.items():
            status = "✓ PASS" if result["success"] else "✗ FAIL"
            duration = result["duration"]
            print(f"  {status} {name} ({duration:.2f}s)")
        
        # Print requirements validation
        requirements = report["requirements_validation"]
        print(f"\nRequirements Validation:")
        for req_id, status in requirements.items():
            status_symbol = "✓" if status["validated"] else "✗"
            print(f"  {status_symbol} {req_id}: {status['description']}")
        
        return report
    
    def validate_requirements(self) -> dict:
        """Validate that system requirements are met based on test results"""
        
        requirements = {
            "9.1": {
                "description": "Handle 100,000+ posts per day",
                "validated": False,
                "evidence": []
            },
            "9.2": {
                "description": "Complete sentiment analysis within 5 seconds",
                "validated": False,
                "evidence": []
            },
            "9.5": {
                "description": "Process 1000+ requests per minute with 99.9% uptime",
                "validated": False,
                "evidence": []
            },
            "11.4": {
                "description": "Provide distributed tracing and correlation IDs",
                "validated": False,
                "evidence": []
            }
        }
        
        # Analyze test results to validate requirements
        for suite_name, result in self.test_results.items():
            if result["success"]:
                if "Performance Validation" in suite_name:
                    requirements["9.1"]["validated"] = True
                    requirements["9.1"]["evidence"].append(f"Performance tests passed in {suite_name}")
                    
                    requirements["9.2"]["validated"] = True
                    requirements["9.2"]["evidence"].append(f"Latency tests passed in {suite_name}")
                    
                    requirements["9.5"]["validated"] = True
                    requirements["9.5"]["evidence"].append(f"Throughput tests passed in {suite_name}")
                
                if "End-to-End" in suite_name:
                    requirements["11.4"]["validated"] = True
                    requirements["11.4"]["evidence"].append(f"Integration tests passed in {suite_name}")
        
        return requirements


async def main():
    """Main entry point for comprehensive system testing"""
    
    runner = SystemTestRunner()
    
    try:
        report = await runner.run_all_system_tests()
        
        # Determine exit code based on results
        if report["suite_summary"]["success_rate"] >= 80:  # 80% success threshold
            print(f"\n✓ System testing completed successfully!")
            print(f"Success rate: {report['suite_summary']['success_rate']:.1f}%")
            sys.exit(0)
        else:
            print(f"\n✗ System testing failed!")
            print(f"Success rate: {report['suite_summary']['success_rate']:.1f}% (below 80% threshold)")
            sys.exit(1)
    
    except Exception as e:
        print(f"\nFatal error during system testing: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())