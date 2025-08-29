# API Gateway Service

Handles authentication, request routing, rate limiting, and API documentation.

## Features

- OAuth2 JWT authentication
- Role-based access control (RBAC)
- Rate limiting with Redis backend
- Request routing to microservices
- OpenAPI documentation

## API Endpoints

- `POST /auth/login` - User authentication
- `POST /auth/refresh` - Token refresh
- `GET /docs` - API documentation
- All service endpoints proxied through gateway