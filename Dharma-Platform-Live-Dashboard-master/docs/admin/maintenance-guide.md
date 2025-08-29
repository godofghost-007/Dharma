# System Maintenance Guide

## Overview

This guide provides detailed procedures for maintaining the Project Dharma platform, ensuring optimal performance, security, and reliability. It covers routine maintenance tasks, performance optimization, troubleshooting, and system updates.

## Maintenance Schedule

### Daily Maintenance (Automated)

#### System Health Monitoring
```bash
#!/bin/bash
# /opt/dharma/scripts/daily_health_check.sh

LOG_FILE="/var/log/dharma/daily_maintenance.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$DATE] Starting daily health check" >> $LOG_FILE

# Check service status
check_services() {
    echo "[$DATE] Checking service status..." >> $LOG_FILE
    
    services=("docker" "nginx" "prometheus" "grafana")
    for service in "${services[@]}"; do
        if systemctl is-active --quiet $service; then
            echo "[$DATE] $service: RUNNING" >> $LOG_FILE
        else
            echo "[$DATE] $service: FAILED" >> $LOG_FILE
            systemctl restart $service
            sleep 10
            if systemctl is-active --quiet $service; then
                echo "[$DATE] $service: RESTARTED SUCCESSFULLY" >> $LOG_FILE
            else
                echo "[$DATE] $service: RESTART FAILED - ALERT REQUIRED" >> $LOG_FILE
                # Send alert to administrators
                /opt/dharma/scripts/send_alert.sh "Service $service failed to restart"
            fi
        fi
    done
}

# Check Docker containers
check_containers() {
    echo "[$DATE] Checking Docker containers..." >> $LOG_FILE
    
    # Get list of expected containers
    expected_containers=(
        "dharma_mongodb_1"
        "dharma_postgresql_1" 
        "dharma_elasticsearch_1"
        "dharma_redis_1"
        "dharma_api-gateway_1"
        "dharma_data-collection_1"
        "dharma_ai-analysis_1"
        "dharma_alert-management_1"
        "dharma_dashboard_1"
    )
    
    for container in "${expected_containers[@]}"; do
        if docker ps --format "table {{.Names}}" | grep -q $container; then
            echo "[$DATE] $container: RUNNING" >> $LOG_FILE
        else
            echo "[$DATE] $container: NOT RUNNING" >> $LOG_FILE
            docker-compose restart $(echo $container | cut -d'_' -f2)
            sleep 15
            if docker ps --format "table {{.Names}}" | grep -q $container; then
                echo "[$DATE] $container: RESTARTED SUCCESSFULLY" >> $LOG_FILE
            else
                echo "[$DATE] $container: RESTART FAILED - ALERT REQUIRED" >> $LOG_FILE
                /opt/dharma/scripts/send_alert.sh "Container $container failed to restart"
            fi
        fi
    done
}

# Check disk space
check_disk_space() {
    echo "[$DATE] Checking disk space..." >> $LOG_FILE
    
    # Check root partition
    root_usage=$(df / | awk 'NR==2{print $5}' | sed 's/%//')
    if [ $root_usage -gt 85 ]; then
        echo "[$DATE] Root partition usage: ${root_usage}% - WARNING" >> $LOG_FILE
        /opt/dharma/scripts/send_alert.sh "Root partition usage is ${root_usage}%"
    else
        echo "[$DATE] Root partition usage: ${root_usage}% - OK" >> $LOG_FILE
    fi
    
    # Check data partition
    data_usage=$(df /data | awk 'NR==2{print $5}' | sed 's/%//')
    if [ $data_usage -gt 80 ]; then
        echo "[$DATE] Data partition usage: ${data_usage}% - WARNING" >> $LOG_FILE
        /opt/dharma/scripts/send_alert.sh "Data partition usage is ${data_usage}%"
        # Trigger cleanup procedures
        /opt/dharma/scripts/cleanup_old_data.sh
    else
        echo "[$DATE] Data partition usage: ${data_usage}% - OK" >> $LOG_FILE
    fi
}

# Check database connectivity
check_databases() {
    echo "[$DATE] Checking database connectivity..." >> $LOG_FILE
    
    # MongoDB
    if mongo --eval "db.runCommand({ping: 1})" --quiet > /dev/null 2>&1; then
        echo "[$DATE] MongoDB: CONNECTED" >> $LOG_FILE
    else
        echo "[$DATE] MongoDB: CONNECTION FAILED" >> $LOG_FILE
        /opt/dharma/scripts/send_alert.sh "MongoDB connection failed"
    fi
    
    # PostgreSQL
    if pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
        echo "[$DATE] PostgreSQL: CONNECTED" >> $LOG_FILE
    else
        echo "[$DATE] PostgreSQL: CONNECTION FAILED" >> $LOG_FILE
        /opt/dharma/scripts/send_alert.sh "PostgreSQL connection failed"
    fi
    
    # Redis
    if redis-cli ping > /dev/null 2>&1; then
        echo "[$DATE] Redis: CONNECTED" >> $LOG_FILE
    else
        echo "[$DATE] Redis: CONNECTION FAILED" >> $LOG_FILE
        /opt/dharma/scripts/send_alert.sh "Redis connection failed"
    fi
    
    # Elasticsearch
    if curl -s http://localhost:9200/_cluster/health > /dev/null 2>&1; then
        echo "[$DATE] Elasticsearch: CONNECTED" >> $LOG_FILE
    else
        echo "[$DATE] Elasticsearch: CONNECTION FAILED" >> $LOG_FILE
        /opt/dharma/scripts/send_alert.sh "Elasticsearch connection failed"
    fi
}

# Execute checks
check_services
check_containers
check_disk_space
check_databases

echo "[$DATE] Daily health check completed" >> $LOG_FILE
```

#### Log Rotation and Cleanup
```bash
#!/bin/bash
# /opt/dharma/scripts/daily_cleanup.sh

# Rotate application logs
find /var/log/dharma -name "*.log" -size +100M -exec gzip {} \;
find /var/log/dharma -name "*.log.gz" -mtime +7 -delete

# Clean Docker logs
docker system prune -f --filter "until=24h"

# Clean temporary files
find /tmp -name "dharma_*" -mtime +1 -delete
find /var/tmp -name "*.tmp" -mtime +1 -delete

# Clean old backup files (keep last 30 days)
find /backup/dharma -name "*.tar.gz" -mtime +30 -delete

# Clean old Elasticsearch indices (keep last 90 days)
curator --config /etc/curator/curator.yml /etc/curator/delete_indices.yml
```

### Weekly Maintenance

#### Database Optimization
```bash
#!/bin/bash
# /opt/dharma/scripts/weekly_db_maintenance.sh

LOG_FILE="/var/log/dharma/weekly_maintenance.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$DATE] Starting weekly database maintenance" >> $LOG_FILE

# MongoDB maintenance
mongodb_maintenance() {
    echo "[$DATE] MongoDB maintenance started" >> $LOG_FILE
    
    # Compact collections
    mongo dharma_platform --eval "
        db.posts.compact();
        db.campaigns.compact();
        db.users.compact();
    " >> $LOG_FILE 2>&1
    
    # Rebuild indexes
    mongo dharma_platform --eval "
        db.posts.reIndex();
        db.campaigns.reIndex();
        db.users.reIndex();
    " >> $LOG_FILE 2>&1
    
    # Update statistics
    mongo dharma_platform --eval "
        db.runCommand({planCacheClear: 'posts'});
        db.runCommand({planCacheClear: 'campaigns'});
    " >> $LOG_FILE 2>&1
    
    echo "[$DATE] MongoDB maintenance completed" >> $LOG_FILE
}

# PostgreSQL maintenance
postgresql_maintenance() {
    echo "[$DATE] PostgreSQL maintenance started" >> $LOG_FILE
    
    # Vacuum and analyze tables
    psql -h localhost -U dharma_user -d dharma_db -c "
        VACUUM ANALYZE alerts;
        VACUUM ANALYZE audit_logs;
        VACUUM ANALYZE users;
        VACUUM ANALYZE user_roles;
    " >> $LOG_FILE 2>&1
    
    # Update table statistics
    psql -h localhost -U dharma_user -d dharma_db -c "
        ANALYZE alerts;
        ANALYZE audit_logs;
        ANALYZE users;
    " >> $LOG_FILE 2>&1
    
    # Check for bloated tables
    psql -h localhost -U dharma_user -d dharma_db -c "
        SELECT schemaname, tablename, 
               pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
        FROM pg_tables 
        WHERE schemaname = 'public' 
        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
    " >> $LOG_FILE 2>&1
    
    echo "[$DATE] PostgreSQL maintenance completed" >> $LOG_FILE
}

# Elasticsearch maintenance
elasticsearch_maintenance() {
    echo "[$DATE] Elasticsearch maintenance started" >> $LOG_FILE
    
    # Force merge old indices
    curl -X POST "localhost:9200/dharma-posts-*/_forcemerge?max_num_segments=1" >> $LOG_FILE 2>&1
    
    # Clear cache
    curl -X POST "localhost:9200/_cache/clear" >> $LOG_FILE 2>&1
    
    # Check cluster health
    curl -X GET "localhost:9200/_cluster/health?pretty" >> $LOG_FILE 2>&1
    
    # Check index sizes
    curl -X GET "localhost:9200/_cat/indices?v&s=store.size:desc" >> $LOG_FILE 2>&1
    
    echo "[$DATE] Elasticsearch maintenance completed" >> $LOG_FILE
}

# Redis maintenance
redis_maintenance() {
    echo "[$DATE] Redis maintenance started" >> $LOG_FILE
    
    # Get memory usage info
    redis-cli info memory >> $LOG_FILE 2>&1
    
    # Clean expired keys
    redis-cli --scan --pattern "temp:*" | xargs -r redis-cli del
    
    # Save current state
    redis-cli bgsave >> $LOG_FILE 2>&1
    
    echo "[$DATE] Redis maintenance completed" >> $LOG_FILE
}

# Execute maintenance tasks
mongodb_maintenance
postgresql_maintenance
elasticsearch_maintenance
redis_maintenance

echo "[$DATE] Weekly database maintenance completed" >> $LOG_FILE
```

#### Performance Analysis
```bash
#!/bin/bash
# /opt/dharma/scripts/weekly_performance_analysis.sh

REPORT_FILE="/var/log/dharma/performance_report_$(date +%Y%m%d).txt"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "Project Dharma Performance Report - $DATE" > $REPORT_FILE
echo "=================================================" >> $REPORT_FILE

# System resource usage
echo "" >> $REPORT_FILE
echo "SYSTEM RESOURCES:" >> $REPORT_FILE
echo "CPU Usage:" >> $REPORT_FILE
top -bn1 | grep "Cpu(s)" >> $REPORT_FILE

echo "" >> $REPORT_FILE
echo "Memory Usage:" >> $REPORT_FILE
free -h >> $REPORT_FILE

echo "" >> $REPORT_FILE
echo "Disk Usage:" >> $REPORT_FILE
df -h >> $REPORT_FILE

echo "" >> $REPORT_FILE
echo "Network Statistics:" >> $REPORT_FILE
ss -tuln >> $REPORT_FILE

# Database performance
echo "" >> $REPORT_FILE
echo "DATABASE PERFORMANCE:" >> $REPORT_FILE

# MongoDB stats
echo "MongoDB Statistics:" >> $REPORT_FILE
mongo --eval "
    db.serverStatus().connections;
    db.serverStatus().opcounters;
    db.stats();
" >> $REPORT_FILE 2>&1

# PostgreSQL stats
echo "" >> $REPORT_FILE
echo "PostgreSQL Statistics:" >> $REPORT_FILE
psql -h localhost -U dharma_user -d dharma_db -c "
    SELECT * FROM pg_stat_database WHERE datname = 'dharma_db';
    SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del 
    FROM pg_stat_user_tables ORDER BY n_tup_ins DESC LIMIT 10;
" >> $REPORT_FILE 2>&1

# Application metrics
echo "" >> $REPORT_FILE
echo "APPLICATION METRICS:" >> $REPORT_FILE

# Get metrics from Prometheus
curl -s 'http://localhost:9090/api/v1/query?query=rate(http_requests_total[5m])' | jq '.data.result' >> $REPORT_FILE 2>&1

# Docker container stats
echo "" >> $REPORT_FILE
echo "CONTAINER STATISTICS:" >> $REPORT_FILE
docker stats --no-stream >> $REPORT_FILE

# Generate recommendations
echo "" >> $REPORT_FILE
echo "RECOMMENDATIONS:" >> $REPORT_FILE

# Check for high CPU usage
cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1 | cut -d',' -f1)
if (( $(echo "$cpu_usage > 80" | bc -l) )); then
    echo "- High CPU usage detected ($cpu_usage%). Consider scaling or optimization." >> $REPORT_FILE
fi

# Check for high memory usage
mem_usage=$(free | grep Mem | awk '{printf("%.1f", $3/$2 * 100.0)}')
if (( $(echo "$mem_usage > 85" | bc -l) )); then
    echo "- High memory usage detected ($mem_usage%). Consider adding more RAM or optimizing memory usage." >> $REPORT_FILE
fi

# Check for high disk usage
disk_usage=$(df / | awk 'NR==2{print $5}' | sed 's/%//')
if [ $disk_usage -gt 80 ]; then
    echo "- High disk usage detected ($disk_usage%). Consider cleanup or adding more storage." >> $REPORT_FILE
fi

echo "Performance analysis completed. Report saved to $REPORT_FILE"
```

### Monthly Maintenance

#### Security Updates and Patches
```bash
#!/bin/bash
# /opt/dharma/scripts/monthly_security_updates.sh

LOG_FILE="/var/log/dharma/security_updates.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$DATE] Starting monthly security updates" >> $LOG_FILE

# Update package lists
apt update >> $LOG_FILE 2>&1

# Check for security updates
security_updates=$(apt list --upgradable 2>/dev/null | grep -i security | wc -l)
echo "[$DATE] Found $security_updates security updates" >> $LOG_FILE

if [ $security_updates -gt 0 ]; then
    echo "[$DATE] Installing security updates..." >> $LOG_FILE
    
    # Create system backup before updates
    /opt/dharma/scripts/create_backup.sh "pre_security_update_$(date +%Y%m%d)"
    
    # Install security updates
    apt upgrade -y >> $LOG_FILE 2>&1
    
    # Check if reboot is required
    if [ -f /var/run/reboot-required ]; then
        echo "[$DATE] Reboot required after security updates" >> $LOG_FILE
        /opt/dharma/scripts/send_alert.sh "System reboot required after security updates"
        
        # Schedule reboot during maintenance window
        echo "shutdown -r +60 'System will reboot in 1 hour for security updates'" | at now
    fi
else
    echo "[$DATE] No security updates available" >> $LOG_FILE
fi

# Update Docker images
echo "[$DATE] Updating Docker images..." >> $LOG_FILE
docker-compose pull >> $LOG_FILE 2>&1

# Scan for vulnerabilities
echo "[$DATE] Running vulnerability scan..." >> $LOG_FILE
if command -v trivy &> /dev/null; then
    trivy image --severity HIGH,CRITICAL dharma/api-gateway:latest >> $LOG_FILE 2>&1
    trivy image --severity HIGH,CRITICAL dharma/data-collection:latest >> $LOG_FILE 2>&1
    trivy image --severity HIGH,CRITICAL dharma/ai-analysis:latest >> $LOG_FILE 2>&1
fi

echo "[$DATE] Monthly security updates completed" >> $LOG_FILE
```

#### Capacity Planning Analysis
```bash
#!/bin/bash
# /opt/dharma/scripts/monthly_capacity_analysis.sh

REPORT_FILE="/var/log/dharma/capacity_report_$(date +%Y%m).txt"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "Project Dharma Capacity Planning Report - $DATE" > $REPORT_FILE
echo "=================================================" >> $REPORT_FILE

# Historical data growth analysis
echo "" >> $REPORT_FILE
echo "DATA GROWTH ANALYSIS:" >> $REPORT_FILE

# MongoDB data growth
mongo_size=$(mongo --eval "db.stats().dataSize" --quiet)
echo "Current MongoDB size: $mongo_size bytes" >> $REPORT_FILE

# PostgreSQL data growth
pg_size=$(psql -h localhost -U dharma_user -d dharma_db -t -c "SELECT pg_database_size('dharma_db');")
echo "Current PostgreSQL size: $pg_size bytes" >> $REPORT_FILE

# Elasticsearch data growth
es_size=$(curl -s "localhost:9200/_cat/indices?bytes=b" | awk '{sum += $9} END {print sum}')
echo "Current Elasticsearch size: $es_size bytes" >> $REPORT_FILE

# Calculate growth rates (requires historical data)
echo "" >> $REPORT_FILE
echo "GROWTH PROJECTIONS:" >> $REPORT_FILE

# Estimate future storage needs (6 months projection)
current_total=$((mongo_size + pg_size + es_size))
monthly_growth_rate=0.15  # 15% monthly growth estimate
projected_6m=$((current_total * (115**6) / (100**6)))

echo "Current total data size: $current_total bytes" >> $REPORT_FILE
echo "Projected size in 6 months: $projected_6m bytes" >> $REPORT_FILE

# Resource utilization trends
echo "" >> $REPORT_FILE
echo "RESOURCE UTILIZATION TRENDS:" >> $REPORT_FILE

# CPU utilization over last month
echo "Average CPU utilization (last 30 days):" >> $REPORT_FILE
curl -s 'http://localhost:9090/api/v1/query?query=avg_over_time(100-avg(rate(node_cpu_seconds_total{mode="idle"}[5m]))*100[30d])' | jq -r '.data.result[0].value[1]' >> $REPORT_FILE

# Memory utilization over last month
echo "Average memory utilization (last 30 days):" >> $REPORT_FILE
curl -s 'http://localhost:9090/api/v1/query?query=avg_over_time((1-node_memory_MemAvailable_bytes/node_memory_MemTotal_bytes)*100[30d])' | jq -r '.data.result[0].value[1]' >> $REPORT_FILE

# Recommendations
echo "" >> $REPORT_FILE
echo "CAPACITY RECOMMENDATIONS:" >> $REPORT_FILE

if [ $projected_6m -gt $((current_total * 3)) ]; then
    echo "- Consider adding additional storage capacity within 3 months" >> $REPORT_FILE
fi

echo "- Monitor data retention policies to optimize storage usage" >> $REPORT_FILE
echo "- Consider implementing data archiving for older records" >> $REPORT_FILE
echo "- Review and optimize database indexes for performance" >> $REPORT_FILE

echo "Capacity analysis completed. Report saved to $REPORT_FILE"
```

## Performance Optimization

### Database Performance Tuning

#### MongoDB Optimization
```javascript
// /opt/dharma/scripts/mongodb_optimization.js

// Connection and performance monitoring
db = db.getSiblingDB('dharma_platform');

// Check current performance
print("=== MongoDB Performance Analysis ===");
print("Server Status:");
printjson(db.serverStatus().connections);
printjson(db.serverStatus().opcounters);

print("\nCollection Statistics:");
printjson(db.posts.stats());
printjson(db.campaigns.stats());

// Optimize indexes
print("\n=== Index Optimization ===");

// Remove unused indexes
db.posts.dropIndex("old_unused_index");

// Create compound indexes for common queries
db.posts.createIndex(
    {"platform": 1, "timestamp": -1, "analysis_results.sentiment": 1},
    {background: true, name: "platform_time_sentiment_idx"}
);

db.posts.createIndex(
    {"user_id": 1, "timestamp": -1},
    {background: true, name: "user_timeline_idx"}
);

// Create text index for content search
db.posts.createIndex(
    {"content": "text", "analysis_results.sentiment": 1},
    {background: true, name: "content_search_idx"}
);

// Optimize campaign queries
db.campaigns.createIndex(
    {"status": 1, "detection_date": -1},
    {background: true, name: "status_detection_idx"}
);

// Check index usage
print("\nIndex Usage Statistics:");
db.posts.aggregate([{$indexStats: {}}]).forEach(printjson);

// Optimize collection settings
print("\n=== Collection Optimization ===");

// Enable compression for large collections
db.runCommand({
    "collMod": "posts",
    "storageEngine": {
        "wiredTiger": {
            "configString": "block_compressor=snappy"
        }
    }
});

// Set up sharding for large collections
if (db.isMaster().ismaster) {
    sh.enableSharding("dharma_platform");
    sh.shardCollection(
        "dharma_platform.posts",
        {"platform": 1, "timestamp": 1}
    );
}

print("MongoDB optimization completed");
```

#### PostgreSQL Optimization
```sql
-- /opt/dharma/scripts/postgresql_optimization.sql

-- Performance analysis
\echo '=== PostgreSQL Performance Analysis ==='

-- Check database size and growth
SELECT 
    pg_size_pretty(pg_database_size('dharma_db')) as database_size,
    pg_size_pretty(pg_total_relation_size('alerts')) as alerts_size,
    pg_size_pretty(pg_total_relation_size('audit_logs')) as audit_logs_size;

-- Check table statistics
SELECT 
    schemaname,
    tablename,
    n_tup_ins as inserts,
    n_tup_upd as updates,
    n_tup_del as deletes,
    n_live_tup as live_tuples,
    n_dead_tup as dead_tuples
FROM pg_stat_user_tables
ORDER BY n_tup_ins DESC;

-- Check index usage
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_tup_read DESC;

-- Identify slow queries
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    rows
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Index optimization
\echo '=== Index Optimization ==='

-- Create partial indexes for common filtered queries
CREATE INDEX CONCURRENTLY idx_alerts_active 
ON alerts(created_at DESC) 
WHERE status IN ('new', 'in_progress');

CREATE INDEX CONCURRENTLY idx_audit_logs_recent 
ON audit_logs(timestamp DESC) 
WHERE timestamp > NOW() - INTERVAL '30 days';

-- Create composite indexes for complex queries
CREATE INDEX CONCURRENTLY idx_alerts_severity_status 
ON alerts(severity, status, created_at DESC);

-- Table maintenance
\echo '=== Table Maintenance ==='

-- Vacuum and analyze tables
VACUUM ANALYZE alerts;
VACUUM ANALYZE audit_logs;
VACUUM ANALYZE users;

-- Reindex if needed
REINDEX INDEX CONCURRENTLY idx_alerts_created_at;

-- Update table statistics
ANALYZE alerts;
ANALYZE audit_logs;

-- Configuration optimization
\echo '=== Configuration Recommendations ==='

-- Check current settings
SHOW shared_buffers;
SHOW effective_cache_size;
SHOW work_mem;
SHOW maintenance_work_mem;

-- Recommend settings based on system memory
SELECT 
    'shared_buffers should be ~25% of RAM' as recommendation,
    pg_size_pretty(pg_settings.setting::bigint * 8192) as current_value
FROM pg_settings 
WHERE name = 'shared_buffers';

\echo 'PostgreSQL optimization completed'
```

#### Elasticsearch Optimization
```bash
#!/bin/bash
# /opt/dharma/scripts/elasticsearch_optimization.sh

echo "=== Elasticsearch Performance Optimization ==="

# Check cluster health
echo "Cluster Health:"
curl -X GET "localhost:9200/_cluster/health?pretty"

# Check node statistics
echo -e "\nNode Statistics:"
curl -X GET "localhost:9200/_nodes/stats?pretty"

# Optimize index settings
echo -e "\nOptimizing index settings..."

# Update index settings for better performance
curl -X PUT "localhost:9200/dharma-posts-*/_settings" -H 'Content-Type: application/json' -d'
{
  "index": {
    "refresh_interval": "30s",
    "number_of_replicas": 1,
    "translog.flush_threshold_size": "1gb",
    "merge.policy.max_merge_at_once": 5,
    "merge.policy.segments_per_tier": 5
  }
}'

# Force merge old indices
echo -e "\nForce merging old indices..."
curl -X POST "localhost:9200/dharma-posts-$(date -d '7 days ago' +%Y.%m.%d)/_forcemerge?max_num_segments=1"

# Clear cache
echo -e "\nClearing cache..."
curl -X POST "localhost:9200/_cache/clear"

# Check index sizes and suggest cleanup
echo -e "\nIndex sizes:"
curl -X GET "localhost:9200/_cat/indices?v&s=store.size:desc"

# Optimize mapping for new indices
echo -e "\nUpdating index template..."
curl -X PUT "localhost:9200/_index_template/dharma-posts" -H 'Content-Type: application/json' -d'
{
  "index_patterns": ["dharma-posts-*"],
  "template": {
    "settings": {
      "number_of_shards": 3,
      "number_of_replicas": 1,
      "refresh_interval": "30s",
      "analysis": {
        "analyzer": {
          "dharma_analyzer": {
            "type": "custom",
            "tokenizer": "standard",
            "filter": ["lowercase", "stop", "snowball"]
          }
        }
      }
    },
    "mappings": {
      "properties": {
        "content": {
          "type": "text",
          "analyzer": "dharma_analyzer",
          "fields": {
            "keyword": {
              "type": "keyword",
              "ignore_above": 256
            }
          }
        },
        "timestamp": {
          "type": "date"
        },
        "platform": {
          "type": "keyword"
        },
        "sentiment": {
          "type": "keyword"
        },
        "risk_score": {
          "type": "float"
        }
      }
    }
  }
}'

echo -e "\nElasticsearch optimization completed"
```

### Application Performance Optimization

#### Connection Pool Tuning
```python
# /opt/dharma/scripts/optimize_connection_pools.py

import asyncio
import asyncpg
import motor.motor_asyncio
import aioredis
from elasticsearch import AsyncElasticsearch

class ConnectionPoolOptimizer:
    """Optimize database connection pools based on current load"""
    
    def __init__(self):
        self.recommendations = {}
    
    async def analyze_postgresql_pool(self):
        """Analyze PostgreSQL connection pool usage"""
        conn = await asyncpg.connect(
            "postgresql://dharma_user:password@localhost:5432/dharma_db"
        )
        
        # Check current connections
        result = await conn.fetch("""
            SELECT count(*) as active_connections,
                   max_conn,
                   (count(*) * 100.0 / max_conn) as usage_percent
            FROM pg_stat_activity, 
                 (SELECT setting::int as max_conn FROM pg_settings WHERE name = 'max_connections') s
            WHERE state = 'active'
            GROUP BY max_conn
        """)
        
        if result:
            usage_percent = result[0]['usage_percent']
            if usage_percent > 80:
                self.recommendations['postgresql'] = {
                    'action': 'increase_pool_size',
                    'current_usage': f"{usage_percent:.1f}%",
                    'recommended_max_connections': result[0]['max_conn'] * 1.5
                }
            elif usage_percent < 20:
                self.recommendations['postgresql'] = {
                    'action': 'decrease_pool_size',
                    'current_usage': f"{usage_percent:.1f}%",
                    'recommended_max_connections': max(10, result[0]['max_conn'] * 0.7)
                }
        
        await conn.close()
    
    async def analyze_mongodb_pool(self):
        """Analyze MongoDB connection pool usage"""
        client = motor.motor_asyncio.AsyncIOMotorClient(
            "mongodb://localhost:27017/dharma_platform",
            maxPoolSize=50
        )
        
        # Get server status
        server_status = await client.admin.command("serverStatus")
        connections = server_status.get('connections', {})
        
        current_connections = connections.get('current', 0)
        available_connections = connections.get('available', 0)
        total_created = connections.get('totalCreated', 0)
        
        usage_percent = (current_connections / (current_connections + available_connections)) * 100
        
        if usage_percent > 80:
            self.recommendations['mongodb'] = {
                'action': 'increase_pool_size',
                'current_usage': f"{usage_percent:.1f}%",
                'recommended_max_pool_size': 75
            }
        elif usage_percent < 20:
            self.recommendations['mongodb'] = {
                'action': 'decrease_pool_size',
                'current_usage': f"{usage_percent:.1f}%",
                'recommended_max_pool_size': 25
            }
        
        client.close()
    
    async def analyze_redis_pool(self):
        """Analyze Redis connection pool usage"""
        redis = aioredis.from_url("redis://localhost:6379")
        
        # Get Redis info
        info = await redis.info()
        connected_clients = info.get('connected_clients', 0)
        
        # Redis doesn't have a fixed pool size, but we can monitor client connections
        if connected_clients > 100:
            self.recommendations['redis'] = {
                'action': 'monitor_connections',
                'current_clients': connected_clients,
                'recommendation': 'Consider connection pooling optimization'
            }
        
        await redis.close()
    
    async def generate_optimization_report(self):
        """Generate comprehensive optimization report"""
        await asyncio.gather(
            self.analyze_postgresql_pool(),
            self.analyze_mongodb_pool(),
            self.analyze_redis_pool()
        )
        
        print("=== Connection Pool Optimization Report ===")
        for db, recommendation in self.recommendations.items():
            print(f"\n{db.upper()}:")
            for key, value in recommendation.items():
                print(f"  {key}: {value}")
        
        # Generate configuration updates
        self.generate_config_updates()
    
    def generate_config_updates(self):
        """Generate updated configuration files"""
        if 'postgresql' in self.recommendations:
            rec = self.recommendations['postgresql']
            if rec['action'] == 'increase_pool_size':
                print(f"\nPostgreSQL Config Update:")
                print(f"max_connections = {int(rec['recommended_max_connections'])}")
        
        if 'mongodb' in self.recommendations:
            rec = self.recommendations['mongodb']
            print(f"\nMongoDB Config Update:")
            print(f"maxPoolSize: {rec['recommended_max_pool_size']}")

# Run optimization analysis
async def main():
    optimizer = ConnectionPoolOptimizer()
    await optimizer.generate_optimization_report()

if __name__ == "__main__":
    asyncio.run(main())
```

## Troubleshooting Procedures

### Common Issues and Solutions

#### Service Startup Issues
```bash
#!/bin/bash
# /opt/dharma/scripts/troubleshoot_startup.sh

echo "=== Project Dharma Startup Troubleshooting ==="

# Check Docker daemon
if ! systemctl is-active --quiet docker; then
    echo "Docker daemon is not running. Starting..."
    systemctl start docker
    sleep 5
fi

# Check Docker Compose file
if [ ! -f "docker-compose.yml" ]; then
    echo "ERROR: docker-compose.yml not found in current directory"
    exit 1
fi

# Validate Docker Compose configuration
echo "Validating Docker Compose configuration..."
docker-compose config > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "ERROR: Invalid Docker Compose configuration"
    docker-compose config
    exit 1
fi

# Check for port conflicts
echo "Checking for port conflicts..."
ports=(5432 27017 9200 6379 8000 8001 8002 8003 8004)
for port in "${ports[@]}"; do
    if netstat -tuln | grep -q ":$port "; then
        echo "WARNING: Port $port is already in use"
        netstat -tuln | grep ":$port "
    fi
done

# Check disk space
echo "Checking disk space..."
df -h | awk '$5 > 90 {print "WARNING: " $0}'

# Check memory availability
echo "Checking memory availability..."
free -h

# Attempt to start services with detailed logging
echo "Starting services with detailed logging..."
docker-compose up -d --remove-orphans

# Wait for services to start
sleep 30

# Check service health
echo "Checking service health..."
docker-compose ps

# Test database connections
echo "Testing database connections..."

# MongoDB
if mongo --eval "db.runCommand({ping: 1})" --quiet > /dev/null 2>&1; then
    echo "✓ MongoDB connection successful"
else
    echo "✗ MongoDB connection failed"
    docker logs dharma_mongodb_1 --tail 50
fi

# PostgreSQL
if pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo "✓ PostgreSQL connection successful"
else
    echo "✗ PostgreSQL connection failed"
    docker logs dharma_postgresql_1 --tail 50
fi

# Redis
if redis-cli ping > /dev/null 2>&1; then
    echo "✓ Redis connection successful"
else
    echo "✗ Redis connection failed"
    docker logs dharma_redis_1 --tail 50
fi

# Elasticsearch
if curl -s http://localhost:9200/_cluster/health > /dev/null 2>&1; then
    echo "✓ Elasticsearch connection successful"
else
    echo "✗ Elasticsearch connection failed"
    docker logs dharma_elasticsearch_1 --tail 50
fi

echo "Startup troubleshooting completed"
```

#### Performance Issues
```bash
#!/bin/bash
# /opt/dharma/scripts/troubleshoot_performance.sh

echo "=== Performance Troubleshooting ==="

# Check system resources
echo "System Resource Usage:"
echo "CPU Usage:"
top -bn1 | grep "Cpu(s)"

echo -e "\nMemory Usage:"
free -h

echo -e "\nDisk I/O:"
iostat -x 1 3

echo -e "\nNetwork Usage:"
ss -tuln | wc -l
echo "Active connections: $(ss -tuln | wc -l)"

# Check Docker container resources
echo -e "\nContainer Resource Usage:"
docker stats --no-stream

# Check database performance
echo -e "\nDatabase Performance:"

# MongoDB slow operations
echo "MongoDB slow operations:"
mongo --eval "db.currentOp({'secs_running': {\$gte: 5}})" --quiet

# PostgreSQL active queries
echo -e "\nPostgreSQL active queries:"
psql -h localhost -U dharma_user -d dharma_db -c "
    SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
    FROM pg_stat_activity 
    WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes'
    AND state = 'active';
"

# Check for blocking queries
psql -h localhost -U dharma_user -d dharma_db -c "
    SELECT blocked_locks.pid AS blocked_pid,
           blocked_activity.usename AS blocked_user,
           blocking_locks.pid AS blocking_pid,
           blocking_activity.usename AS blocking_user,
           blocked_activity.query AS blocked_statement,
           blocking_activity.query AS current_statement_in_blocking_process
    FROM pg_catalog.pg_locks blocked_locks
    JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
    JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
        AND blocking_locks.DATABASE IS NOT DISTINCT FROM blocked_locks.DATABASE
        AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
        AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
        AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
        AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
        AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
        AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
        AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
        AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
        AND blocking_locks.pid != blocked_locks.pid
    JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
    WHERE NOT blocked_locks.GRANTED;
"

# Elasticsearch performance
echo -e "\nElasticsearch performance:"
curl -s "localhost:9200/_cluster/stats?pretty" | jq '.nodes.jvm.mem'
curl -s "localhost:9200/_nodes/stats/indices?pretty" | jq '.nodes[].indices.search'

# Application-specific performance checks
echo -e "\nApplication Performance Metrics:"
curl -s "localhost:9090/api/v1/query?query=rate(http_requests_total[5m])" | jq '.data.result'

# Generate performance recommendations
echo -e "\nPerformance Recommendations:"

# Check if any service is using too much CPU
high_cpu_containers=$(docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}" | awk 'NR>1 && $2+0 > 80 {print $1}')
if [ ! -z "$high_cpu_containers" ]; then
    echo "- High CPU usage detected in containers: $high_cpu_containers"
    echo "  Consider scaling these services or optimizing their performance"
fi

# Check if any service is using too much memory
high_mem_containers=$(docker stats --no-stream --format "table {{.Container}}\t{{.MemPerc}}" | awk 'NR>1 && $2+0 > 80 {print $1}')
if [ ! -z "$high_mem_containers" ]; then
    echo "- High memory usage detected in containers: $high_mem_containers"
    echo "  Consider increasing memory limits or optimizing memory usage"
fi

echo "Performance troubleshooting completed"
```

This maintenance guide provides comprehensive procedures for keeping the Project Dharma platform running optimally. Regular execution of these maintenance tasks ensures system reliability, performance, and security.