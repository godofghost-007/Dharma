# Collaboration Service

Team coordination and knowledge sharing service for Project Dharma.

## Features

- Shared workspaces and investigation templates
- Collaborative annotations and case management  
- Team coordination and workflow management
- Knowledge sharing and documentation

## API Endpoints

- `GET /health` - Health check
- `POST /workspaces` - Create workspace
- `GET /workspaces` - List workspaces
- `POST /annotations` - Create annotation
- `GET /cases` - List cases

## Configuration

Set environment variables:
- `MONGODB_URL` - MongoDB connection string
- `REDIS_URL` - Redis connection string

## Usage

```bash
# Start service
python main.py

# Or with Docker
docker build -t collaboration-service .
docker run -p 8006:8006 collaboration-service
```