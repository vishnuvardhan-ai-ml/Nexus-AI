# Root-level production Dockerfile for NEXUS AI Backend
# Supports repository-root builds for Google Cloud Run / Render
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    ENVIRONMENT=production \
    DEBUG=false \
    PYTHONPATH=/app/backend

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/

RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/

WORKDIR /app/backend

EXPOSE 8080

CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1
