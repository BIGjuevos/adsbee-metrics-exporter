# adsbee-metrics-exporter
Metrics Exporter for ADSBee for use in prometheus.

## Shoutout

Huge thanks to the ADSBee project ([GitHub](https://github.com/CoolNamesAllTaken/adsbee)) and to [pantsforbirds.com](https://www.pantsforbirds.com) for inspiring and enabling this exporter.

## Overview

This is a lightweight Prometheus exporter that consumes ADSBee metrics from a WebSocket and exposes them on an HTTP endpoint for Prometheus scraping.

Prebuilt Docker image on Docker Hub: [bigjuevos/adsbee-metrics-exporter](https://hub.docker.com/r/bigjuevos/adsbee-metrics-exporter) — see the repository page: [Docker Hub repository page](https://hub.docker.com/repository/docker/bigjuevos/adsbee-metrics-exporter).

### Input JSON example

```
{
  "aircraft_dictionary_metrics": {
    "raw_squitter_frames": 92,
    "valid_squitter_frames": 64,
    "raw_extended_squitter_frames": 66,
    "valid_extended_squitter_frames": 37,
    "demods_1090": 158,
    "raw_squitter_frames_by_source": [29, 21, 26, 16],
    "valid_squitter_frames_by_source": [21, 17, 13, 13],
    "raw_extended_squitter_frames_by_source": [10, 10, 25, 21],
    "valid_extended_squitter_frames_by_source": [13, 11, 6, 7],
    "demods_1090_by_source": [39, 31, 51, 37],
    "raw_uat_adsb_frames": 10,
    "valid_uat_adsb_frames": 5,
    "raw_uat_uplink_frames": 3,
    "valid_uat_uplink_frames": 1,
    "raw_remote_id_frames": 4,
    "valid_remote_id_frames": 2,
    "num_mode_s_aircraft": 22,
    "num_uat_aircraft": 2,
    "num_remote_id_aircraft": 1
  },
  "server_metrics": {
    "feed_uri": ["", "", "", "", "", "", "feed.whereplane.xyz", "feed.adsb.lol", "feed.airplanes.live", "feed.adsb.fi"],
    "feed_mps": [0, 0, 0, 0, 0, 0, 98, 98, 98, 98]
  },
  "device_status": {
    "rp2040": {
      "uptime_ms": 77517602,
      "core_0_usage_percent": 87,
      "core_1_usage_percent": 0,
      "temperature_deg_c": 55,
      "noise_floor_dbm": -103,
      "noise_floor_mv": 741
    },
    "gnss": {
      "enabled": true,
      "fix_valid": true,
      "latitude_deg": 37.774900,
      "longitude_deg": -122.419400,
      "altitude_ft": 52,
      "heading_deg": 0.0,
      "speed_kts": 0,
      "num_satellites": 9,
      "utc_time": "12:34:56"
    },
    "subg": {
      "uptime_ms": 77510903,
      "user_core_usage_percent": 99,
      "temperature_deg_c": 57
    },
    "esp32": {
      "uptime_ms": 77472192,
      "core_0_usage_percent": 46,
      "core_1_usage_percent": 16,
      "temperature_deg_c": 63,
      "heap_free_bytes": 44204,
      "heap_largest_free_block_bytes": 17396
    }
  }
}
```

### Exported metrics

**Aircraft dictionary metrics:**

- `adsbee_raw_squitter_frames_current` (Gauge)
- `adsbee_valid_squitter_frames_current` (Gauge)
- `adsbee_raw_extended_squitter_frames_current` (Gauge)
- `adsbee_valid_extended_squitter_frames_current` (Gauge)
- `adsbee_demods_1090_current` (Gauge)
- `adsbee_raw_uat_adsb_frames_current` (Gauge)
- `adsbee_valid_uat_adsb_frames_current` (Gauge)
- `adsbee_raw_uat_uplink_frames_current` (Gauge)
- `adsbee_valid_uat_uplink_frames_current` (Gauge)
- `adsbee_num_mode_s_aircraft_current` (Gauge)
- `adsbee_num_uat_aircraft_current` (Gauge)
- `adsbee_raw_remote_id_frames_current` (Gauge)
- `adsbee_valid_remote_id_frames_current` (Gauge)
- `adsbee_num_remote_id_aircraft_current` (Gauge) — Remote ID aircraft (drones)

**Per-source receiver metrics** (labeled by `source` — the index into the `*_by_source` arrays, e.g. `0`–`3`):

- `adsbee_raw_squitter_frames_by_source_current{source}` (Gauge)
- `adsbee_valid_squitter_frames_by_source_current{source}` (Gauge)
- `adsbee_raw_extended_squitter_frames_by_source_current{source}` (Gauge)
- `adsbee_valid_extended_squitter_frames_by_source_current{source}` (Gauge)
- `adsbee_demods_1090_by_source_current{source}` (Gauge)

**Server metrics:**

- `adsbee_feed_mps{feed_uri}` (Gauge) — exported only for non-empty `feed_uri` entries

**Device status metrics** (labeled by `device` — e.g. `rp2040`, `subg`, `esp32`):

- `adsbee_device_uptime_seconds{device}` (Gauge) — uptime converted from ms to seconds
- `adsbee_device_core_usage_percent{device, core}` (Gauge) — CPU core usage
- `adsbee_device_temperature_deg_c{device}` (Gauge) — temperature in degrees Celsius
- `adsbee_device_heap_free_bytes{device}` (Gauge) — heap free bytes (esp32 only)
- `adsbee_device_heap_largest_free_block_bytes{device}` (Gauge) — largest free block (esp32 only)
- `adsbee_device_noise_floor_dbm{device}` (Gauge) — 1090 receiver noise floor in dBm (rp2040 only)
- `adsbee_device_noise_floor_mv{device}` (Gauge) — 1090 receiver noise floor RSSI voltage in mV (rp2040 only)

**GNSS metrics** (from `device_status.gnss`):

- `adsbee_gnss_enabled` (Gauge) — 1 if GNSS is enabled, else 0
- `adsbee_gnss_fix_valid` (Gauge) — 1 if GNSS has a valid fix, else 0
- `adsbee_gnss_num_satellites` (Gauge) — satellites in use

Location metrics, exported **only** when `EXPORT_GNSS_LOCATION=true`:

- `adsbee_gnss_latitude_deg` (Gauge)
- `adsbee_gnss_longitude_deg` (Gauge)
- `adsbee_gnss_altitude_ft` (Gauge)
- `adsbee_gnss_heading_deg` (Gauge)
- `adsbee_gnss_speed_kts` (Gauge)

All new metrics are backwards-compatible: old firmware payloads that omit the new fields will simply not populate these gauges.

## Configuration

Environment variables:

- `WS_URL` (required): WebSocket URL to consume metrics from. Example: `ws://host:port/metrics`
- `EXPORTER_PORT` (default: `9100`): HTTP port to expose metrics on.
- `RECONNECT_MIN_SECONDS` (default: `1`): Initial reconnect backoff.
- `RECONNECT_MAX_SECONDS` (default: `30`): Max reconnect backoff.
- `CONNECT_TIMEOUT_SECONDS` (default: `10`): WebSocket connect timeout.
- `RECEIVE_TIMEOUT_SECONDS` (default: `30`, set to `None` to disable): Receive timeout; on timeout, the exporter pings and continues or reconnects if ping fails.
- `HEARTBEAT_INTERVAL_SECONDS` (default: `30`, set to `None` to disable): How often to send an application-level heartbeat message to the device. The ADSBee firmware's `/metrics` WebSocket server prunes any client that has not sent a *data* frame within its 90s inactivity timeout (protocol-level WebSocket pings do not count). Keep this comfortably below 90s; the default 30s mirrors the official web dashboard's heartbeat.
- `HEARTBEAT_MESSAGE` (default: `ping`): The text message sent as the heartbeat data frame.
- `EXPORT_GNSS_LOCATION` (default: `false`): Set to `true` to export GNSS position and motion (`adsbee_gnss_latitude_deg`, `_longitude_deg`, `_altitude_ft`, `_heading_deg`, `_speed_kts`). Off by default because it records your receiver's location in Prometheus. GNSS status (enabled, fix, satellites) is always exported.
- `LOG_LEVEL` (default: `INFO`): Logging level.

## Running locally

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export WS_URL="ws://your-adsbee-host:80/metrics"
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
  -e WS_URL="ws://your-adsbee-host:80/metrics" \
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
WS_URL="ws://your-adsbee-host:80/metrics" \
EXPORTER_PORT=9100 \
docker compose up -d
```

- Using a `.env` file (create one alongside `docker-compose.yml`):

```env
# WebSocket source for ADSBee metrics
WS_URL=ws://your-adsbee-host:80/metrics

# Host port to expose (container always listens on 9100)
EXPORTER_PORT=9100

# Optional tuning
LOG_LEVEL=INFO
RECONNECT_MIN_SECONDS=1
RECONNECT_MAX_SECONDS=30
CONNECT_TIMEOUT_SECONDS=10
RECEIVE_TIMEOUT_SECONDS=30

# Export GNSS position/motion (reveals receiver location)
EXPORT_GNSS_LOCATION=false
```

Then run:

```bash
docker compose up -d
```

## Grafana dashboard

If you're using Prometheus with Grafana, a ready-to-import dashboard is provided at `grafana-dashboard.json`.

![Example Grafana dashboard](images/grafana.png)

### Importing into Grafana

1. In Grafana, go to Dashboards → Import.
2. Upload the `grafana-dashboard.json` file (or paste its JSON).
3. When prompted, select your Prometheus data source.
4. Click Import.

The dashboard visualizes the exported metrics listed above and should work once Prometheus is scraping this exporter.
