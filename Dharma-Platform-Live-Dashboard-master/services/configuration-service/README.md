# Configuration Service

Manages service discovery, feature flags, and centralized configuration.

## Features

- Service registry and discovery
- Feature flag management
- Secrets management
- Configuration versioning

## API Endpoints

- `GET /services` - List registered services
- `GET /config/{service}` - Get service configuration
- `POST /features/toggle` - Toggle feature flags
- `GET /health` - Service health check