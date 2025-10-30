# extractor/Dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && rm -rf /var/lib/apt/lists/*

# Python deps only what we need
RUN pip install --no-cache-dir requests pandas pyarrow psycopg2-binary

WORKDIR /app
COPY extractor /app/extractor

# default command runs the autorun logic
CMD ["python", "/app/extractor/autorun.py"]
