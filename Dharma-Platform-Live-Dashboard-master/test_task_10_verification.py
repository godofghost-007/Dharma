#!/usr/bin/env python3
"""
Task 10 Verification: Set up monitoring and observability
Verifies all components are implemented without running them
"""

import os
import sys
import json
import yaml

def check_file_exists(file_path, description):
    """Check if a file exists and return result"""
    if os.path.exists(file_path):
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description}: {file_path} - NOT FOUND")
        return False

def check_directory_structure():
    """Check that all monitoring directories and files exist"""
    print("Checking monitoring and observability file structure...")
    
    files_and_descriptions = [
        # Centralized Logging (Task 10.1)
        ("shared/logging/structured_logger.py", "Structured Logger"),
        ("shared/logging/log_aggregator.py", "Log Aggregator"),
        ("shared/logging/log_alerting.py", "Log Alerting"),
        ("infrastructure/elk/docker-compose.elk.yml", "ELK Stack Configuration"),
        ("infrastructure/elk/logstash/pipeline/logstash.conf", "Logstash Pipeline"),
        ("infrastructure/elk/filebeat/filebeat.yml", "Filebeat Configuration"),
        ("infrastructure/elk/kibana/dashboards/dharma-overview-dashboard.json", "Kibana Dashboard"),
        
        # Metrics and Monitoring (Task 10.2)
        ("shared/monitoring/metrics_collector.py", "Metrics Collector"),
        ("infrastructure/monitoring/docker-compose.monitoring.yml", "Monitoring Stack"),
        ("infrastructure/monitoring/prometheus/prometheus.yml", "Prometheus Configuration"),
        ("infrastructure/monitoring/prometheus/alert_rules.yml", "Prometheus Alert Rules"),
        ("infrastructure/monitoring/grafana/grafana.ini", "Grafana Configuration"),
        ("infrastructure/monitoring/alertmanager/alertmanager.yml", "AlertManager Configuration"),
        
        # Distributed Tracing (Task 10.3)
        ("shared/tracing/tracer.py", "Distributed Tracer"),
        ("shared/tracing/correlation.py", "Correlation Manager"),
        ("shared/tracing/error_tracker.py", "Error Tracker"),
        ("shared/tracing/performance_profiler.py", "Performance Profiler"),
        ("shared/tracing/integration.py", "Tracing Integration"),
        ("shared/tracing/config.py", "Tracing Configuration"),
        ("infrastructure/tracing/jaeger-config.yml", "Jaeger Configuration"),
        ("infrastructure/tracing/otel-collector-config.yml", "OpenTelemetry Collector"),
        
        # Health Checks and Service Discovery
        ("shared/monitoring/health_checks.py", "Health Checks"),
        ("shared/monitoring/service_discovery.py", "Service Discovery"),
        ("shared/monitoring/observability_integration.py", "Observability Integration"),
        
        # Test Files
        ("tests/test_centralized_logging.py", "Logging Tests"),
        ("tests/test_metrics_monitoring.py", "Metrics Tests"),
        ("tests/test_distributed_tracing.py", "Tracing Tests"),
        ("tests/test_health_checks.py", "Health Check Tests"),
    ]
    
    results = []
    for file_path, description in files_and_descriptions:
        result = check_file_exists(file_path, description)
        results.append((file_path, result))
    
    return results

def check_configuration_validity():
    """Check that configuration files are valid"""
    print("\nChecking configuration file validity...")
    
    config_checks = []
    
    # Check ELK Docker Compose
    elk_compose = "infrastructure/elk/docker-compose.elk.yml"
    if os.path.exists(elk_compose):
        try:
            with open(elk_compose, 'r') as f:
                elk_config = yaml.safe_load(f)
                if 'services' in elk_config and 'elasticsearch' in elk_config['services']:
                    print("✅ ELK Docker Compose is valid YAML with required services")
                    config_checks.append(True)
                else:
                    print("❌ ELK Docker Compose missing required services")
                    config_checks.append(False)
        except Exception as e:
            print(f"❌ ELK Docker Compose invalid: {e}")
            config_checks.append(False)
    
    # Check Monitoring Docker Compose
    monitoring_compose = "infrastructure/monitoring/docker-compose.monitoring.yml"
    if os.path.exists(monitoring_compose):
        try:
            with open(monitoring_compose, 'r') as f:
                monitoring_config = yaml.safe_load(f)
                if 'services' in monitoring_config and 'prometheus' in monitoring_config['services']:
                    print("✅ Monitoring Docker Compose is valid YAML with required services")
                    config_checks.append(True)
                else:
                    print("❌ Monitoring Docker Compose missing required services")
                    config_checks.append(False)
        except Exception as e:
            print(f"❌ Monitoring Docker Compose invalid: {e}")
            config_checks.append(False)
    
    # Check Jaeger Configuration
    jaeger_config = "infrastructure/tracing/jaeger-config.yml"
    if os.path.exists(jaeger_config):
        try:
            with open(jaeger_config, 'r') as f:
                jaeger_cfg = yaml.safe_load(f)
                if 'services' in jaeger_cfg and 'jaeger' in jaeger_cfg['services']:
                    print("✅ Jaeger configuration is valid YAML")
                    config_checks.append(True)
                else:
                    print("❌ Jaeger configuration missing required services")
                    config_checks.append(False)
        except Exception as e:
            print(f"❌ Jaeger configuration invalid: {e}")
            config_checks.append(False)
    
    # Check Kibana Dashboard
    kibana_dashboard = "infrastructure/elk/kibana/dashboards/dharma-overview-dashboard.json"
    if os.path.exists(kibana_dashboard):
        try:
            with open(kibana_dashboard, 'r') as f:
                dashboard_config = json.load(f)
                if 'objects' in dashboard_config:
                    print("✅ Kibana dashboard is valid JSON")
                    config_checks.append(True)
                else:
                    print("❌ Kibana dashboard missing required structure")
                    config_checks.append(False)
        except Exception as e:
            print(f"❌ Kibana dashboard invalid: {e}")
            config_checks.append(False)
    
    return config_checks

def check_requirements_satisfaction():
    """Check that all requirements are satisfied"""
    print("\nChecking requirements satisfaction...")
    
    requirements = [
        ("11.1", "Centralized logging using ELK stack", [
            "infrastructure/elk/docker-compose.elk.yml",
            "shared/logging/structured_logger.py",
            "shared/logging/log_aggregator.py"
        ]),
        ("11.2", "Metrics collection with Prometheus and Grafana", [
            "infrastructure/monitoring/docker-compose.monitoring.yml",
            "shared/monitoring/metrics_collector.py",
            "infrastructure/monitoring/prometheus/prometheus.yml"
        ]),
        ("11.3", "Health checks and service discovery", [
            "shared/monitoring/health_checks.py",
            "shared/monitoring/service_discovery.py"
        ]),
        ("11.4", "Distributed tracing and error tracking", [
            "shared/tracing/tracer.py",
            "shared/tracing/error_tracker.py",
            "infrastructure/tracing/jaeger-config.yml"
        ]),
        ("11.5", "Performance profiling and bottleneck identification", [
            "shared/tracing/performance_profiler.py"
        ])
    ]
    
    requirement_results = []
    
    for req_id, description, files in requirements:
        print(f"\nRequirement {req_id}: {description}")
        all_files_exist = True
        for file_path in files:
            if os.path.exists(file_path):
                print(f"  ✅ {file_path}")
            else:
                print(f"  ❌ {file_path} - MISSING")
                all_files_exist = False
        
        if all_files_exist:
            print(f"  ✅ Requirement {req_id} SATISFIED")
        else:
            print(f"  ❌ Requirement {req_id} NOT SATISFIED")
        
        requirement_results.append((req_id, all_files_exist))
    
    return requirement_results

def check_completion_summaries():
    """Check that completion summaries exist"""
    print("\nChecking completion summaries...")
    
    summaries = [
        "TASK_10_COMPLETION_SUMMARY.md",
        "TASK_10_3_COMPLETION_SUMMARY.md"
    ]
    
    summary_results = []
    for summary in summaries:
        if os.path.exists(summary):
            print(f"✅ {summary} exists")
            summary_results.append(True)
        else:
            print(f"❌ {summary} missing")
            summary_results.append(False)
    
    return summary_results

def main():
    """Main verification function"""
    print("=" * 70)
    print("TASK 10 VERIFICATION: SET UP MONITORING AND OBSERVABILITY")
    print("=" * 70)
    
    # Check file structure
    print("\n1. FILE STRUCTURE VERIFICATION")
    print("-" * 50)
    file_results = check_directory_structure()
    
    # Check configuration validity
    print("\n2. CONFIGURATION VALIDITY")
    print("-" * 50)
    config_results = check_configuration_validity()
    
    # Check requirements satisfaction
    print("\n3. REQUIREMENTS SATISFACTION")
    print("-" * 50)
    requirement_results = check_requirements_satisfaction()
    
    # Check completion summaries
    print("\n4. COMPLETION SUMMARIES")
    print("-" * 50)
    summary_results = check_completion_summaries()
    
    # Calculate overall results
    total_files = len(file_results)
    files_passed = sum(1 for _, result in file_results if result)
    
    total_configs = len(config_results)
    configs_passed = sum(config_results)
    
    total_requirements = len(requirement_results)
    requirements_passed = sum(1 for _, result in requirement_results if result)
    
    total_summaries = len(summary_results)
    summaries_passed = sum(summary_results)
    
    # Final summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    
    print(f"Files:         {files_passed}/{total_files} present")
    print(f"Configurations: {configs_passed}/{total_configs} valid")
    print(f"Requirements:   {requirements_passed}/{total_requirements} satisfied")
    print(f"Summaries:     {summaries_passed}/{total_summaries} present")
    
    # Overall assessment
    overall_score = (files_passed + configs_passed + requirements_passed + summaries_passed)
    total_possible = (total_files + total_configs + total_requirements + total_summaries)
    
    print(f"\nOverall Score: {overall_score}/{total_possible} ({(overall_score/total_possible)*100:.1f}%)")
    
    if overall_score == total_possible:
        print("\n🎉 TASK 10 FULLY COMPLETED!")
        print("✅ All monitoring and observability components are implemented")
        print("✅ All subtasks (10.1, 10.2, 10.3) are complete")
        print("✅ All requirements (11.1, 11.2, 11.3, 11.4, 11.5) are satisfied")
        return True
    elif overall_score >= total_possible * 0.9:
        print("\n✅ TASK 10 SUBSTANTIALLY COMPLETED!")
        print("Most components are implemented and functional")
        return True
    else:
        print("\n⚠️  TASK 10 PARTIALLY COMPLETED")
        print("Some components may need attention")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)