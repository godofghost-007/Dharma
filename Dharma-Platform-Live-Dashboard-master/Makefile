# Project Dharma Makefile

.PHONY: help install test lint format clean build up down logs shell

# Default target
help:
	@echo "Available commands:"
	@echo "  install     - Install dependencies and setup development environment"
	@echo "  test        - Run all tests"
	@echo "  lint        - Run linting checks"
	@echo "  format      - Format code with black and isort"
	@echo "  clean       - Clean up temporary files and caches"
	@echo "  build       - Build all Docker images"
	@echo "  up          - Start all services with docker-compose"
	@echo "  down        - Stop all services"
	@echo "  logs        - Show logs from all services"
	@echo "  shell       - Open shell in a service container"

# Development setup
install:
	pip install -r requirements.txt
	pre-commit install
	@echo "Development environment setup complete!"

# Testing
test:
	pytest tests/ -v --cov=services --cov=shared --cov-report=html --cov-report=term

test-fast:
	pytest tests/ -v -x

# Code quality
lint:
	flake8 services/ shared/ tests/
	mypy services/ shared/ --ignore-missing-imports
	bandit -r services/ shared/ -f json -o bandit-report.json

format:
	black services/ shared/ tests/
	isort services/ shared/ tests/

# Cleanup
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -f bandit-report.json

# Docker operations
build:
	./scripts/docker-build.sh

build-service:
	@if [ -z "$(SERVICE)" ]; then echo "Usage: make build-service SERVICE=<service-name>"; exit 1; fi
	docker build -t dharma/$(SERVICE):latest ./services/$(SERVICE)

# Docker Compose operations
up:
	docker-compose up -d

up-build:
	docker-compose up -d --build

down:
	docker-compose down

down-volumes:
	docker-compose down -v

logs:
	docker-compose logs -f

logs-service:
	@if [ -z "$(SERVICE)" ]; then echo "Usage: make logs-service SERVICE=<service-name>"; exit 1; fi
	docker-compose logs -f $(SERVICE)

# Development utilities
shell:
	@if [ -z "$(SERVICE)" ]; then echo "Usage: make shell SERVICE=<service-name>"; exit 1; fi
	docker-compose exec $(SERVICE) /bin/bash

shell-db:
	docker-compose exec mongodb mongosh

shell-redis:
	docker-compose exec redis redis-cli

shell-postgres:
	docker-compose exec postgresql psql -U dharma_user -d dharma

# Database operations
init-db:
	docker-compose exec mongodb mongosh dharma_platform /docker-entrypoint-initdb.d/01-init-database.js
	docker-compose exec postgresql psql -U dharma_user -d dharma -f /docker-entrypoint-initdb.d/01-init-schema.sql

reset-db:
	docker-compose down -v
	docker-compose up -d mongodb postgresql redis elasticsearch
	sleep 10
	make init-db

# Monitoring
status:
	docker-compose ps

health:
	@echo "Checking service health..."
	@curl -f http://localhost:8000/health || echo "Data Collection Service: DOWN"
	@curl -f http://localhost:8001/health || echo "AI Analysis Service: DOWN"
	@curl -f http://localhost:8080/health || echo "API Gateway: DOWN"
	@curl -f http://localhost:8501/health || echo "Dashboard: DOWN"

# Production operations
deploy-staging:
	@echo "Deploying to staging..."
	# Add staging deployment commands

deploy-prod:
	@echo "Deploying to production..."
	# Add production deployment commands

# Security
security-scan:
	safety check
	bandit -r services/ shared/
	trivy fs .

# Documentation
docs:
	@echo "Generating documentation..."
	# Add documentation generation commands