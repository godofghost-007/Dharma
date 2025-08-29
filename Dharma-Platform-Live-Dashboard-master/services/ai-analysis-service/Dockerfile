# Multi-stage build for AI Analysis Service
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies for ML libraries
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY services/ai-analysis-service/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Create non-root user
RUN groupadd -r dharma && useradd -r -g dharma dharma

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder stage
COPY --from=builder /root/.local /home/dharma/.local

# Copy shared modules first (from project root context)
COPY shared/ ./shared/

# Copy validation scripts
COPY scripts/validate_credentials.py ./scripts/
COPY scripts/docker_startup_check.py ./scripts/

# Copy application code
COPY services/ai-analysis-service/ .

# Create models directory
RUN mkdir -p /app/models && chown -R dharma:dharma /app
USER dharma

# Add local Python packages to PATH
ENV PATH=/home/dharma/.local/bin:$PATH

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Expose port
EXPOSE 8001

# Create startup script that validates environment before starting the service
RUN echo '#!/bin/bash\n\
set -e\n\
echo "🚀 Starting AI Analysis Service..."\n\
export SERVICE_NAME=ai-analysis-service\n\
python scripts/docker_startup_check.py\n\
if [ $? -ne 0 ]; then\n\
    echo "❌ Startup validation failed, exiting..."\n\
    exit 1\n\
fi\n\
echo "✅ Starting application..."\n\
exec uvicorn main:app --host 0.0.0.0 --port 8001\n\
' > /app/start.sh && chmod +x /app/start.sh

# Run the application with startup validation
CMD ["/app/start.sh"]