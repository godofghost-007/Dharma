# Incident Response Runbook

## Overview

This runbook provides detailed procedures for responding to various types of incidents in the Project Dharma platform. It covers security incidents, system outages, performance issues, and data integrity problems with step-by-step response procedures.

## Incident Classification and Severity Levels

### Severity Levels

#### Severity 1 (Critical)
- **Definition**: Complete system outage or security breach
- **Impact**: All users unable to access platform or data compromise
- **Response Time**: Immediate (within 15 minutes)
- **Escalation**: Automatic to senior management and security team

#### Severity 2 (High)
- **Definition**: Major functionality impaired or significant performance degradation
- **Impact**: Core features unavailable or severely degraded
- **Response Time**: Within 1 hour
- **Escalation**: To technical lead and operations manager

#### Severity 3 (Medium)
- **Definition**: Minor functionality issues or moderate performance impact
- **Impact**: Some features affected but workarounds available
- **Response Time**: Within 4 hours
- **Escalation**: To assigned technical team

#### Severity 4 (Low)
- **Definition**: Cosmetic issues or minor inconveniences
- **Impact**: Minimal user impact with easy workarounds
- **Response Time**: Within 24 hours
- **Escalation**: Standard support queue

### Incident Types

#### Security Incidents
- Unauthorized access attempts
- Data breaches or leaks
- Malware or ransomware attacks
- Insider threats
- API security violations

#### System Outages
- Complete platform unavailability
- Database connectivity issues
- Network infrastructure failures
- Third-party service dependencies
- Hardware failures

#### Performance Issues
- Slow response times
- High resource utilization
- Database performance problems
- Memory leaks or resource exhaustion
- Capacity limitations

#### Data Integrity Issues
- Data corruption or loss
- Synchronization problems
- Backup failures
- Migration issues
- Inconsistent analysis results

## Incident Response Team Structure

### Core Response Team

#### Incident Commander (IC)
- **Role**: Overall incident coordination and decision-making
- **Responsibilities**:
  - Assess incident severity and impact
  - Coordinate response activities
  - Communicate with stakeholders
  - Make critical decisions during incident
  - Conduct post-incident review

#### Technical Lead
- **Role**: Technical investigation and resolution
- **Responsibilities**:
  - Diagnose technical root causes
  - Implement technical solutions
  - Coordinate with development teams
  - Provide technical updates to IC

#### Communications Lead
- **Role**: Internal and external communications
- **Responsibilities**:
  - Manage stakeholder communications
  - Prepare status updates and notifications
  - Coordinate with public relations if needed
  - Document communication activities

#### Security Lead (for security incidents)
- **Role**: Security-specific response and investigation
- **Responsibilities**:
  - Assess security impact and containment
  - Coordinate with security teams
  - Implement security measures
  - Conduct forensic analysis

### Extended Response Team

#### Database Administrator
- **Role**: Database-specific issues and recovery
- **On-call**: 24/7 for Severity 1-2 incidents

#### Network Administrator
- **Role**: Network infrastructure and connectivity issues
- **On-call**: 24/7 for Severity 1-2 incidents

#### Development Team Lead
- **Role**: Application-specific issues and code fixes
- **On-call**: Business hours for Severity 3-4, 24/7 for Severity 1-2

#### Legal Counsel
- **Role**: Legal implications and compliance requirements
- **On-call**: As needed for security incidents

## Incident Response Procedures

### Initial Response (0-15 minutes)

#### Step 1: Incident Detection and Reporting
```bash
# Incident detection sources:
# - Automated monitoring alerts
# - User reports
# - Security system alerts
# - Third-party notifications

# Immediate actions:
1. Acknowledge incident receipt
2. Assign unique incident ID
3. Record initial timestamp
4. Gather basic incident information
```

#### Step 2: Initial Assessment
```bash
# Assessment checklist:
- [ ] Verify incident is genuine (not false positive)
- [ ] Determine preliminary severity level
- [ ] Identify affected systems and users
- [ ] Assess potential security implications
- [ ] Check for related incidents or patterns

# Documentation template:
Incident ID: INC-YYYY-MMDD-XXXX
Reported Time: [timestamp]
Reporter: [name/system]
Initial Description: [brief description]
Affected Systems: [list]
Preliminary Severity: [1-4]
```

#### Step 3: Team Activation
```bash
# Severity 1 activation:
- Incident Commander: Immediate notification
- Technical Lead: Immediate notification
- Communications Lead: Within 5 minutes
- Security Lead: Within 10 minutes (if security-related)
- Senior Management: Within 15 minutes

# Notification methods:
- Primary: Phone call
- Secondary: SMS/Text
- Tertiary: Email
- Emergency: Physical location if needed
```

### Investigation and Containment (15 minutes - 4 hours)

#### Security Incident Response

**Step 1: Immediate Containment**
```bash
#!/bin/bash
# Security incident containment script

# Isolate affected systems
echo "Starting security incident containment..."

# Block suspicious IP addresses
if [ "$SUSPICIOUS_IPS" ]; then
    for ip in $SUSPICIOUS_IPS; do
        iptables -A INPUT -s $ip -j DROP
        echo "Blocked IP: $ip"
    done
fi

# Disable compromised user accounts
if [ "$COMPROMISED_USERS" ]; then
    for user in $COMPROMISED_USERS; do
        # Disable user account
        psql -h localhost -U dharma_user -d dharma_db -c "
            UPDATE users SET status = 'disabled', 
                           disabled_reason = 'Security incident',
                           disabled_at = NOW()
            WHERE username = '$user';
        "
        echo "Disabled user: $user"
    done
fi

# Revoke API keys if compromised
if [ "$COMPROMISED_API_KEYS" ]; then
    for key in $COMPROMISED_API_KEYS; do
        redis-cli DEL "api_key:$key"
        echo "Revoked API key: $key"
    done
fi

# Enable enhanced logging
echo "Enabling enhanced security logging..."
# Update log levels for detailed forensics
```

**Step 2: Evidence Preservation**
```bash
#!/bin/bash
# Evidence preservation script

INCIDENT_ID=$1
EVIDENCE_DIR="/var/log/incidents/$INCIDENT_ID"

mkdir -p $EVIDENCE_DIR

# Capture system state
echo "Preserving evidence for incident $INCIDENT_ID..."

# System logs
cp /var/log/auth.log $EVIDENCE_DIR/
cp /var/log/syslog $EVIDENCE_DIR/
cp /var/log/dharma/*.log $EVIDENCE_DIR/

# Database logs
pg_dump -h localhost -U dharma_user dharma_db > $EVIDENCE_DIR/database_snapshot.sql

# Network connections
netstat -tuln > $EVIDENCE_DIR/network_connections.txt
ss -tuln > $EVIDENCE_DIR/socket_stats.txt

# Process information
ps aux > $EVIDENCE_DIR/process_list.txt
lsof > $EVIDENCE_DIR/open_files.txt

# Memory dump (if required)
if [ "$MEMORY_DUMP" = "true" ]; then
    dd if=/dev/mem of=$EVIDENCE_DIR/memory_dump.img
fi

# Create evidence hash
find $EVIDENCE_DIR -type f -exec sha256sum {} \; > $EVIDENCE_DIR/evidence_hashes.txt

echo "Evidence preserved in $EVIDENCE_DIR"
```

**Step 3: Forensic Analysis**
```bash
#!/bin/bash
# Basic forensic analysis script

INCIDENT_ID=$1
EVIDENCE_DIR="/var/log/incidents/$INCIDENT_ID"
ANALYSIS_DIR="$EVIDENCE_DIR/analysis"

mkdir -p $ANALYSIS_DIR

echo "Starting forensic analysis for incident $INCIDENT_ID..."

# Analyze authentication logs
echo "=== Authentication Analysis ===" > $ANALYSIS_DIR/auth_analysis.txt
grep -E "(Failed|Accepted)" $EVIDENCE_DIR/auth.log | \
    awk '{print $1, $2, $3, $9, $11}' | \
    sort | uniq -c | sort -nr >> $ANALYSIS_DIR/auth_analysis.txt

# Analyze database access
echo "=== Database Access Analysis ===" > $ANALYSIS_DIR/db_analysis.txt
psql -h localhost -U dharma_user -d dharma_db -c "
    SELECT username, action, resource_type, timestamp, details
    FROM audit_logs 
    WHERE timestamp > NOW() - INTERVAL '24 hours'
    ORDER BY timestamp DESC;
" >> $ANALYSIS_DIR/db_analysis.txt

# Analyze API access
echo "=== API Access Analysis ===" > $ANALYSIS_DIR/api_analysis.txt
grep "API" /var/log/dharma/api-gateway.log | \
    grep -E "(401|403|429)" | \
    awk '{print $1, $4, $7, $9}' | \
    sort | uniq -c | sort -nr >> $ANALYSIS_DIR/api_analysis.txt

# Network traffic analysis
echo "=== Network Traffic Analysis ===" > $ANALYSIS_DIR/network_analysis.txt
# Analyze firewall logs, connection patterns, etc.

echo "Forensic analysis completed. Results in $ANALYSIS_DIR"
```

#### System Outage Response

**Step 1: Service Health Assessment**
```bash
#!/bin/bash
# System health assessment script

echo "=== Project Dharma System Health Assessment ==="
echo "Timestamp: $(date)"

# Check Docker services
echo -e "\n=== Docker Services ==="
docker-compose ps

# Check database connectivity
echo -e "\n=== Database Connectivity ==="
# MongoDB
if mongo --eval "db.runCommand({ping: 1})" --quiet > /dev/null 2>&1; then
    echo "MongoDB: ONLINE"
    mongo --eval "db.serverStatus().connections" --quiet
else
    echo "MongoDB: OFFLINE"
    docker logs dharma_mongodb_1 --tail 20
fi

# PostgreSQL
if pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo "PostgreSQL: ONLINE"
    psql -h localhost -U dharma_user -d dharma_db -c "SELECT count(*) FROM pg_stat_activity;"
else
    echo "PostgreSQL: OFFLINE"
    docker logs dharma_postgresql_1 --tail 20
fi

# Redis
if redis-cli ping > /dev/null 2>&1; then
    echo "Redis: ONLINE"
    redis-cli info replication
else
    echo "Redis: OFFLINE"
    docker logs dharma_redis_1 --tail 20
fi

# Elasticsearch
if curl -s http://localhost:9200/_cluster/health > /dev/null 2>&1; then
    echo "Elasticsearch: ONLINE"
    curl -s http://localhost:9200/_cluster/health | jq '.status'
else
    echo "Elasticsearch: OFFLINE"
    docker logs dharma_elasticsearch_1 --tail 20
fi

# Check API endpoints
echo -e "\n=== API Endpoint Health ==="
services=("api-gateway:8000" "data-collection:8001" "ai-analysis:8002" "alert-management:8003")
for service in "${services[@]}"; do
    if curl -s -o /dev/null -w "%{http_code}" http://$service/health | grep -q "200"; then
        echo "$service: HEALTHY"
    else
        echo "$service: UNHEALTHY"
        service_name=$(echo $service | cut -d':' -f1)
        docker logs dharma_${service_name}_1 --tail 10
    fi
done

# System resources
echo -e "\n=== System Resources ==="
echo "CPU Usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
echo "Memory Usage: $(free | grep Mem | awk '{printf("%.1f%%", $3/$2 * 100.0)}')"
echo "Disk Usage: $(df -h / | awk 'NR==2{printf "%s", $5}')"
```

**Step 2: Service Recovery**
```bash
#!/bin/bash
# Service recovery script

SERVICE_NAME=$1
RECOVERY_TYPE=${2:-"restart"}  # restart, rebuild, restore

echo "Starting recovery for service: $SERVICE_NAME"
echo "Recovery type: $RECOVERY_TYPE"

case $RECOVERY_TYPE in
    "restart")
        echo "Restarting service..."
        docker-compose restart $SERVICE_NAME
        sleep 30
        
        # Verify service health
        if docker-compose ps $SERVICE_NAME | grep -q "Up"; then
            echo "Service $SERVICE_NAME restarted successfully"
        else
            echo "Service $SERVICE_NAME restart failed"
            docker logs dharma_${SERVICE_NAME}_1 --tail 50
            exit 1
        fi
        ;;
        
    "rebuild")
        echo "Rebuilding service..."
        docker-compose stop $SERVICE_NAME
        docker-compose rm -f $SERVICE_NAME
        docker-compose build $SERVICE_NAME
        docker-compose up -d $SERVICE_NAME
        sleep 60
        
        # Verify service health
        if docker-compose ps $SERVICE_NAME | grep -q "Up"; then
            echo "Service $SERVICE_NAME rebuilt successfully"
        else
            echo "Service $SERVICE_NAME rebuild failed"
            exit 1
        fi
        ;;
        
    "restore")
        echo "Restoring service from backup..."
        # Stop service
        docker-compose stop $SERVICE_NAME
        
        # Restore data if applicable
        if [ "$SERVICE_NAME" = "mongodb" ]; then
            # Restore MongoDB from latest backup
            LATEST_BACKUP=$(ls -t /backup/dharma/mongodb_* | head -1)
            mongorestore --drop --dir=$LATEST_BACKUP
        elif [ "$SERVICE_NAME" = "postgresql" ]; then
            # Restore PostgreSQL from latest backup
            LATEST_BACKUP=$(ls -t /backup/dharma/postgresql_* | head -1)
            psql -h localhost -U dharma_user -d dharma_db < $LATEST_BACKUP
        fi
        
        # Restart service
        docker-compose up -d $SERVICE_NAME
        sleep 60
        ;;
esac

echo "Recovery completed for $SERVICE_NAME"
```

#### Performance Issue Response

**Step 1: Performance Analysis**
```bash
#!/bin/bash
# Performance analysis script

echo "=== Performance Analysis Report ==="
echo "Timestamp: $(date)"

# System performance
echo -e "\n=== System Performance ==="
echo "Load Average: $(uptime | awk -F'load average:' '{print $2}')"
echo "CPU Usage:"
top -bn1 | grep "Cpu(s)"

echo -e "\nMemory Usage:"
free -h

echo -e "\nDisk I/O:"
iostat -x 1 3 | tail -n +4

echo -e "\nNetwork Statistics:"
ss -s

# Database performance
echo -e "\n=== Database Performance ==="

# MongoDB performance
echo "MongoDB Performance:"
mongo --eval "
    db.serverStatus().opcounters;
    db.serverStatus().connections;
    db.currentOp({'secs_running': {\$gte: 1}});
" --quiet

# PostgreSQL performance
echo -e "\nPostgreSQL Performance:"
psql -h localhost -U dharma_user -d dharma_db -c "
    SELECT query, calls, total_time, mean_time, rows
    FROM pg_stat_statements
    WHERE mean_time > 1000
    ORDER BY mean_time DESC
    LIMIT 10;
"

# Check for blocking queries
psql -h localhost -U dharma_user -d dharma_db -c "
    SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
    FROM pg_stat_activity 
    WHERE (now() - pg_stat_activity.query_start) > interval '30 seconds'
    AND state = 'active';
"

# Application performance
echo -e "\n=== Application Performance ==="
# Check response times from monitoring
curl -s 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,rate(http_request_duration_seconds_bucket[5m]))' | \
    jq '.data.result[] | {service: .metric.service, p95_response_time: .value[1]}'

# Container resource usage
echo -e "\n=== Container Resources ==="
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
```

**Step 2: Performance Optimization**
```bash
#!/bin/bash
# Performance optimization script

OPTIMIZATION_TYPE=$1  # cpu, memory, database, network

echo "Starting performance optimization: $OPTIMIZATION_TYPE"

case $OPTIMIZATION_TYPE in
    "cpu")
        echo "Optimizing CPU usage..."
        
        # Identify high CPU processes
        high_cpu_processes=$(ps aux --sort=-%cpu | head -10)
        echo "High CPU processes:"
        echo "$high_cpu_processes"
        
        # Adjust container CPU limits if needed
        docker update --cpus="2.0" dharma_ai-analysis_1
        docker update --cpus="1.5" dharma_data-collection_1
        ;;
        
    "memory")
        echo "Optimizing memory usage..."
        
        # Clear system caches
        sync && echo 3 > /proc/sys/vm/drop_caches
        
        # Restart memory-intensive services
        docker-compose restart ai-analysis
        
        # Adjust JVM heap sizes for Elasticsearch
        docker-compose exec elasticsearch bash -c "
            echo '-Xms8g' >> /usr/share/elasticsearch/config/jvm.options
            echo '-Xmx8g' >> /usr/share/elasticsearch/config/jvm.options
        "
        docker-compose restart elasticsearch
        ;;
        
    "database")
        echo "Optimizing database performance..."
        
        # MongoDB optimization
        mongo --eval "
            db.posts.reIndex();
            db.campaigns.reIndex();
            db.runCommand({planCacheClear: 'posts'});
        "
        
        # PostgreSQL optimization
        psql -h localhost -U dharma_user -d dharma_db -c "
            VACUUM ANALYZE alerts;
            VACUUM ANALYZE audit_logs;
            REINDEX DATABASE dharma_db;
        "
        
        # Clear Redis memory
        redis-cli FLUSHDB
        ;;
        
    "network")
        echo "Optimizing network performance..."
        
        # Check network connections
        netstat -tuln | wc -l
        
        # Optimize network settings
        echo 'net.core.rmem_max = 134217728' >> /etc/sysctl.conf
        echo 'net.core.wmem_max = 134217728' >> /etc/sysctl.conf
        sysctl -p
        ;;
esac

echo "Performance optimization completed"
```

### Communication Procedures

#### Internal Communications

**Incident Status Updates**
```
Subject: [INCIDENT] INC-YYYY-MMDD-XXXX - [Severity] - [Brief Description]

Incident Details:
- Incident ID: INC-YYYY-MMDD-XXXX
- Severity: [1-4]
- Status: [Investigating/Identified/Monitoring/Resolved]
- Start Time: [timestamp]
- Affected Systems: [list]
- Impact: [description]

Current Actions:
- [Action 1]
- [Action 2]
- [Action 3]

Next Update: [timestamp]
Incident Commander: [name]
```

**Escalation Notifications**
```
Subject: [ESCALATION] INC-YYYY-MMDD-XXXX - Requires Senior Management Attention

Escalation Reason:
- [ ] Severity 1 incident
- [ ] Extended duration (>4 hours)
- [ ] Customer impact
- [ ] Security implications
- [ ] Media attention potential

Incident Summary:
[Brief description of incident and impact]

Actions Taken:
[Summary of response actions]

Assistance Needed:
[Specific help or decisions required]

Contact: [Incident Commander details]
```

#### External Communications

**Customer Notification Template**
```
Subject: Service Status Update - Project Dharma Platform

Dear Project Dharma Users,

We are currently experiencing [brief description of issue] that may affect [specific functionality]. 

Impact:
- [Specific impacts on user experience]
- [Affected features or services]
- [Estimated number of affected users]

Actions:
- Our technical team is actively working to resolve this issue
- [Specific actions being taken]
- [Workarounds available to users]

Timeline:
- Issue detected: [timestamp]
- Estimated resolution: [timestamp or "investigating"]

We will provide updates every [frequency] until the issue is resolved.

For questions, please contact: [support contact information]

Thank you for your patience.

Project Dharma Operations Team
```

### Post-Incident Procedures

#### Incident Resolution

**Resolution Checklist**
```
- [ ] Root cause identified and documented
- [ ] Fix implemented and tested
- [ ] System functionality fully restored
- [ ] Performance metrics returned to normal
- [ ] All stakeholders notified of resolution
- [ ] Incident timeline documented
- [ ] Evidence preserved (if applicable)
- [ ] Lessons learned identified
- [ ] Follow-up actions assigned
- [ ] Incident formally closed
```

#### Post-Incident Review (PIR)

**PIR Meeting Agenda**
```
1. Incident Overview (10 minutes)
   - Timeline and key events
   - Impact assessment
   - Response team performance

2. Root Cause Analysis (20 minutes)
   - Technical root causes
   - Process failures
   - Human factors

3. Response Effectiveness (15 minutes)
   - What worked well
   - What could be improved
   - Communication effectiveness

4. Lessons Learned (10 minutes)
   - Key takeaways
   - Process improvements
   - Training needs

5. Action Items (5 minutes)
   - Preventive measures
   - Process updates
   - Follow-up tasks
```

**PIR Report Template**
```
# Post-Incident Review Report

## Incident Summary
- **Incident ID**: INC-YYYY-MMDD-XXXX
- **Date/Time**: [start] - [end]
- **Duration**: [total time]
- **Severity**: [1-4]
- **Impact**: [description]

## Timeline
| Time | Event | Action Taken |
|------|-------|--------------|
| [timestamp] | [event] | [action] |

## Root Cause Analysis
### Primary Cause
[Detailed description of root cause]

### Contributing Factors
- [Factor 1]
- [Factor 2]
- [Factor 3]

## Response Assessment
### What Worked Well
- [Success 1]
- [Success 2]

### Areas for Improvement
- [Improvement 1]
- [Improvement 2]

## Action Items
| Action | Owner | Due Date | Status |
|--------|-------|----------|--------|
| [action] | [person] | [date] | [status] |

## Lessons Learned
[Key lessons and recommendations]
```

This incident response runbook provides comprehensive procedures for handling various types of incidents in the Project Dharma platform, ensuring rapid response and effective resolution while maintaining detailed documentation for continuous improvement.