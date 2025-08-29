# Docker Deployment Guide

This guide explains how to deploy the Dharma platform with secure credential management using Docker.

## Environment Configuration

### Development Deployment

1. **Copy environment template:**
   ```bash
   cp .env.template .env
   ```

2. **Update credentials in .env:**
   - Add your actual Twitter API credentials
   - Add your YouTube API key
   - Add your Telegram bot token
   - Update JWT and encryption keys

3. **Deploy with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

### Production Deployment

#### Option 1: Environment Variables (Recommended for most cases)

1. **Copy production environment template:**
   ```bash
   cp .env.prod.template .env.prod
   ```

2. **Update production credentials in .env.prod**

3. **Deploy with production configuration:**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

#### Option 2: Docker Secrets (Recommended for Docker Swarm)

1. **Initialize Docker Swarm:**
   ```bash
   docker swarm init
   ```

2. **Set up environment variables:**
   ```bash
   export TWITTER_API_KEY="your_twitter_api_key"
   export TWITTER_API_SECRET="your_twitter_api_secret"
   # ... set all other credentials
   ```

3. **Create Docker secrets:**
   ```bash
   chmod +x scripts/setup_docker_secrets.sh
   ./scripts/setup_docker_secrets.sh
   ```

4. **Deploy with secrets:**
   ```bash
   docker stack deploy -c docker-compose.yml -c docker-compose.prod.yml -c docker-compose.secrets.yml dharma
   ```

## Credential Validation

All containers include automatic credential validation on startup:

- **Environment variables** are validated before service startup
- **API credentials** are tested for accessibility
- **Docker secrets** are loaded if available
- **Service dependencies** are checked

### Manual Validation

You can manually validate credentials:

```bash
# Test credential validation
python scripts/validate_credentials.py

# Test full startup validation
python scripts/docker_startup_check.py
```

## Health Checks

All services include health checks that validate:
- Service availability
- Credential accessibility
- Environment configuration

Monitor health status:
```bash
docker-compose ps
```

## Troubleshooting

### Common Issues

1. **Credential validation fails:**
   - Check that all required environment variables are set
   - Verify API credentials are valid
   - Check file permissions for Docker secrets

2. **Service startup fails:**
   - Check container logs: `docker-compose logs <service-name>`
   - Verify dependencies are running
   - Check network connectivity

3. **Docker secrets not loading:**
   - Ensure Docker Swarm is initialized
   - Verify secrets exist: `docker secret ls`
   - Check secret file permissions

### Logs and Monitoring

View service logs:
```bash
# All services
docker-compose logs

# Specific service
docker-compose logs data-collection-service

# Follow logs
docker-compose logs -f
```

## Security Best Practices

1. **Never commit .env files** to version control
2. **Use Docker secrets** for production deployments
3. **Rotate credentials regularly**
4. **Monitor credential usage** through logs
5. **Use least privilege** for API access

## Deployment Commands Reference

```bash
# Development
docker-compose up -d

# Production with environment files
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Production with Docker secrets (Swarm mode)
docker stack deploy -c docker-compose.yml -c docker-compose.prod.yml -c docker-compose.secrets.yml dharma

# Stop services
docker-compose down

# Remove secrets (Swarm mode)
docker secret ls --filter 'name=dharma_' --format '{{.Name}}' | xargs docker secret rm

# Rebuild and restart
docker-compose up -d --build
```