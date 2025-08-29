#!/bin/bash

# Build all Docker images for Project Dharma services

set -e

echo "Building Project Dharma Docker images..."

# Build services
services=(
    "data-collection-service"
    "ai-analysis-service"
    "api-gateway-service"
    "dashboard-service"
)

for service in "${services[@]}"; do
    echo "Building $service..."
    docker build -t "dharma/$service:latest" "./services/$service"
    echo "✓ Built $service"
done

echo "All Docker images built successfully!"

# Optional: Tag images for registry
if [ "$1" = "--tag-registry" ]; then
    REGISTRY=${2:-"your-registry.com"}
    for service in "${services[@]}"; do
        docker tag "dharma/$service:latest" "$REGISTRY/dharma/$service:latest"
        echo "✓ Tagged $service for registry $REGISTRY"
    done
fi