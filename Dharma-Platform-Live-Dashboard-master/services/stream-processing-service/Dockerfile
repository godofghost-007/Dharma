FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY services/stream-processing-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules first (from project root context)
COPY shared/ ./shared/

# Copy application code
COPY services/stream-processing-service/app/ ./app/

# Create non-root user
RUN useradd -m -u 1000 dharma && chown -R dharma:dharma /app
USER dharma

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Expose port
EXPOSE 8002

# Run the application
CMD ["python", "-m", "app.main"]