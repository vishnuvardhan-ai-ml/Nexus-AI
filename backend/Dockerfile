# Multi-stage / optimized production Dockerfile for NEXUS AI Backend
# Target Platform: Google Cloud Run / Render / Container Engine
FROM python:3.11-slim

# Prevent Python from writing .pyc files & enable unbuffered standard I/O for live streaming logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    ENVIRONMENT=production \
    DEBUG=false

WORKDIR /app

# Install runtime utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency specifications first to leverage Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application source code
COPY . .

# Expose standard Cloud Run port
EXPOSE 8080

# Run uvicorn server binding dynamically to PORT injected by Cloud Run or Render
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1
