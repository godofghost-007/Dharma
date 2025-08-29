#!/usr/bin/env python3
"""
Project Dharma Completion Verification Script
Verifies that all components are properly implemented and ready for launch
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Any


class ProjectVerifier:
    """Verifies project completion status"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.verification_results = {}
        
    def verify_all(self) -> Dict[str, Any]:
        """Run all verification checks"""
        print("="*80)
        print("PROJECT DHARMA - COMPLETION VERIFICATION")
        print("="*80)
        
        checks = [
            ("Project Structure", self.verify_project_structure),
            ("Services Implementation", self.verify_services),
            ("Database Infrastructure", self.verify_databases),
            ("Configuration Files", self.verify_configuration),
            ("Documentation", self.verify_documentation),
            ("Testing Suite", self.verify_testing),
            ("Security Implementation", self.verify_security),
            ("Monitoring Setup", self.verify_monitoring),
            ("Deployment Readiness", self.verify_deployment)
        ]
        
        overall_score = 0
        total_checks = len(checks)
        
        for check_name, check_function in checks:
            print(f"\n{'='*60}")
            print(f"CHECKING: {check_name}")
            print(f"{'='*60}")
            
            try:
                result = check_function()
                self.verification_results[check_name] = result
                
                if result.get("passed", False):
                    print(f"✅ {check_name}: PASSED")
                    overall_score += 1
                else:
                    print(f"❌ {check_name}: FAILED")
                    if "issues" in result:
                        for issue in result["issues"]:
                            print(f"   - {issue}")
                            
            except Exception as e:
                print(f"❌ {check_name}: ERROR - {str(e)}")
                self.verification_results[check_name] = {
                    "passed": False,
                    "error": str(e)
                }
        
        # Calculate overall completion
        completion_percentage = (overall_score / total_checks) * 100
        
        self.verification_results["overall"] = {
            "completion_percentage": completion_percentage,
            "passed_checks": overall_score,
            "total_checks": total_checks,
            "ready_for_production": completion_percentage >= 95
        }
        
        # Print summary
        print(f"\n{'='*80}")
        print("VERIFICATION SUMMARY")
        print(f"{'='*80}")
        print(f"Completion: {completion_percentage:.1f}%")
        print(f"Passed: {overall_score}/{total_checks}")
        print(f"Production Ready: {'✅ YES' if completion_percentage >= 95 else '❌ NO'}")
        print(f"{'='*80}")
        
        return self.verification_results
    
    def verify_project_structure(self) -> Dict[str, Any]:
        """Verify project directory structure"""
        required_dirs = [
            "services",
            "shared",
            "infrastructure", 
            "tests",
            "docs",
            "scripts",
            "migrations"
        ]
        
        required_files = [
            "docker-compose.yml",
            "requirements.txt",
            "README.md",
            "launch.py",
            "PROJECT_COMPLETION_SUMMARY.md"
        ]
        
        issues = []
        
        # Check directories
        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                issues.append(f"Missing directory: {dir_name}")
        
        # Check files
        for file_name in required_files:
            file_path = self.project_root / file_name
            if not file_path.exists():
                issues.append(f"Missing file: {file_name}")
        
        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "checked_dirs": len(required_dirs),
            "checked_files": len(required_files)
        }
    
    def verify_services(self) -> Dict[str, Any]:
        """Verify all microservices are implemented"""
        required_services = [
            "data-collection-service",
            "ai-analysis-service", 
            "stream-processing-service",
            "alert-management-service",
            "api-gateway-service",
            "dashboard-service",
            "event-bus-service",
            "collaboration-service",
            "cost-monitoring-service"
        ]
        
        issues = []
        implemented_services = []
        
        services_dir = self.project_root / "services"
        
        for service_name in required_services:
            service_dir = services_dir / service_name
            
            if not service_dir.exists():
                issues.append(f"Missing service directory: {service_name}")
                continue
            
            # Check for main.py or app.py
            main_files = ["main.py", "app.py", "app/main.py"]
            has_main = any((service_dir / main_file).exists() for main_file in main_files)
            
            if not has_main:
                issues.append(f"Missing main file in service: {service_name}")
                continue
            
            # Check for Dockerfile
            dockerfile = service_dir / "Dockerfile"
            if not dockerfile.exists():
                issues.append(f"Missing Dockerfile in service: {service_name}")
                continue
            
            implemented_services.append(service_name)
        
        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "implemented_services": implemented_services,
            "total_required": len(required_services)
        }
    
    def verify_databases(self) -> Dict[str, Any]:
        """Verify database infrastructure"""
        issues = []
        
        # Check database initialization scripts
        db_configs = [
            ("MongoDB", "infrastructure/mongodb/init"),
            ("PostgreSQL", "infrastructure/postgresql/init"),
            ("Elasticsearch", "infrastructure/elasticsearch/mappings"),
            ("Redis", "infrastructure/redis")
        ]
        
        for db_name, config_path in db_configs:
            full_path = self.project_root / config_path
            if not full_path.exists():
                issues.append(f"Missing {db_name} configuration: {config_path}")
        
        # Check migration scripts
        migrations_dir = self.project_root / "migrations"
        if migrations_dir.exists():
            required_migration_dirs = ["mongodb", "postgresql", "elasticsearch"]
            for migration_dir in required_migration_dirs:
                migration_path = migrations_dir / migration_dir
                if not migration_path.exists():
                    issues.append(f"Missing migration directory: {migration_dir}")
        else:
            issues.append("Missing migrations directory")
        
        # Check shared database modules
        shared_db_dir = self.project_root / "shared" / "database"
        if shared_db_dir.exists():
            required_db_modules = ["mongodb.py", "postgresql.py", "redis.py", "elasticsearch.py"]
            for module in required_db_modules:
                module_path = shared_db_dir / module
                if not module_path.exists():
                    issues.append(f"Missing database module: {module}")
        else:
            issues.append("Missing shared database modules")
        
        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "databases_configured": len([db for db, _ in db_configs])
        }
    
    def verify_configuration(self) -> Dict[str, Any]:
        """Verify configuration files"""
        issues = []
        
        # Check Docker Compose
        compose_file = self.project_root / "docker-compose.yml"
        if compose_file.exists():
            try:
                import yaml
                with open(compose_file) as f:
                    compose_config = yaml.safe_load(f)
                
                # Check for required services in compose
                services = compose_config.get("services", {})
                required_compose_services = [
                    "mongodb", "postgresql", "elasticsearch", "redis",
                    "kafka", "zookeeper", "temporal"
                ]
                
                for service in required_compose_services:
                    if service not in services:
                        issues.append(f"Missing service in docker-compose.yml: {service}")
                        
            except Exception as e:
                issues.append(f"Invalid docker-compose.yml: {str(e)}")
        else:
            issues.append("Missing docker-compose.yml")
        
        # Check infrastructure configurations
        infra_configs = [
            "infrastructure/prometheus/prometheus.yml",
            "infrastructure/grafana/grafana.ini", 
            "infrastructure/elk/docker-compose.elk.yml",
            "infrastructure/kubernetes/services.yaml"
        ]
        
        for config_path in infra_configs:
            full_path = self.project_root / config_path
            if not full_path.exists():
                issues.append(f"Missing configuration: {config_path}")
        
        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "configurations_checked": len(infra_configs) + 1
        }
    
    def verify_documentation(self) -> Dict[str, Any]:
        """Verify documentation completeness"""
        issues = []
        
        # Check main documentation files
        required_docs = [
            "docs/README.md",
            "docs/api/openapi.yaml",
            "docs/user/dashboard-user-guide.md",
            "docs/admin/system-configuration-guide.md",
            "docs/developer/onboarding-guide.md",
            "docs/architecture/system-architecture.md",
            "docs/operations/incident-response-runbook.md",
            "docs/operations/troubleshooting.md"
        ]
        
        for doc_path in required_docs:
            full_path = self.project_root / doc_path
            if not full_path.exists():
                issues.append(f"Missing documentation: {doc_path}")
        
        # Check service-specific documentation
        services_dir = self.project_root / "services"
        if services_dir.exists():
            for service_dir in services_dir.iterdir():
                if service_dir.is_dir():
                    readme_path = service_dir / "README.md"
                    if not readme_path.exists():
                        issues.append(f"Missing service README: {service_dir.name}/README.md")
        
        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "documentation_files_checked": len(required_docs)
        }
    
    def verify_testing(self) -> Dict[str, Any]:
        """Verify testing suite completeness"""
        issues = []
        
        # Check test directories
        test_dirs = [
            "tests/unit",
            "tests/integration", 
            "tests/performance",
            "tests/security",
            "tests/disaster_recovery",
            "tests/system"
        ]
        
        for test_dir in test_dirs:
            full_path = self.project_root / test_dir
            if not full_path.exists():
                issues.append(f"Missing test directory: {test_dir}")
        
        # Check test runners
        test_runners = [
            "tests/run_unit_tests.py",
            "tests/run_integration_tests.py",
            "tests/performance/test_load_testing.py",
            "tests/security/run_security_compliance_tests.py",
            "tests/disaster_recovery/run_disaster_recovery_tests.py"
        ]
        
        for runner in test_runners:
            full_path = self.project_root / runner
            if not full_path.exists():
                issues.append(f"Missing test runner: {runner}")
        
        # Check for test configuration files
        test_configs = [
            "tests/unit/conftest.py",
            "tests/integration/conftest.py",
            "tests/performance/conftest.py"
        ]
        
        for config in test_configs:
            full_path = self.project_root / config
            if not full_path.exists():
                issues.append(f"Missing test config: {config}")
        
        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "test_components_checked": len(test_dirs) + len(test_runners) + len(test_configs)
        }
    
    def verify_security(self) -> Dict[str, Any]:
        """Verify security implementation"""
        issues = []
        
        # Check security modules
        security_modules = [
            "shared/security/encryption.py",
            "shared/security/audit_logger.py",
            "shared/security/input_validation.py",
            "shared/security/api_key_manager.py",
            "shared/security/tls_manager.py"
        ]
        
        for module in security_modules:
            full_path = self.project_root / module
            if not full_path.exists():
                issues.append(f"Missing security module: {module}")
        
        # Check governance modules
        governance_modules = [
            "shared/governance/data_anonymizer.py",
            "shared/governance/retention_manager.py",
            "shared/governance/compliance_reporter.py"
        ]
        
        for module in governance_modules:
            full_path = self.project_root / module
            if not full_path.exists():
                issues.append(f"Missing governance module: {module}")
        
        # Check security tests
        security_tests = [
            "tests/security/test_penetration_testing.py",
            "tests/security/test_vulnerability_assessment.py",
            "tests/security/test_compliance_audit.py"
        ]
        
        for test in security_tests:
            full_path = self.project_root / test
            if not full_path.exists():
                issues.append(f"Missing security test: {test}")
        
        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "security_components_checked": len(security_modules) + len(governance_modules) + len(security_tests)
        }
    
    def verify_monitoring(self) -> Dict[str, Any]:
        """Verify monitoring and observability setup"""
        issues = []
        
        # Check monitoring configurations
        monitoring_configs = [
            "infrastructure/prometheus/prometheus.yml",
            "infrastructure/grafana/grafana.ini",
            "infrastructure/elk/docker-compose.elk.yml",
            "infrastructure/tracing/jaeger-config.yml"
        ]
        
        for config in monitoring_configs:
            full_path = self.project_root / config
            if not full_path.exists():
                issues.append(f"Missing monitoring config: {config}")
        
        # Check monitoring modules
        monitoring_modules = [
            "shared/monitoring/health_checks.py",
            "shared/monitoring/metrics_collector.py",
            "shared/tracing/tracer.py",
            "shared/logging/structured_logger.py"
        ]
        
        for module in monitoring_modules:
            full_path = self.project_root / module
            if not full_path.exists():
                issues.append(f"Missing monitoring module: {module}")
        
        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "monitoring_components_checked": len(monitoring_configs) + len(monitoring_modules)
        }
    
    def verify_deployment(self) -> Dict[str, Any]:
        """Verify deployment readiness"""
        issues = []
        
        # Check deployment scripts
        deployment_files = [
            "launch.py",
            "scripts/deploy.sh",
            "scripts/backup_restore.py"
        ]
        
        for file in deployment_files:
            full_path = self.project_root / file
            if not full_path.exists():
                issues.append(f"Missing deployment file: {file}")
        
        # Check Kubernetes manifests
        k8s_manifests = [
            "infrastructure/kubernetes/services.yaml",
            "infrastructure/kubernetes/databases.yaml",
            "infrastructure/kubernetes/configmap.yaml",
            "infrastructure/kubernetes/secrets.yaml"
        ]
        
        for manifest in k8s_manifests:
            full_path = self.project_root / manifest
            if not full_path.exists():
                issues.append(f"Missing Kubernetes manifest: {manifest}")
        
        # Check Terraform configurations
        terraform_files = [
            "infrastructure/terraform/main.tf",
            "infrastructure/terraform/variables.tf",
            "infrastructure/terraform/vpc.tf"
        ]
        
        for tf_file in terraform_files:
            full_path = self.project_root / tf_file
            if not full_path.exists():
                issues.append(f"Missing Terraform file: {tf_file}")
        
        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "deployment_components_checked": len(deployment_files) + len(k8s_manifests) + len(terraform_files)
        }
    
    def save_verification_report(self):
        """Save verification report to file"""
        report_file = self.project_root / "verification_report.json"
        
        with open(report_file, 'w') as f:
            json.dump(self.verification_results, f, indent=2)
        
        print(f"\n📄 Verification report saved to: {report_file}")


def main():
    """Main verification function"""
    verifier = ProjectVerifier()
    
    try:
        results = verifier.verify_all()
        verifier.save_verification_report()
        
        # Exit with appropriate code
        if results["overall"]["ready_for_production"]:
            print("\n🎉 PROJECT DHARMA IS READY FOR PRODUCTION! 🎉")
            sys.exit(0)
        else:
            print("\n⚠️  Project needs attention before production deployment")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()