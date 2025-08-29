# System Configuration Guide

## Overview

This guide provides comprehensive instructions for configuring and maintaining the Project Dharma platform. It covers all aspects of system administration, from initial setup to ongoing maintenance and optimization.

## Initial System Setup

### Prerequisites

#### Hardware Requirements
- **Minimum Configuration**:
  - CPU: 16 cores (Intel Xeon or AMD EPYC)
  - RAM: 64GB DDR4
  - Storage: 2TB NVMe SSD + 10TB HDD
  - Network: 10Gbps connection

- **Recommended Configuration**:
  - CPU: 32 cores (Intel Xeon or AMD EPYC)
  - RAM: 128GB DDR4
  - Storage: 4TB NVMe SSD + 20TB HDD
  - Network: 25Gbps connection with redundancy

#### Software Requirements
- **Operating System**: Ubuntu 22.04 LTS or CentOS 8
- **Container Runtime**: Docker 24.0+ and Docker Compose 2.0+
- **Orchestration**: Kubernetes 1.28+ (for production)
- **Monitoring**: Prometheus, Grafana, ELK Stack
- **Security**: SSL/TLS certificates, firewall configuration

### Installation Process

#### 1. Base System Configuration

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y curl wget git vim htop iotop nethogs

# Configure system limits
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf
echo "vm.max_map_count=262144" >> /etc/sysctl.conf

# Apply sysctl changes
sudo sysctl -p
```

#### 2. Docker Installation and Configuration

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Configure Docker daemon
sudo mkdir -p /etc/docker
cat <<EOF | sudo tee /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "data-root": "/var/lib/docker"
}
EOF

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

#### 3. Project Dharma Deployment

```bash
# Clone the repository
git clone https://github.com/your-org/project-dharma.git
cd project-dharma

# Configure environment variables
cp .env.example .env
# Edit .env file with your configuration

# Deploy the platform
make deploy-production
```

## Configuration Management

### Environment Configuration

#### Core Environment Variables

```bash
# Database Configuration
MONGODB_URI=mongodb://mongodb:27017/dharma_platform
POSTGRESQL_URI=postgresql://user:password@postgresql:5432/dharma_db
ELASTICSEARCH_URI=http://elasticsearch:9200
REDIS_URI=redis://redis:6379/0

# API Keys and Secrets
TWITTER_BEARER_TOKEN=your_twitter_bearer_token
YOUTUBE_API_KEY=your_youtube_api_key
TELEGRAM_API_ID=your_telegram_api_id
TELEGRAM_API_HASH=your_telegram_api_hash

# Security Configuration
JWT_SECRET_KEY=your_jwt_secret_key
ENCRYPTION_KEY=your_encryption_key
SSL_CERT_PATH=/etc/ssl/certs/dharma.crt
SSL_KEY_PATH=/etc/ssl/private/dharma.key

# Monitoring and Logging
PROMETHEUS_URL=http://prometheus:9090
GRAFANA_URL=http://grafana:3000
ELASTICSEARCH_LOG_INDEX=dharma-logs
LOG_LEVEL=INFO

# Performance Configuration
MAX_WORKERS=8
BATCH_SIZE=1000
CACHE_TTL=3600
RATE_LIMIT_PER_MINUTE=1000
```

#### Service-Specific Configuration

**Data Collection Service**
```yaml
# services/data-collection-service/config.yaml
collection:
  twitter:
    enabled: true
    rate_limit: 300  # requests per 15 minutes
    retry_attempts: 3
    timeout: 30
  youtube:
    enabled: true
    quota_limit: 10000  # daily quota
    batch_size: 50
  telegram:
    enabled: true
    session_file: /data/telegram.session
  web_scraping:
    enabled: true
    respect_robots: true
    delay_range: [1, 3]  # seconds between requests

storage:
  mongodb:
    collection: raw_posts
    batch_size: 1000
  kafka:
    topic: collected_data
    partition_key: platform
```

**AI Analysis Service**
```yaml
# services/ai-analysis-service/config.yaml
models:
  sentiment:
    model_path: /models/dharma-bert-sentiment
    batch_size: 32
    confidence_threshold: 0.7
  bot_detection:
    model_path: /models/bot-detection-model.pkl
    feature_window: 30  # days
    threshold: 0.8
  campaign_detection:
    similarity_threshold: 0.85
    temporal_window: 24  # hours
    min_participants: 5

processing:
  max_concurrent: 4
  timeout: 300  # seconds
  retry_attempts: 2
```

### Database Configuration

#### MongoDB Configuration

```javascript
// /etc/mongod.conf equivalent in JavaScript
{
  "storage": {
    "dbPath": "/var/lib/mongodb",
    "journal": {"enabled": true},
    "wiredTiger": {
      "engineConfig": {"cacheSizeGB": 16},
      "collectionConfig": {"blockCompressor": "snappy"}
    }
  },
  "systemLog": {
    "destination": "file",
    "logAppend": true,
    "path": "/var/log/mongodb/mongod.log"
  },
  "net": {
    "port": 27017,
    "bindIp": "0.0.0.0"
  },
  "replication": {
    "replSetName": "dharma-replica-set"
  },
  "sharding": {
    "clusterRole": "shardsvr"
  }
}
```

**Index Configuration**
```javascript
// Create indexes for optimal performance
db.posts.createIndex({"timestamp": -1})
db.posts.createIndex({"platform": 1, "timestamp": -1})
db.posts.createIndex({"user_id": 1})
db.posts.createIndex({"analysis_results.sentiment": 1})
db.posts.createIndex({"analysis_results.risk_score": -1})
db.posts.createIndex({"content": "text"})

db.campaigns.createIndex({"detection_date": -1})
db.campaigns.createIndex({"status": 1})
db.campaigns.createIndex({"coordination_score": -1})

db.users.createIndex({"username": 1}, {"unique": true})
db.users.createIndex({"email": 1}, {"unique": true})
```

#### PostgreSQL Configuration

```sql
-- /etc/postgresql/14/main/postgresql.conf key settings
-- Memory Configuration
shared_buffers = 8GB
effective_cache_size = 24GB
work_mem = 256MB
maintenance_work_mem = 2GB

-- Connection Configuration
max_connections = 200
shared_preload_libraries = 'pg_stat_statements'

-- Performance Configuration
random_page_cost = 1.1
effective_io_concurrency = 200
max_worker_processes = 16
max_parallel_workers_per_gather = 4
```

**Database Optimization**
```sql
-- Create optimized indexes
CREATE INDEX CONCURRENTLY idx_alerts_created_at ON alerts(created_at DESC);
CREATE INDEX CONCURRENTLY idx_alerts_status ON alerts(status);
CREATE INDEX CONCURRENTLY idx_alerts_severity ON alerts(severity);
CREATE INDEX CONCURRENTLY idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX CONCURRENTLY idx_audit_logs_user_id ON audit_logs(user_id);

-- Configure autovacuum
ALTER TABLE alerts SET (autovacuum_vacuum_scale_factor = 0.1);
ALTER TABLE audit_logs SET (autovacuum_vacuum_scale_factor = 0.05);

-- Analyze tables for query optimization
ANALYZE alerts;
ANALYZE audit_logs;
ANALYZE users;
```

#### Elasticsearch Configuration

```yaml
# /etc/elasticsearch/elasticsearch.yml
cluster.name: dharma-cluster
node.name: dharma-node-1
path.data: /var/lib/elasticsearch
path.logs: /var/log/elasticsearch
network.host: 0.0.0.0
http.port: 9200
discovery.type: single-node

# Memory settings
bootstrap.memory_lock: true
# Set in /etc/elasticsearch/jvm.options:
# -Xms16g
# -Xmx16g

# Index settings
index.number_of_shards: 3
index.number_of_replicas: 1
index.refresh_interval: 30s
```

**Index Templates**
```json
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
          "analyzer": "dharma_analyzer"
        },
        "timestamp": {
          "type": "date"
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
}
```

#### Redis Configuration

```conf
# /etc/redis/redis.conf
bind 0.0.0.0
port 6379
timeout 300
tcp-keepalive 300

# Memory management
maxmemory 8gb
maxmemory-policy allkeys-lru
maxmemory-samples 5

# Persistence
save 900 1
save 300 10
save 60 10000
rdbcompression yes
rdbchecksum yes

# Logging
loglevel notice
logfile /var/log/redis/redis-server.log

# Security
requirepass your_redis_password
```

### Security Configuration

#### SSL/TLS Configuration

```nginx
# /etc/nginx/sites-available/dharma
server {
    listen 443 ssl http2;
    server_name dharma.yourdomain.com;

    ssl_certificate /etc/ssl/certs/dharma.crt;
    ssl_certificate_key /etc/ssl/private/dharma.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Firewall Configuration

```bash
# UFW firewall rules
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH
sudo ufw allow ssh

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow internal services (adjust IP ranges as needed)
sudo ufw allow from 10.0.0.0/8 to any port 5432  # PostgreSQL
sudo ufw allow from 10.0.0.0/8 to any port 27017 # MongoDB
sudo ufw allow from 10.0.0.0/8 to any port 9200  # Elasticsearch
sudo ufw allow from 10.0.0.0/8 to any port 6379  # Redis

# Enable firewall
sudo ufw enable
```

#### Authentication and Authorization

```python
# Authentication configuration
AUTH_CONFIG = {
    "jwt": {
        "secret_key": os.getenv("JWT_SECRET_KEY"),
        "algorithm": "HS256",
        "access_token_expire_minutes": 30,
        "refresh_token_expire_days": 7
    },
    "password": {
        "min_length": 12,
        "require_uppercase": True,
        "require_lowercase": True,
        "require_numbers": True,
        "require_special": True,
        "bcrypt_rounds": 12
    },
    "session": {
        "timeout_minutes": 60,
        "max_concurrent_sessions": 3,
        "secure_cookies": True
    },
    "mfa": {
        "enabled": True,
        "totp_issuer": "Project Dharma",
        "backup_codes_count": 10
    }
}

# Role-based access control
RBAC_CONFIG = {
    "roles": {
        "admin": {
            "permissions": ["*"],
            "description": "Full system access"
        },
        "analyst": {
            "permissions": [
                "dashboard:read",
                "campaigns:read",
                "alerts:read",
                "alerts:acknowledge",
                "investigations:create",
                "investigations:read",
                "investigations:update"
            ],
            "description": "Standard analyst access"
        },
        "viewer": {
            "permissions": [
                "dashboard:read",
                "campaigns:read",
                "alerts:read"
            ],
            "description": "Read-only access"
        }
    }
}
```

## Monitoring and Alerting Configuration

### Prometheus Configuration

```yaml
# /etc/prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"
  - "recording_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  - job_name: 'dharma-services'
    static_configs:
      - targets:
        - 'api-gateway:8000'
        - 'data-collection:8001'
        - 'ai-analysis:8002'
        - 'alert-management:8003'
        - 'dashboard:8004'
    metrics_path: /metrics
    scrape_interval: 30s

  - job_name: 'infrastructure'
    static_configs:
      - targets:
        - 'node-exporter:9100'
        - 'mongodb-exporter:9216'
        - 'postgres-exporter:9187'
        - 'elasticsearch-exporter:9114'
        - 'redis-exporter:9121'
```

### Grafana Configuration

```yaml
# /etc/grafana/grafana.ini
[server]
protocol = https
http_port = 3000
cert_file = /etc/ssl/certs/grafana.crt
cert_key = /etc/ssl/private/grafana.key

[database]
type = postgres
host = postgresql:5432
name = grafana
user = grafana
password = ${GRAFANA_DB_PASSWORD}

[auth]
disable_login_form = false
oauth_auto_login = false

[auth.ldap]
enabled = false

[smtp]
enabled = true
host = smtp.yourdomain.com:587
user = grafana@yourdomain.com
password = ${SMTP_PASSWORD}
from_address = grafana@yourdomain.com
```

### ELK Stack Configuration

#### Logstash Configuration

```ruby
# /etc/logstash/conf.d/dharma.conf
input {
  beats {
    port => 5044
  }
  
  kafka {
    bootstrap_servers => "kafka:9092"
    topics => ["dharma-logs"]
    codec => json
  }
}

filter {
  if [fields][service] {
    mutate {
      add_field => { "service_name" => "%{[fields][service]}" }
    }
  }
  
  if [message] =~ /^\{.*\}$/ {
    json {
      source => "message"
    }
  }
  
  date {
    match => [ "timestamp", "ISO8601" ]
  }
  
  mutate {
    remove_field => [ "host", "agent", "ecs", "input" ]
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "dharma-logs-%{+YYYY.MM.dd}"
    template_name => "dharma-logs"
    template => "/etc/logstash/templates/dharma-logs-template.json"
    template_overwrite => true
  }
}
```

#### Kibana Configuration

```yaml
# /etc/kibana/kibana.yml
server.port: 5601
server.host: "0.0.0.0"
elasticsearch.hosts: ["http://elasticsearch:9200"]
kibana.index: ".kibana"

# Security
server.ssl.enabled: true
server.ssl.certificate: /etc/ssl/certs/kibana.crt
server.ssl.key: /etc/ssl/private/kibana.key

# Logging
logging.dest: /var/log/kibana/kibana.log
logging.level: info
```

## Performance Optimization

### Database Performance Tuning

#### MongoDB Optimization

```javascript
// Performance monitoring queries
db.runCommand({serverStatus: 1})
db.runCommand({collStats: "posts"})
db.posts.getIndexes()

// Optimization commands
db.posts.createIndex({"timestamp": -1}, {background: true})
db.runCommand({compact: "posts"})
db.runCommand({planCacheClear: "posts"})

// Sharding configuration
sh.enableSharding("dharma_platform")
sh.shardCollection("dharma_platform.posts", {"platform": 1, "timestamp": 1})
```

#### PostgreSQL Optimization

```sql
-- Performance analysis
SELECT * FROM pg_stat_activity WHERE state = 'active';
SELECT * FROM pg_stat_user_tables ORDER BY seq_tup_read DESC;
SELECT * FROM pg_stat_user_indexes ORDER BY idx_tup_read DESC;

-- Query optimization
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM alerts WHERE created_at > NOW() - INTERVAL '1 day';

-- Maintenance tasks
VACUUM ANALYZE alerts;
REINDEX INDEX CONCURRENTLY idx_alerts_created_at;
```

#### Elasticsearch Optimization

```bash
# Cluster health monitoring
curl -X GET "elasticsearch:9200/_cluster/health?pretty"
curl -X GET "elasticsearch:9200/_cat/indices?v"
curl -X GET "elasticsearch:9200/_cat/shards?v"

# Index optimization
curl -X POST "elasticsearch:9200/dharma-posts-*/_forcemerge?max_num_segments=1"
curl -X PUT "elasticsearch:9200/dharma-posts-*/_settings" -H 'Content-Type: application/json' -d'
{
  "index": {
    "refresh_interval": "30s",
    "number_of_replicas": 1
  }
}'
```

### Application Performance Tuning

#### Connection Pool Configuration

```python
# Database connection pools
DATABASE_POOLS = {
    "mongodb": {
        "maxPoolSize": 50,
        "minPoolSize": 5,
        "maxIdleTimeMS": 30000,
        "waitQueueTimeoutMS": 5000,
        "serverSelectionTimeoutMS": 5000
    },
    "postgresql": {
        "max_connections": 20,
        "min_connections": 5,
        "max_idle": 300,
        "max_lifetime": 3600
    },
    "redis": {
        "max_connections": 50,
        "retry_on_timeout": True,
        "health_check_interval": 30
    }
}
```

#### Caching Strategy

```python
# Cache configuration
CACHE_CONFIG = {
    "default_ttl": 3600,  # 1 hour
    "policies": {
        "user_profiles": {"ttl": 1800, "max_size": 10000},
        "sentiment_results": {"ttl": 86400, "max_size": 100000},
        "campaign_data": {"ttl": 3600, "max_size": 50000},
        "dashboard_metrics": {"ttl": 300, "max_size": 1000}
    },
    "invalidation": {
        "enabled": True,
        "patterns": {
            "user_update": ["user:*", "dashboard:user:*"],
            "model_update": ["analysis:*"],
            "campaign_update": ["campaign:*", "dashboard:campaign:*"]
        }
    }
}
```

## Backup and Recovery

### Backup Configuration

#### Automated Backup Script

```bash
#!/bin/bash
# /opt/dharma/scripts/backup.sh

BACKUP_DIR="/backup/dharma"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Create backup directory
mkdir -p $BACKUP_DIR/$DATE

# MongoDB backup
mongodump --uri="mongodb://mongodb:27017/dharma_platform" --out=$BACKUP_DIR/$DATE/mongodb/

# PostgreSQL backup
pg_dump -h postgresql -U dharma_user dharma_db > $BACKUP_DIR/$DATE/postgresql_backup.sql

# Elasticsearch backup
curl -X PUT "elasticsearch:9200/_snapshot/dharma_backup/$DATE" -H 'Content-Type: application/json' -d'
{
  "indices": "dharma-*",
  "ignore_unavailable": true,
  "include_global_state": false
}'

# Redis backup
redis-cli --rdb $BACKUP_DIR/$DATE/redis_backup.rdb

# Configuration backup
tar -czf $BACKUP_DIR/$DATE/config_backup.tar.gz /opt/dharma/config/

# Compress backup
tar -czf $BACKUP_DIR/dharma_backup_$DATE.tar.gz $BACKUP_DIR/$DATE/
rm -rf $BACKUP_DIR/$DATE/

# Clean old backups
find $BACKUP_DIR -name "dharma_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete

# Upload to cloud storage (optional)
# aws s3 cp $BACKUP_DIR/dharma_backup_$DATE.tar.gz s3://dharma-backups/
```

#### Backup Verification

```bash
#!/bin/bash
# /opt/dharma/scripts/verify_backup.sh

BACKUP_FILE=$1
TEMP_DIR="/tmp/backup_verify"

# Extract backup
mkdir -p $TEMP_DIR
tar -xzf $BACKUP_FILE -C $TEMP_DIR

# Verify MongoDB backup
mongorestore --dry-run --dir=$TEMP_DIR/mongodb/dharma_platform/

# Verify PostgreSQL backup
pg_restore --list $TEMP_DIR/postgresql_backup.sql > /dev/null

# Verify Elasticsearch snapshot
curl -X GET "elasticsearch:9200/_snapshot/dharma_backup/_all"

# Cleanup
rm -rf $TEMP_DIR

echo "Backup verification completed for $BACKUP_FILE"
```

### Disaster Recovery Procedures

#### Recovery Planning

```yaml
# disaster_recovery_plan.yml
recovery_objectives:
  rto: 4 hours  # Recovery Time Objective
  rpo: 1 hour   # Recovery Point Objective

recovery_procedures:
  database_recovery:
    mongodb:
      - Stop MongoDB service
      - Restore data from backup
      - Restart MongoDB service
      - Verify data integrity
    postgresql:
      - Stop PostgreSQL service
      - Restore database from backup
      - Restart PostgreSQL service
      - Run integrity checks
    elasticsearch:
      - Stop Elasticsearch service
      - Restore indices from snapshot
      - Restart Elasticsearch service
      - Verify cluster health

  application_recovery:
    - Deploy application containers
    - Restore configuration files
    - Update DNS records
    - Verify service health
    - Resume data collection

  verification_steps:
    - Check all services are running
    - Verify data integrity
    - Test critical workflows
    - Monitor system performance
    - Notify stakeholders
```

## Maintenance Procedures

### Regular Maintenance Tasks

#### Daily Tasks

```bash
#!/bin/bash
# /opt/dharma/scripts/daily_maintenance.sh

# Check system health
systemctl status docker
docker ps --filter "status=exited"

# Check disk space
df -h | grep -E "(8[0-9]|9[0-9])%"

# Check log file sizes
find /var/log -name "*.log" -size +1G

# Database maintenance
mongo --eval "db.runCommand({serverStatus: 1})"
psql -h postgresql -U dharma_user -d dharma_db -c "SELECT pg_database_size('dharma_db');"

# Clean temporary files
find /tmp -name "dharma_*" -mtime +1 -delete

# Update system metrics
/opt/dharma/scripts/collect_metrics.sh
```

#### Weekly Tasks

```bash
#!/bin/bash
# /opt/dharma/scripts/weekly_maintenance.sh

# Database optimization
mongo --eval "db.posts.reIndex()"
psql -h postgresql -U dharma_user -d dharma_db -c "VACUUM ANALYZE;"

# Log rotation
logrotate /etc/logrotate.d/dharma

# Security updates
apt list --upgradable | grep -i security

# Performance analysis
/opt/dharma/scripts/performance_report.sh

# Backup verification
/opt/dharma/scripts/verify_latest_backup.sh
```

#### Monthly Tasks

```bash
#!/bin/bash
# /opt/dharma/scripts/monthly_maintenance.sh

# Full system backup
/opt/dharma/scripts/full_backup.sh

# Security audit
/opt/dharma/scripts/security_audit.sh

# Performance optimization
/opt/dharma/scripts/optimize_databases.sh

# Update documentation
/opt/dharma/scripts/update_system_docs.sh

# Capacity planning review
/opt/dharma/scripts/capacity_analysis.sh
```

### Troubleshooting Procedures

#### Service Health Checks

```bash
#!/bin/bash
# /opt/dharma/scripts/health_check.sh

echo "=== Project Dharma Health Check ==="

# Check Docker services
echo "Docker Services:"
docker-compose ps

# Check database connections
echo "Database Connectivity:"
mongo --eval "db.runCommand({ping: 1})" --quiet && echo "MongoDB: OK" || echo "MongoDB: FAILED"
pg_isready -h postgresql -p 5432 && echo "PostgreSQL: OK" || echo "PostgreSQL: FAILED"
redis-cli ping && echo "Redis: OK" || echo "Redis: FAILED"
curl -s elasticsearch:9200/_cluster/health | jq '.status' && echo "Elasticsearch: OK" || echo "Elasticsearch: FAILED"

# Check API endpoints
echo "API Endpoints:"
curl -s -o /dev/null -w "%{http_code}" http://api-gateway:8000/health && echo "API Gateway: OK" || echo "API Gateway: FAILED"
curl -s -o /dev/null -w "%{http_code}" http://data-collection:8001/health && echo "Data Collection: OK" || echo "Data Collection: FAILED"
curl -s -o /dev/null -w "%{http_code}" http://ai-analysis:8002/health && echo "AI Analysis: OK" || echo "AI Analysis: FAILED"

# Check system resources
echo "System Resources:"
echo "CPU Usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
echo "Memory Usage: $(free | grep Mem | awk '{printf("%.1f%%", $3/$2 * 100.0)}')"
echo "Disk Usage: $(df -h / | awk 'NR==2{printf "%s", $5}')"
```

This system configuration guide provides comprehensive instructions for setting up, configuring, and maintaining the Project Dharma platform. Regular review and updates of these configurations ensure optimal system performance and security.