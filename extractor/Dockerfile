# syntax=docker/dockerfile:1.7-labs
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install extractor requirements first (cache-friendly)
COPY extractor/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy and install the shared package
COPY common /app/common
RUN pip install --no-cache-dir -e /app/common

# Copy extractor code
COPY extractor/autorun.py /app/autorun.py

# Make sure output dir exists (compose also mounts /data)
RUN mkdir -p /data/usgs_earthquakes

CMD ["python", "/app/autorun.py"]
