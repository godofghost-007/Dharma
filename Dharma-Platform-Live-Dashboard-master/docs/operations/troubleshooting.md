# Troubleshooting Guide

## Overview

This guide provides solutions to common issues encountered in the Project Dharma platform. Issues are organized by category with step-by-step resolution procedures.

## Quick Diagnostics

### System Health Check
```bash
# Check all service health
curl -s http://localhost:8000/health | jq '.'

# Check database connectivity
python scripts/check_databases.py

# Verify Kafka cluster
docker-compose exec kafka kafka-broker-api-versions.sh --bootstrap-server localhost:9092

# Check Redis cluster
docker-compose exec redis redis-cli cluster info
```

### Service Status Overview
```bash
# Docker services status
docker-compose ps

# Kubernetes pods status (if using K8s)
kubectl get pods -n dharma-platform

# Check service logs
docker-compose logs --tail=50 -f api-gateway-service
```

## Common Issues

### 1. Service Startup Issues

#### Problem: Service fails to start with database connection error
**Symptoms:**
- Service exits immediately after startup
- Error logs show database connection timeout
- Health check endpoints return 503

**Diagnosis:**
```bash
# Check database container status
docker-compose ps mongodb postgresql redis

# Test database connectivity
telnet localhost 27017  # MongoDB
telnet localhost 5432   # PostgreSQL
telnet localhost 6379   # Redis

# Check database logs
docker-compose logs mongodb
```

**Resolution:**
```bash
# Restart database services
docker-compose restart mongodb postgresql redis

# Wait for databases to be ready
./scripts/wait-for-databases.sh

# Restart application services
docker-compose restart api-gateway-service data-collection-service
```

#### Problem: Port already in use error
**Symptoms:**
- Docker compose fails with "port already allocated"
- Service cannot bind to specified port

**Diagnosis:**
```bash
# Check what's using the port
lsof -i :8000
netstat -tulpn | grep :8000

# Check Docker port mappings
docker ps --format "table {{.Names}}\t{{.Ports}}"
```

**Resolution:**
```bash
# Kill process using the port
sudo kill -9 <PID>

# Or change port in docker-compose.yml
# ports:
#   - "8001:8000"  # Use different external port

# Restart services
docker-compose up -d
```##
# 2. API Gateway Issues

#### Problem: Authentication failures (401 Unauthorized)
**Symptoms:**
- All API requests return 401 status
- Valid JWT tokens are rejected
- Login endpoint not working

**Diagnosis:**
```bash
# Check JWT secret configuration
docker-compose exec api-gateway-service env | grep JWT

# Verify user database
docker-compose exec postgresql psql -U dharma -d dharma_platform -c "SELECT * FROM users LIMIT 5;"

# Test login endpoint directly
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

**Resolution:**
```bash
# Reset JWT secret (will invalidate all tokens)
docker-compose exec api-gateway-service python -c "
import secrets
print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))
" >> .env

# Restart API gateway
docker-compose restart api-gateway-service

# Create admin user if missing
docker-compose exec api-gateway-service python scripts/create_admin_user.py
```

#### Problem: Rate limiting blocking legitimate requests
**Symptoms:**
- API returns 429 Too Many Requests
- Requests blocked even with low traffic
- Rate limit headers show exhausted quota

**Diagnosis:**
```bash
# Check Redis rate limit keys
docker-compose exec redis redis-cli keys "rate_limit:*"

# View current rate limit values
docker-compose exec redis redis-cli get "rate_limit:user:123"

# Check rate limiting configuration
docker-compose exec api-gateway-service env | grep RATE_LIMIT
```

**Resolution:**
```bash
# Clear rate limit cache
docker-compose exec redis redis-cli flushdb

# Adjust rate limits in configuration
# Edit docker-compose.yml or .env file:
# RATE_LIMIT_PER_MINUTE=2000

# Restart API gateway
docker-compose restart api-gateway-service
```

### 3. Data Collection Issues

#### Problem: Twitter API rate limit exceeded
**Symptoms:**
- Twitter collector stops collecting data
- Error logs show "Rate limit exceeded"
- No new Twitter posts in database

**Diagnosis:**
```bash
# Check Twitter API credentials
docker-compose exec data-collection-service env | grep TWITTER

# View collector logs
docker-compose logs data-collection-service | grep -i twitter

# Check rate limit status
curl -H "Authorization: Bearer $TWITTER_BEARER_TOKEN" \
  "https://api.twitter.com/2/tweets/search/recent?query=test&max_results=10"
```

**Resolution:**
```bash
# Wait for rate limit reset (15 minutes for most endpoints)
# Or implement exponential backoff in collector

# Add multiple API keys for rotation
# Edit .env file:
# TWITTER_API_KEYS=key1,key2,key3

# Restart data collection service
docker-compose restart data-collection-service
```

#### Problem: Kafka message queue backup
**Symptoms:**
- High memory usage in Kafka containers
- Slow data processing
- Consumer lag increasing

**Diagnosis:**
```bash
# Check Kafka topics and lag
docker-compose exec kafka kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 --describe --all-groups

# Check topic sizes
docker-compose exec kafka kafka-log-dirs.sh \
  --bootstrap-server localhost:9092 --describe

# Monitor Kafka metrics
curl http://localhost:9092/metrics
```

**Resolution:**
```bash
# Increase consumer instances
docker-compose up --scale stream-processing-service=3

# Adjust Kafka retention settings
docker-compose exec kafka kafka-configs.sh \
  --bootstrap-server localhost:9092 \
  --entity-type topics \
  --entity-name social-media-posts \
  --alter --add-config retention.ms=86400000

# Clear old messages if needed (CAUTION: Data loss)
docker-compose exec kafka kafka-delete-records.sh \
  --bootstrap-server localhost:9092 \
  --offset-json-file delete-records.json
```

### 4. AI Analysis Issues

#### Problem: Sentiment analysis model not loading
**Symptoms:**
- AI analysis service fails to start
- Error about missing model files
- Analysis requests timeout

**Diagnosis:**
```bash
# Check model files
docker-compose exec ai-analysis-service ls -la /app/models/

# Check GPU availability (if using GPU)
docker-compose exec ai-analysis-service nvidia-smi

# View model loading logs
docker-compose logs ai-analysis-service | grep -i model
```

**Resolution:**
```bash
# Download missing models
docker-compose exec ai-analysis-service python scripts/download_models.py

# Or mount models from host
# Add to docker-compose.yml:
# volumes:
#   - ./models:/app/models:ro

# Restart AI service
docker-compose restart ai-analysis-service
```

#### Problem: High memory usage in AI service
**Symptoms:**
- AI service container killed by OOM
- Slow analysis response times
- Memory usage continuously increasing

**Diagnosis:**
```bash
# Check container memory usage
docker stats ai-analysis-service

# Monitor Python memory usage
docker-compose exec ai-analysis-service python -c "
import psutil
print(f'Memory: {psutil.virtual_memory().percent}%')
print(f'Available: {psutil.virtual_memory().available / 1024**3:.2f} GB')
"

# Check for memory leaks
docker-compose exec ai-analysis-service python scripts/memory_profiler.py
```

**Resolution:**
```bash
# Increase container memory limit
# Edit docker-compose.yml:
# deploy:
#   resources:
#     limits:
#       memory: 4G

# Enable batch processing to reduce memory usage
# Edit AI service configuration:
# BATCH_SIZE=32
# MAX_CONCURRENT_REQUESTS=4

# Restart with new limits
docker-compose up -d ai-analysis-service
```

### 5. Database Issues

#### Problem: MongoDB connection pool exhausted
**Symptoms:**
- "No available connections" errors
- Slow database operations
- Connection timeout errors

**Diagnosis:**
```bash
# Check MongoDB connection stats
docker-compose exec mongodb mongo --eval "db.serverStatus().connections"

# Monitor active connections
docker-compose exec mongodb mongo --eval "
db.runCommand({currentOp: true, $all: true}).inprog.forEach(
  function(op) { 
    if(op.secs_running > 5) print(JSON.stringify(op, null, 2)); 
  }
)"

# Check connection pool configuration
docker-compose exec api-gateway-service env | grep MONGO
```

**Resolution:**
```bash
# Increase connection pool size
# Edit .env file:
# MONGODB_MAX_POOL_SIZE=100
# MONGODB_MIN_POOL_SIZE=10

# Kill long-running operations
docker-compose exec mongodb mongo --eval "
db.runCommand({killOp: 1, op: <operation_id>})
"

# Restart services to reset connections
docker-compose restart api-gateway-service ai-analysis-service
```

#### Problem: PostgreSQL deadlocks
**Symptoms:**
- "Deadlock detected" errors in logs
- Transactions timing out
- Alert management operations failing

**Diagnosis:**
```bash
# Check for deadlocks in PostgreSQL logs
docker-compose logs postgresql | grep -i deadlock

# Monitor active queries
docker-compose exec postgresql psql -U dharma -d dharma_platform -c "
SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
FROM pg_stat_activity 
WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';
"

# Check lock information
docker-compose exec postgresql psql -U dharma -d dharma_platform -c "
SELECT * FROM pg_locks WHERE NOT granted;
"
```

**Resolution:**
```bash
# Kill blocking queries
docker-compose exec postgresql psql -U dharma -d dharma_platform -c "
SELECT pg_terminate_backend(pid) FROM pg_stat_activity 
WHERE (now() - pg_stat_activity.query_start) > interval '10 minutes';
"

# Optimize queries causing deadlocks
# Review and add appropriate indexes
# Implement retry logic with exponential backoff

# Restart PostgreSQL if needed
docker-compose restart postgresql
```

### 6. Dashboard Issues

#### Problem: Dashboard not loading or showing blank page
**Symptoms:**
- Streamlit dashboard shows white screen
- Browser console shows JavaScript errors
- Dashboard service returns 500 errors

**Diagnosis:**
```bash
# Check dashboard service logs
docker-compose logs dashboard-service

# Test dashboard API endpoints
curl http://localhost:8501/health

# Check browser console for errors
# Open browser developer tools (F12)

# Verify API connectivity from dashboard
docker-compose exec dashboard-service curl http://api-gateway-service:8000/health
```

**Resolution:**
```bash
# Clear browser cache and cookies
# Or try incognito/private browsing mode

# Restart dashboard service
docker-compose restart dashboard-service

# Check for missing environment variables
docker-compose exec dashboard-service env | grep API_

# Update dashboard dependencies
docker-compose exec dashboard-service pip install -r requirements.txt --upgrade
```

#### Problem: Real-time updates not working
**Symptoms:**
- Dashboard data doesn't refresh automatically
- WebSocket connections failing
- Metrics show stale data

**Diagnosis:**
```bash
# Check WebSocket connections
# Browser developer tools -> Network -> WS tab

# Test WebSocket endpoint
wscat -c ws://localhost:8501/ws

# Check Redis pub/sub for real-time events
docker-compose exec redis redis-cli monitor
```

**Resolution:**
```bash
# Restart dashboard service
docker-compose restart dashboard-service

# Check firewall/proxy settings for WebSocket support
# Ensure WebSocket upgrade headers are allowed

# Verify Redis pub/sub configuration
docker-compose exec redis redis-cli config get notify-keyspace-events
```

### 7. Performance Issues

#### Problem: High CPU usage across services
**Symptoms:**
- System becomes unresponsive
- API response times increase significantly
- Container CPU usage at 100%

**Diagnosis:**
```bash
# Check system resources
top
htop
docker stats

# Identify CPU-intensive processes
docker-compose exec <service> top

# Check for infinite loops or inefficient algorithms
docker-compose logs <service> | grep -i error
```

**Resolution:**
```bash
# Scale horizontally
docker-compose up --scale ai-analysis-service=3

# Optimize database queries
# Add appropriate indexes
# Use connection pooling

# Implement caching
# Enable Redis caching for frequently accessed data

# Profile and optimize code
# Use profiling tools to identify bottlenecks
```

#### Problem: Disk space running low
**Symptoms:**
- "No space left on device" errors
- Docker containers failing to start
- Log files growing rapidly

**Diagnosis:**
```bash
# Check disk usage
df -h
du -sh /var/lib/docker/

# Check Docker disk usage
docker system df

# Identify large log files
find /var/log -type f -size +100M -exec ls -lh {} \;
```

**Resolution:**
```bash
# Clean up Docker resources
docker system prune -a --volumes

# Rotate log files
docker-compose exec <service> logrotate /etc/logrotate.conf

# Configure log retention
# Edit docker-compose.yml:
# logging:
#   driver: "json-file"
#   options:
#     max-size: "10m"
#     max-file: "3"

# Archive old data
python scripts/archive_old_data.py --days 30
```

## Emergency Procedures

### Complete System Recovery
```bash
# 1. Stop all services
docker-compose down

# 2. Backup current data
python scripts/backup_all_databases.py

# 3. Clean up Docker resources
docker system prune -a --volumes

# 4. Restore from backup if needed
python scripts/restore_from_backup.py --backup-file latest_backup.tar.gz

# 5. Start services in order
docker-compose up -d mongodb postgresql redis
sleep 30
docker-compose up -d kafka
sleep 30
docker-compose up -d

# 6. Verify system health
python scripts/health_check_all.py
```

### Data Recovery Procedures
```bash
# MongoDB recovery
mongorestore --host localhost:27017 --db dharma_platform backup/mongodb/

# PostgreSQL recovery
docker-compose exec postgresql psql -U dharma -d dharma_platform < backup/postgresql/backup.sql

# Elasticsearch recovery
curl -X POST "localhost:9200/_snapshot/backup_repo/snapshot_1/_restore"
```

## Monitoring and Alerting

### Key Metrics to Monitor
- **Service Health**: HTTP health check endpoints
- **Database Performance**: Connection pool usage, query response times
- **Message Queue**: Kafka consumer lag, message throughput
- **Resource Usage**: CPU, memory, disk usage per service
- **Error Rates**: HTTP 5xx responses, exception counts

### Setting Up Alerts
```yaml
# Example Prometheus alert rules
groups:
  - name: dharma-platform
    rules:
      - alert: ServiceDown
        expr: up{job="dharma-services"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.instance }} is down"
      
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High error rate on {{ $labels.service }}"
```

## Getting Help

### Log Analysis
```bash
# Centralized log search (if ELK stack is running)
curl -X GET "localhost:9200/logs-*/_search" -H 'Content-Type: application/json' -d'
{
  "query": {
    "bool": {
      "must": [
        {"range": {"@timestamp": {"gte": "now-1h"}}},
        {"match": {"level": "ERROR"}}
      ]
    }
  }
}'

# Service-specific log analysis
docker-compose logs --since 1h api-gateway-service | grep ERROR
```

### Contact Information
- **On-call Engineer**: +91-XXXX-XXXX-XX
- **DevOps Team**: devops@dharma.gov.in
- **Security Team**: security@dharma.gov.in (for security incidents)
- **Escalation**: tech-lead@dharma.gov.in

### External Resources
- **Docker Documentation**: https://docs.docker.com/
- **Kubernetes Troubleshooting**: https://kubernetes.io/docs/tasks/debug-application-cluster/
- **MongoDB Operations**: https://docs.mongodb.com/manual/administration/
- **PostgreSQL Troubleshooting**: https://www.postgresql.org/docs/current/

Remember: Always backup data before making significant changes, and document any resolution steps for future reference.