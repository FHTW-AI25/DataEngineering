# syntax=docker/dockerfile:1.7-labs
FROM python:3.11-slim

# Prevents Python from writing .pyc files and buffers
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY autorun.py ./

# Environment defaults (can be overridden in docker-compose or .env)
ENV DATA_DIR=/data/usgs_earthquakes
ENV USGS_BASE_URL="https://earthquake.usgs.gov/fdsnws/event/1/query"
ENV MONTHS_BEFORE_CURRENT=12
ENV REQUEST_TIMEOUT_SECONDS=10
ENV REQUEST_SLEEP_SECONDS=0.2
ENV MAX_SPLIT_RETRIES=3

# Create output directory inside container
RUN mkdir -p /data/usgs_earthquakes

# Default command — run the extractor
CMD ["python", "/app/autorun.py"]
