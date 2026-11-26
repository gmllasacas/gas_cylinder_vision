FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies for OpenCV, FFMPEG, and healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    ffmpeg \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create non-root application user and group
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -s /bin/bash -m appuser

WORKDIR /app

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application codebase and configuration
COPY app/ ./app/
COPY locales/ ./locales/
COPY static/ ./static/
COPY templates/ ./templates/
COPY models/ ./models/
COPY config.json ./config.json

# Pre-create data and runtime directories with non-root ownership
RUN mkdir -p /app/data /app/videos /app/models && \
    chown -R appuser:appgroup /app

USER appuser

# Expose FastAPI default port
EXPOSE 8000

# Container healthcheck querying the public unauthenticated /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run FastAPI app with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
