# adsbee-metrics-exporter
Metrics Exporter for ADSBee for use in prometheus.

## Shoutout

Huge thanks to the ADSBee project ([GitHub](https://github.com/CoolNamesAllTaken/adsbee)) and to [pantsforbirds.com](https://www.pantsforbirds.com) for inspiring and enabling this exporter.

## Overview

This is a lightweight Prometheus exporter that consumes ADSBee metrics from a WebSocket and exposes them on an HTTP endpoint for Prometheus scraping.

Prebuilt Docker image on Docker Hub: [bigjuevos/adsbee-metrics-exporter](https://hub.docker.com/r/bigjuevos/adsbee-metrics-exporter) — see the repository page: [Docker Hub repository page](https://hub.docker.com/repository/docker/bigjuevos/adsbee-metrics-exporter/general).

### Input JSON example

```
{ 
  "aircraft_dictionary_metrics": { 
    "raw_squitter_frames": 84,
    "valid_squitter_frames": 4,
    "raw_extended_squitter_frames": 82,
    "valid_extended_squitter_frames": 18,
    "demods_1090": 192,
    "raw_squitter_frames_by_source": [0, 0, 0],
    "valid_squitter_frames_by_source": [0, 0, 0],
    "raw_extended_squitter_frames_by_source": [0, 0, 0],
    "valid_extended_squitter_frames_by_source": [0, 2, 0],
    "demods_1090_by_source": [0, 0, 0]
  },
  "server_metrics": { 
    "feed_uri": ["", "", "", "", "", "", "feed.whereplane.xyz", "feed.adsb.lol", "feed.airplanes.live", "feed.adsb.fi"],
    "feed_mps": [0, 0, 0, 0, 0, 0, 23, 0, 23, 0]
  }
}
```

### Exported metrics

- `adsbee_raw_squitter_frames_current` (Gauge)
- `adsbee_valid_squitter_frames_current` (Gauge)
- `adsbee_raw_extended_squitter_frames_current` (Gauge)
- `adsbee_valid_extended_squitter_frames_current` (Gauge)
- `adsbee_demods_1090_current` (Gauge)
- `adsbee_feed_mps{feed_uri}` (Gauge) — exported only for non-empty `feed_uri` entries

## Configuration

Environment variables:

- `WS_URL` (required): WebSocket URL to consume metrics from. Example: `ws://host:port/metrics`
- `EXPORTER_PORT` (default: `9100`): HTTP port to expose metrics on.
- `RECONNECT_MIN_SECONDS` (default: `1`): Initial reconnect backoff.
- `RECONNECT_MAX_SECONDS` (default: `30`): Max reconnect backoff.
- `CONNECT_TIMEOUT_SECONDS` (default: `10`): WebSocket connect timeout.
- `RECEIVE_TIMEOUT_SECONDS` (default: `30`, set to `None` to disable): Receive timeout; on timeout, the exporter pings and continues or reconnects if ping fails.
- `LOG_LEVEL` (default: `INFO`): Logging level.

## Running locally

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export WS_URL="ws://localhost:8080/metrics"
python exporter.py
```

Prometheus metrics will be available at `http://localhost:9100/` (path `/metrics`).

## Docker

Pull (recommended):

```
docker pull bigjuevos/adsbee-metrics-exporter:latest
```

Run:

```
docker run --rm -p 9100:9100 \
  -e WS_URL="ws://host.docker.internal:8080/metrics" \
  -e EXPORTER_PORT=9100 \
  bigjuevos/adsbee-metrics-exporter:latest
```

Build locally (optional):

```
docker build -t adsbee-metrics-exporter:latest .
```

## Docker Compose

This repository includes a `docker-compose.yml` that pulls the published image by default. To build locally instead, uncomment the `build` section inside `docker-compose.yml`.

### Quick start

From the project root:

```bash
docker compose up -d
```

Then visit `http://localhost:9100/metrics`.

By default, the container listens on port `9100` and the exporter connects to `ws://host.docker.internal:8080/metrics` (suitable for macOS/Windows when the ADSBee source runs on the host). On Linux, adjust `WS_URL` to point at your ADSBee source.

### Configuration

You can configure the exporter by setting environment variables before running compose, or by creating a `.env` file in the project root.

- Inline environment variables:

```bash
WS_URL="ws://host.docker.internal:8080/metrics" \
EXPORTER_PORT=9100 \
docker compose up -d
```

- Using a `.env` file (create one alongside `docker-compose.yml`):

```env
# WebSocket source for ADSBee metrics
WS_URL=ws://host.docker.internal:8080/metrics

# Host port to expose (container always listens on 9100)
EXPORTER_PORT=9100

# Optional tuning
LOG_LEVEL=INFO
RECONNECT_MIN_SECONDS=1
RECONNECT_MAX_SECONDS=30
CONNECT_TIMEOUT_SECONDS=10
RECEIVE_TIMEOUT_SECONDS=30
```

Then run:

```bash
docker compose up -d
```

## Grafana dashboard

If you're using Prometheus with Grafana, a ready-to-import dashboard is provided at `grafana-dashboard.json`.

### Importing into Grafana

1. In Grafana, go to Dashboards → Import.
2. Upload the `grafana-dashboard.json` file (or paste its JSON).
3. When prompted, select your Prometheus data source.
4. Click Import.

The dashboard visualizes the exported metrics listed above and should work once Prometheus is scraping this exporter.

### Common operations

- Logs:

```bash
docker compose logs -f adsbee-metrics-exporter
```

- Rebuild after code changes:

```bash
docker compose up -d --build
```

- Stop and remove:

```bash
docker compose down
```

## Notes

- `server_metrics.feed_uri` and `server_metrics.feed_mps` are treated as matched arrays; only non-empty `feed_uri` entries are exported with corresponding `feed_mps`.
- The exporter performs exponential backoff on reconnect between `RECONNECT_MIN_SECONDS` and `RECONNECT_MAX_SECONDS`.
