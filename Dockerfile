FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install runtime deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY exporter.py ./

EXPOSE 9100

# Default envs (can be overridden at runtime)
ENV WS_URL="ws://localhost:8080/metrics" \
    EXPORTER_PORT=9100 \
    RECONNECT_MIN_SECONDS=1 \
    RECONNECT_MAX_SECONDS=30 \
    CONNECT_TIMEOUT_SECONDS=10 \
    RECEIVE_TIMEOUT_SECONDS=30 \
    LOG_LEVEL=INFO

CMD ["python", "-u", "exporter.py"]


