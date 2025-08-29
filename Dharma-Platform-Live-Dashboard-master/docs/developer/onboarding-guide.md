# Developer Onboarding Guide

## Welcome to Project Dharma

This guide will help you get started with developing on the Project Dharma platform. Please follow the steps in order to set up your development environment and understand the codebase structure.

## Prerequisites

### Required Software
- **Python 3.11+**: Primary development language
- **Docker & Docker Compose**: For containerized development
- **Git**: Version control
- **Node.js 18+**: For frontend development and tooling
- **kubectl**: Kubernetes command-line tool
- **Helm**: Kubernetes package manager

### Recommended Tools
- **VS Code** with Python and Docker extensions
- **Postman** or **Insomnia** for API testing
- **MongoDB Compass** for database exploration
- **pgAdmin** for PostgreSQL management
- **Kibana** for log analysis

## Development Environment Setup

### 1. Clone the Repository
```bash
git clone https://github.com/your-org/project-dharma.git
cd project-dharma
```

### 2. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit environment variables
# Set your API keys, database credentials, etc.
nano .env
```

### 3. Install Dependencies
```bash
# Install Python dependencies
pip install -r requirements.txt

# Install pre-commit hooks
pre-commit install

# Install development tools
pip install -r requirements-dev.txt
```

### 4. Start Development Services
```bash
# Start all services with Docker Compose
docker-compose up -d

# Verify services are running
docker-compose ps

# Check service logs
docker-compose logs -f api-gateway-service
```

### 5. Database Setup
```bash
# Run database migrations
python scripts/migrate.py

# Seed development data (optional)
python scripts/seed_dev_data.py
```

### 6. Verify Installation
```bash
# Run health checks
curl http://localhost:8000/health

# Run basic tests
python -m pytest tests/unit/ -v

# Access dashboard
open http://localhost:8501
```

## Project Structure

```
project-dharma/
├── services/                    # Microservices
│   ├── api-gateway-service/     # API Gateway and authentication
│   ├── data-collection-service/ # Data collection from platforms
│   ├── ai-analysis-service/     # AI/ML analysis engine
│   ├── campaign-detection-service/ # Campaign detection
│   ├── alert-management-service/ # Alert generation and routing
│   ├── dashboard-service/       # Web dashboard
│   └── stream-processing-service/ # Real-time processing
├── shared/                      # Shared libraries and utilities
│   ├── models/                  # Pydantic data models
│   ├── database/               # Database connection utilities
│   ├── security/               # Security and encryption
│   ├── monitoring/             # Monitoring and observability
│   └── config/                 # Configuration management
├── infrastructure/             # Infrastructure as Code
│   ├── kubernetes/             # K8s manifests
│   ├── terraform/              # Infrastructure provisioning
│   ├── monitoring/             # Monitoring stack configs
│   └── elk/                    # Logging stack configs
├── tests/                      # Test suites
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── performance/            # Load and performance tests
├── docs/                       # Documentation
│   ├── api/                    # API documentation
│   ├── architecture/           # System architecture
│   ├── developer/              # Developer guides
│   └── operations/             # Operational runbooks
├── scripts/                    # Utility scripts
├── migrations/                 # Database migrations
└── docker-compose.yml          # Development environment
```

## Development Workflow

### 1. Feature Development Process
1. **Create Feature Branch**: `git checkout -b feature/your-feature-name`
2. **Write Tests First**: Follow TDD principles
3. **Implement Feature**: Write minimal code to pass tests
4. **Run Tests**: Ensure all tests pass
5. **Code Review**: Create pull request for review
6. **Merge**: Merge after approval and CI passes

### 2. Code Standards

#### Python Code Style
- **PEP 8** compliance enforced by `black` and `flake8`
- **Type hints** required for all function signatures
- **Docstrings** required for all public functions and classes
- **Maximum line length**: 88 characters (black default)

#### Example Code Structure
```python
from typing import List, Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

class DataModel(BaseModel):
    """Example data model with proper typing."""
    
    id: str
    name: str
    tags: List[str] = []
    metadata: Optional[dict] = None

async def process_data(data: DataModel) -> dict:
    """
    Process data and return results.
    
    Args:
        data: Input data model
        
    Returns:
        Processing results dictionary
        
    Raises:
        ValueError: If data validation fails
    """
    logger.info(f"Processing data for {data.id}")
    
    if not data.name:
        raise ValueError("Name is required")
    
    # Processing logic here
    result = {"status": "success", "processed_id": data.id}
    
    logger.info(f"Successfully processed {data.id}")
    return result
```

### 3. Testing Guidelines

#### Unit Tests
- **Coverage Target**: Minimum 80% code coverage
- **Test Structure**: Arrange, Act, Assert pattern
- **Mocking**: Use `pytest-mock` for external dependencies
- **Fixtures**: Use pytest fixtures for test data

#### Example Unit Test
```python
import pytest
from unittest.mock import AsyncMock, patch
from your_service.models import DataModel
from your_service.processor import process_data

@pytest.fixture
def sample_data():
    """Sample data fixture."""
    return DataModel(
        id="test-123",
        name="Test Data",
        tags=["test", "sample"]
    )

@pytest.mark.asyncio
async def test_process_data_success(sample_data):
    """Test successful data processing."""
    # Act
    result = await process_data(sample_data)
    
    # Assert
    assert result["status"] == "success"
    assert result["processed_id"] == "test-123"

@pytest.mark.asyncio
async def test_process_data_invalid_name():
    """Test data processing with invalid name."""
    # Arrange
    invalid_data = DataModel(id="test-456", name="")
    
    # Act & Assert
    with pytest.raises(ValueError, match="Name is required"):
        await process_data(invalid_data)
```

#### Integration Tests
- **Database Tests**: Use test database containers
- **API Tests**: Test complete request/response cycles
- **Service Integration**: Test service-to-service communication

### 4. Database Development

#### Migration Guidelines
- **Sequential Numbering**: Use sequential numbers for migration files
- **Rollback Support**: Always include rollback procedures
- **Data Migration**: Separate schema and data migrations
- **Testing**: Test migrations on copy of production data

#### Example Migration
```sql
-- migrations/postgresql/008_add_user_preferences.sql
-- Migration: Add user preferences table
-- Author: developer@dharma.gov.in
-- Date: 2024-01-15

BEGIN;

-- Create user preferences table
CREATE TABLE user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    preference_key VARCHAR(100) NOT NULL,
    preference_value JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, preference_key)
);

-- Create indexes
CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id);
CREATE INDEX idx_user_preferences_key ON user_preferences(preference_key);

-- Add trigger for updated_at
CREATE TRIGGER update_user_preferences_updated_at
    BEFORE UPDATE ON user_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMIT;

-- Rollback procedure:
-- DROP TABLE user_preferences CASCADE;
```

## Service Development Guidelines

### 1. Creating a New Service

#### Service Template Structure
```
new-service/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── core/
│   │   ├── config.py        # Service configuration
│   │   └── dependencies.py  # Dependency injection
│   ├── api/
│   │   └── routes.py        # API endpoints
│   ├── models/
│   │   └── schemas.py       # Pydantic models
│   └── services/
│       └── business_logic.py # Business logic
├── tests/
│   ├── test_api.py
│   └── test_services.py
├── Dockerfile
├── requirements.txt
└── README.md
```

#### Service Configuration Template
```python
# app/core/config.py
from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Service configuration settings."""
    
    # Service identification
    service_name: str = "new-service"
    service_version: str = "1.0.0"
    
    # API configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # Database configuration
    mongodb_url: str
    postgresql_url: str
    redis_url: str
    
    # External service URLs
    api_gateway_url: str
    
    # Security
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    
    # Monitoring
    enable_metrics: bool = True
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

### 2. API Development Standards

#### FastAPI Application Template
```python
# app/main.py
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import routes
from shared.monitoring.middleware import MetricsMiddleware
from shared.security.middleware import SecurityMiddleware

def create_app() -> FastAPI:
    """Create FastAPI application with middleware and routes."""
    
    app = FastAPI(
        title=f"{settings.service_name} API",
        version=settings.service_version,
        description="Service description here",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None
    )
    
    # Add middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(SecurityMiddleware)
    
    # Include routes
    app.include_router(routes.router, prefix="/api/v1")
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": settings.service_name}
    
    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
```

### 3. Error Handling Standards

#### Custom Exception Classes
```python
# app/core/exceptions.py
from fastapi import HTTPException
from typing import Optional, Dict, Any

class ServiceException(Exception):
    """Base exception for service-specific errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

class ValidationError(ServiceException):
    """Raised when input validation fails."""
    pass

class NotFoundError(ServiceException):
    """Raised when requested resource is not found."""
    pass

class ExternalServiceError(ServiceException):
    """Raised when external service call fails."""
    pass

# Exception handlers
from fastapi import Request
from fastapi.responses import JSONResponse

async def service_exception_handler(request: Request, exc: ServiceException):
    """Handle service-specific exceptions."""
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.message,
            "details": exc.details,
            "type": exc.__class__.__name__
        }
    )

async def not_found_exception_handler(request: Request, exc: NotFoundError):
    """Handle not found exceptions."""
    return JSONResponse(
        status_code=404,
        content={
            "error": exc.message,
            "details": exc.details
        }
    )
```

## Debugging and Troubleshooting

### 1. Local Development Debugging

#### VS Code Debug Configuration
```json
// .vscode/launch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug Service",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/services/your-service/app/main.py",
            "env": {
                "PYTHONPATH": "${workspaceFolder}",
                "DEBUG": "true"
            },
            "console": "integratedTerminal",
            "justMyCode": false
        }
    ]
}
```

#### Logging Configuration
```python
# shared/config/logging.py
import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logging(service_name: str, log_level: str = "INFO"):
    """Setup structured logging for service."""
    
    # Create formatter
    formatter = jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(name)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Setup handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(handler)
    
    # Add service context
    logging.getLogger().info(
        "Logging initialized",
        extra={"service": service_name, "log_level": log_level}
    )
```

### 2. Common Issues and Solutions

#### Database Connection Issues
```python
# Check database connectivity
async def check_database_connection():
    """Verify database connections are working."""
    try:
        # MongoDB check
        from shared.database.mongodb import get_mongodb_client
        mongo_client = await get_mongodb_client()
        await mongo_client.admin.command('ping')
        print("✓ MongoDB connection successful")
        
        # PostgreSQL check
        from shared.database.postgresql import get_postgresql_pool
        pg_pool = await get_postgresql_pool()
        async with pg_pool.acquire() as conn:
            await conn.fetchval('SELECT 1')
        print("✓ PostgreSQL connection successful")
        
        # Redis check
        from shared.database.redis import get_redis_client
        redis_client = await get_redis_client()
        await redis_client.ping()
        print("✓ Redis connection successful")
        
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        raise
```

#### Service Discovery Issues
```bash
# Check service registration
curl http://localhost:8500/v1/agent/services

# Check service health
curl http://localhost:8500/v1/health/service/your-service

# Debug DNS resolution
nslookup your-service.service.consul
```

#### Performance Debugging
```python
# Add performance monitoring
import time
import functools
from typing import Callable

def monitor_performance(func: Callable) -> Callable:
    """Decorator to monitor function performance."""
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            logging.info(
                f"Function {func.__name__} completed",
                extra={
                    "function": func.__name__,
                    "duration_ms": duration * 1000,
                    "status": "success"
                }
            )
            return result
        except Exception as e:
            duration = time.time() - start_time
            logging.error(
                f"Function {func.__name__} failed",
                extra={
                    "function": func.__name__,
                    "duration_ms": duration * 1000,
                    "status": "error",
                    "error": str(e)
                }
            )
            raise
    
    return wrapper
```

## Useful Commands

### Development Commands
```bash
# Start specific service
docker-compose up data-collection-service

# View service logs
docker-compose logs -f ai-analysis-service

# Run tests for specific service
python -m pytest services/api-gateway-service/tests/ -v

# Run linting
black services/
flake8 services/

# Run type checking
mypy services/your-service/

# Generate API documentation
python scripts/generate_api_docs.py
```

### Database Commands
```bash
# Connect to MongoDB
docker-compose exec mongodb mongo dharma_platform

# Connect to PostgreSQL
docker-compose exec postgresql psql -U dharma -d dharma_platform

# Run migrations
python scripts/migrate.py --target latest

# Backup database
python scripts/backup_database.py --output backup.sql
```

### Monitoring Commands
```bash
# Check service health
curl http://localhost:8000/health

# View metrics
curl http://localhost:8000/metrics

# Check Kafka topics
docker-compose exec kafka kafka-topics.sh --list --bootstrap-server localhost:9092

# View Redis keys
docker-compose exec redis redis-cli keys "*"
```

## Getting Help

### Internal Resources
- **Architecture Documentation**: `/docs/architecture/`
- **API Documentation**: `/docs/api/`
- **Troubleshooting Guide**: `/docs/operations/troubleshooting.md`
- **Code Examples**: `/examples/`

### Team Contacts
- **Tech Lead**: tech-lead@dharma.gov.in
- **DevOps Team**: devops@dharma.gov.in
- **Security Team**: security@dharma.gov.in

### External Resources
- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **Pydantic Documentation**: https://pydantic-docs.helpmanual.io/
- **Docker Documentation**: https://docs.docker.com/
- **Kubernetes Documentation**: https://kubernetes.io/docs/

## Next Steps

1. **Complete Environment Setup**: Ensure all services are running locally
2. **Run Test Suite**: Verify your setup by running the full test suite
3. **Explore Codebase**: Start with the service you'll be working on
4. **Read Architecture Docs**: Understand the overall system design
5. **Join Team Channels**: Connect with your team for ongoing support

Welcome to the team! 🚀