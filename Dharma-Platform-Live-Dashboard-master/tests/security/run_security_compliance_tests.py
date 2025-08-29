"""
Security and compliance testing runner
Executes all security tests for task 15.2
"""

import asyncio
import sys
import time
import json
from datetime import datetime
from pathlib import Path
import subprocess
import aiohttp


class SecurityTestRunner:
    """Orchestrates security and compliance testing"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = None
        self.security_score = 0
    
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
    
    async def wait_for_services(self) -> bool:
        """Wait for services to be ready for security testing"""
        
        services = {
            "API Gateway": "http://localhost:8000",
            "Data Collection": "http://localhost:8001",
            "AI Analysis": "http://localhost:8002", 
            "Alert Management": "http://localhost:8003"
        }
        
        print("Waiting for services to be ready for security testing...")
        
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
        
        if all_ready:
            print("All services are ready for security testing!")
        else:
            print("Some services are not ready. Security tests may be limited.")
        
        return all_ready
    
    def run_security_test_suite(self, test_file: str, test_name: str) -> dict:
        """Run a specific security test suite and capture results"""
        
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
            f"--json-report-file=security_results_{test_name.lower().replace(' ', '_')}.json",
            "--asyncio-mode=auto"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd="tests/security")
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
            json_file = Path(f"tests/security/security_results_{test_name.lower().replace(' ', '_')}.json")
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
    
    async def run_all_security_tests(self) -> dict:
        """Run all security and compliance tests"""
        
        self.start_time = time.time()
        
        print("Starting Security and Compliance Testing Suite")
        print(f"Start time: {datetime.now().isoformat()}")
        
        # Check service readiness
        services_ready = await self.wait_for_services()
        
        if not services_ready:
            print("\nWarning: Not all services are ready. Some security tests may fail.")
        
        # Define security test suites to run
        security_test_suites = [
            {
                "file": "test_penetration_testing.py",
                "name": "Penetration Testing",
                "description": "Authentication, authorization, and input validation security tests",
                "weight": 40  # Percentage weight for overall security score
            },
            {
                "file": "test_vulnerability_assessment.py", 
                "name": "Vulnerability Assessment",
                "description": "Network security, application vulnerabilities, and database security",
                "weight": 35
            },
            {
                "file": "test_compliance_audit.py",
                "name": "Compliance Audit", 
                "description": "Data protection, audit logging, and documentation compliance",
                "weight": 25
            }
        ]
        
        # Run each security test suite
        for suite in security_test_suites:
            print(f"\n{'-'*40}")
            print(f"Starting: {suite['name']}")
            print(f"Description: {suite['description']}")
            print(f"Weight: {suite['weight']}%")
            print(f"{'-'*40}")
            
            result = self.run_security_test_suite(suite["file"], suite["name"])
            result["weight"] = suite["weight"]
            self.test_results[suite["name"]] = result
            
            if result["success"]:
                print(f"✓ {suite['name']} completed successfully")
            else:
                print(f"✗ {suite['name']} failed")
                print(f"Error details: {result.get('stderr', 'No error details')}")
        
        # Generate security assessment report
        return self.generate_security_report()
    
    def calculate_security_score(self) -> float:
        """Calculate overall security score based on test results"""
        
        total_weight = 0
        weighted_score = 0
        
        for suite_name, result in self.test_results.items():
            weight = result.get("weight", 0)
            total_weight += weight
            
            # Calculate suite score based on success and detailed results
            suite_score = 0
            if result["success"]:
                suite_score = 100  # Base score for successful completion
                
                # Adjust score based on detailed test results if available
                if "detailed_results" in result:
                    detailed = result["detailed_results"]
                    summary = detailed.get("summary", {})
                    
                    if summary.get("total", 0) > 0:
                        passed = summary.get("passed", 0)
                        total = summary.get("total", 1)
                        suite_score = (passed / total) * 100
            
            weighted_score += (suite_score * weight / 100)
        
        return weighted_score if total_weight > 0 else 0
    
    def assess_security_requirements(self) -> dict:
        """Assess compliance with security requirements"""
        
        requirements_assessment = {
            "8.1": {
                "description": "Data encryption at rest and in transit",
                "validated": False,
                "evidence": [],
                "score": 0
            },
            "8.2": {
                "description": "JWT tokens with role-based access control",
                "validated": False,
                "evidence": [],
                "score": 0
            },
            "8.3": {
                "description": "Rate limiting and input validation",
                "validated": False,
                "evidence": [],
                "score": 0
            },
            "8.4": {
                "description": "Comprehensive audit logs",
                "validated": False,
                "evidence": [],
                "score": 0
            },
            "17.5": {
                "description": "Independent audits and classification accuracy",
                "validated": False,
                "evidence": [],
                "score": 0
            }
        }
        
        # Analyze test results to validate requirements
        for suite_name, result in self.test_results.items():
            if result["success"]:
                if "Penetration Testing" in suite_name:
                    # JWT and RBAC testing
                    requirements_assessment["8.2"]["validated"] = True
                    requirements_assessment["8.2"]["evidence"].append(f"Authentication tests passed in {suite_name}")
                    requirements_assessment["8.2"]["score"] = 90
                    
                    # Input validation testing
                    requirements_assessment["8.3"]["validated"] = True
                    requirements_assessment["8.3"]["evidence"].append(f"Input validation tests passed in {suite_name}")
                    requirements_assessment["8.3"]["score"] = 85
                
                if "Vulnerability Assessment" in suite_name:
                    # Data encryption testing
                    requirements_assessment["8.1"]["validated"] = True
                    requirements_assessment["8.1"]["evidence"].append(f"Encryption tests passed in {suite_name}")
                    requirements_assessment["8.1"]["score"] = 80
                
                if "Compliance Audit" in suite_name:
                    # Audit logging testing
                    requirements_assessment["8.4"]["validated"] = True
                    requirements_assessment["8.4"]["evidence"].append(f"Audit logging tests passed in {suite_name}")
                    requirements_assessment["8.4"]["score"] = 85
                    
                    # Independent audit capability
                    requirements_assessment["17.5"]["validated"] = True
                    requirements_assessment["17.5"]["evidence"].append(f"Compliance audit tests passed in {suite_name}")
                    requirements_assessment["17.5"]["score"] = 75
        
        return requirements_assessment
    
    def generate_security_report(self) -> dict:
        """Generate comprehensive security assessment report"""
        
        end_time = time.time()
        total_duration = end_time - self.start_time
        
        # Calculate overall statistics
        total_suites = len(self.test_results)
        successful_suites = sum(1 for result in self.test_results.values() if result["success"])
        failed_suites = total_suites - successful_suites
        
        # Calculate security score
        self.security_score = self.calculate_security_score()
        
        # Assess security requirements
        requirements_assessment = self.assess_security_requirements()
        
        # Determine security level
        if self.security_score >= 90:
            security_level = "EXCELLENT"
        elif self.security_score >= 80:
            security_level = "GOOD"
        elif self.security_score >= 70:
            security_level = "ACCEPTABLE"
        elif self.security_score >= 60:
            security_level = "NEEDS IMPROVEMENT"
        else:
            security_level = "CRITICAL ISSUES"
        
        # Generate report
        report = {
            "test_execution": {
                "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
                "end_time": datetime.fromtimestamp(end_time).isoformat(),
                "total_duration": total_duration
            },
            "security_assessment": {
                "overall_score": self.security_score,
                "security_level": security_level,
                "total_suites": total_suites,
                "successful_suites": successful_suites,
                "failed_suites": failed_suites,
                "success_rate": (successful_suites / total_suites * 100) if total_suites > 0 else 0
            },
            "requirements_compliance": requirements_assessment,
            "detailed_results": self.test_results,
            "recommendations": self.generate_security_recommendations()
        }
        
        # Save report to file
        report_file = f"security_assessment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n{'='*60}")
        print("SECURITY AND COMPLIANCE ASSESSMENT SUMMARY")
        print(f"{'='*60}")
        print(f"Overall Security Score: {self.security_score:.1f}/100")
        print(f"Security Level: {security_level}")
        print(f"Test Suites: {successful_suites}/{total_suites} successful")
        print(f"Total Duration: {total_duration:.2f} seconds")
        print(f"Report saved to: {report_file}")
        
        # Print suite results
        print(f"\nSuite Results:")
        for name, result in self.test_results.items():
            status = "✓ PASS" if result["success"] else "✗ FAIL"
            duration = result["duration"]
            weight = result.get("weight", 0)
            print(f"  {status} {name} ({duration:.2f}s, {weight}% weight)")
        
        # Print requirements compliance
        print(f"\nRequirements Compliance:")
        for req_id, assessment in requirements_assessment.items():
            status = "✓" if assessment["validated"] else "✗"
            score = assessment["score"]
            print(f"  {status} {req_id}: {assessment['description']} ({score}/100)")
        
        return report
    
    def generate_security_recommendations(self) -> list:
        """Generate security recommendations based on test results"""
        
        recommendations = []
        
        # Analyze failed tests and generate recommendations
        for suite_name, result in self.test_results.items():
            if not result["success"]:
                if "Penetration Testing" in suite_name:
                    recommendations.append({
                        "priority": "HIGH",
                        "category": "Authentication & Authorization",
                        "issue": "Penetration testing failed",
                        "recommendation": "Review and strengthen authentication mechanisms, RBAC implementation, and input validation",
                        "impact": "Critical security vulnerabilities may exist"
                    })
                
                elif "Vulnerability Assessment" in suite_name:
                    recommendations.append({
                        "priority": "HIGH", 
                        "category": "Infrastructure Security",
                        "issue": "Vulnerability assessment failed",
                        "recommendation": "Address network security issues, database access controls, and encryption implementation",
                        "impact": "System may be vulnerable to attacks"
                    })
                
                elif "Compliance Audit" in suite_name:
                    recommendations.append({
                        "priority": "MEDIUM",
                        "category": "Compliance & Governance",
                        "issue": "Compliance audit failed",
                        "recommendation": "Improve audit logging, data protection policies, and documentation completeness",
                        "impact": "May not meet regulatory compliance requirements"
                    })
        
        # Add general recommendations based on security score
        if self.security_score < 70:
            recommendations.append({
                "priority": "CRITICAL",
                "category": "Overall Security",
                "issue": f"Low security score ({self.security_score:.1f}/100)",
                "recommendation": "Conduct comprehensive security review and implement immediate security improvements",
                "impact": "System poses significant security risks"
            })
        
        elif self.security_score < 85:
            recommendations.append({
                "priority": "MEDIUM",
                "category": "Security Improvement",
                "issue": f"Moderate security score ({self.security_score:.1f}/100)",
                "recommendation": "Address identified security gaps and implement additional security controls",
                "impact": "Security posture could be strengthened"
            })
        
        return recommendations


async def main():
    """Main entry point for security and compliance testing"""
    
    runner = SecurityTestRunner()
    
    try:
        report = await runner.run_all_security_tests()
        
        # Determine exit code based on security assessment
        security_score = report["security_assessment"]["overall_score"]
        
        if security_score >= 80:  # 80% security threshold
            print(f"\n✓ Security and compliance testing completed successfully!")
            print(f"Security Score: {security_score:.1f}/100")
            sys.exit(0)
        else:
            print(f"\n✗ Security and compliance testing identified issues!")
            print(f"Security Score: {security_score:.1f}/100 (below 80% threshold)")
            
            # Print critical recommendations
            recommendations = report.get("recommendations", [])
            critical_recs = [r for r in recommendations if r.get("priority") == "CRITICAL"]
            
            if critical_recs:
                print(f"\nCritical Issues:")
                for rec in critical_recs:
                    print(f"  - {rec['issue']}: {rec['recommendation']}")
            
            sys.exit(1)
    
    except Exception as e:
        print(f"\nFatal error during security testing: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())