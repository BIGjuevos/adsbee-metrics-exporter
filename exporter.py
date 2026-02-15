#!/usr/bin/env python3

import asyncio
import json
import logging
import os
import signal
import sys
from typing import Any, Dict, List, Optional

import websockets
from prometheus_client import Gauge, start_http_server


class AdsbeeMetricsExporter:
    """Prometheus exporter that consumes metrics from a WebSocket and exposes them.

    Metrics exported:
    - Gauges (last absolute values seen):
        adsbee_raw_squitter_frames
        adsbee_valid_squitter_frames
        adsbee_raw_extended_squitter_frames
        adsbee_valid_extended_squitter_frames
        adsbee_demods_1090
    - Gauges for server feed rates:
        adsbee_feed_mps{feed_uri}
    
    """

    def __init__(self) -> None:
        self.websocket_url: str = os.environ.get("WS_URL", "ws://localhost:8080/metrics")
        self.exporter_port: int = int(os.environ.get("EXPORTER_PORT", "9100"))
        self.reconnect_min_seconds: float = float(os.environ.get("RECONNECT_MIN_SECONDS", "1"))
        self.reconnect_max_seconds: float = float(os.environ.get("RECONNECT_MAX_SECONDS", "30"))
        self.connect_timeout_seconds: float = float(os.environ.get("CONNECT_TIMEOUT_SECONDS", "10"))
        self.receive_timeout_seconds: Optional[float] = self._get_optional_float(
            os.environ.get("RECEIVE_TIMEOUT_SECONDS", "30")
        )

        # Prometheus metrics (aircraft metrics as gauges only)

        self.raw_squitter_frames_gauge = Gauge(
            "adsbee_raw_squitter_frames_current",
            "Latest absolute value for raw squitter frames.",
        )
        self.valid_squitter_frames_gauge = Gauge(
            "adsbee_valid_squitter_frames_current",
            "Latest absolute value for valid squitter frames.",
        )
        self.raw_extended_squitter_frames_gauge = Gauge(
            "adsbee_raw_extended_squitter_frames_current",
            "Latest absolute value for raw extended squitter frames.",
        )
        self.valid_extended_squitter_frames_gauge = Gauge(
            "adsbee_valid_extended_squitter_frames_current",
            "Latest absolute value for valid extended squitter frames.",
        )
        self.demods_1090_gauge = Gauge(
            "adsbee_demods_1090_current",
            "Latest absolute value for 1090 demods.",
        )

        # New aircraft dictionary metrics (UAT frames and aircraft counts)
        self.raw_uat_adsb_frames_gauge = Gauge(
            "adsbee_raw_uat_adsb_frames_current",
            "Latest absolute value for raw UAT ADS-B frames.",
        )
        self.valid_uat_adsb_frames_gauge = Gauge(
            "adsbee_valid_uat_adsb_frames_current",
            "Latest absolute value for valid UAT ADS-B frames.",
        )
        self.raw_uat_uplink_frames_gauge = Gauge(
            "adsbee_raw_uat_uplink_frames_current",
            "Latest absolute value for raw UAT uplink frames.",
        )
        self.valid_uat_uplink_frames_gauge = Gauge(
            "adsbee_valid_uat_uplink_frames_current",
            "Latest absolute value for valid UAT uplink frames.",
        )
        self.num_mode_s_aircraft_gauge = Gauge(
            "adsbee_num_mode_s_aircraft_current",
            "Latest absolute value for number of Mode S aircraft.",
        )
        self.num_uat_aircraft_gauge = Gauge(
            "adsbee_num_uat_aircraft_current",
            "Latest absolute value for number of UAT aircraft.",
        )

        self.feed_mps_gauge = Gauge(
            "adsbee_feed_mps",
            "Messages per second per upstream feed URI.",
            labelnames=("feed_uri",),
        )

        # Device status metrics (labeled by device name)
        self.device_uptime_gauge = Gauge(
            "adsbee_device_uptime_seconds",
            "Device uptime in seconds.",
            labelnames=("device",),
        )
        self.device_core_usage_gauge = Gauge(
            "adsbee_device_core_usage_percent",
            "Device CPU core usage percent.",
            labelnames=("device", "core"),
        )
        self.device_temperature_gauge = Gauge(
            "adsbee_device_temperature_deg_c",
            "Device temperature in degrees Celsius.",
            labelnames=("device",),
        )
        self.device_heap_free_gauge = Gauge(
            "adsbee_device_heap_free_bytes",
            "Device heap free bytes.",
            labelnames=("device",),
        )
        self.device_heap_largest_free_block_gauge = Gauge(
            "adsbee_device_heap_largest_free_block_bytes",
            "Device largest free heap block in bytes.",
            labelnames=("device",),
        )

    @staticmethod
    def _get_optional_float(value: Optional[str]) -> Optional[float]:
        if value is None or value == "" or value.lower() == "none":
            return None
        return float(value)

    def _update_gauges_from_absolute(self, metrics: Dict[str, Any]) -> None:
        if "raw_squitter_frames" in metrics:
            value = int(metrics["raw_squitter_frames"])
            self.raw_squitter_frames_gauge.set(value)
        if "valid_squitter_frames" in metrics:
            value = int(metrics["valid_squitter_frames"])
            self.valid_squitter_frames_gauge.set(value)
        if "raw_extended_squitter_frames" in metrics:
            value = int(metrics["raw_extended_squitter_frames"])
            self.raw_extended_squitter_frames_gauge.set(value)
        if "valid_extended_squitter_frames" in metrics:
            value = int(metrics["valid_extended_squitter_frames"])
            self.valid_extended_squitter_frames_gauge.set(value)
        if "demods_1090" in metrics:
            value = int(metrics["demods_1090"])
            self.demods_1090_gauge.set(value)
        if "raw_uat_adsb_frames" in metrics:
            self.raw_uat_adsb_frames_gauge.set(int(metrics["raw_uat_adsb_frames"]))
        if "valid_uat_adsb_frames" in metrics:
            self.valid_uat_adsb_frames_gauge.set(int(metrics["valid_uat_adsb_frames"]))
        if "raw_uat_uplink_frames" in metrics:
            self.raw_uat_uplink_frames_gauge.set(int(metrics["raw_uat_uplink_frames"]))
        if "valid_uat_uplink_frames" in metrics:
            self.valid_uat_uplink_frames_gauge.set(int(metrics["valid_uat_uplink_frames"]))
        if "num_mode_s_aircraft" in metrics:
            self.num_mode_s_aircraft_gauge.set(int(metrics["num_mode_s_aircraft"]))
        if "num_uat_aircraft" in metrics:
            self.num_uat_aircraft_gauge.set(int(metrics["num_uat_aircraft"]))

    def _update_device_status(self, device_status: Dict[str, Any]) -> None:
        if not device_status:
            return
        for device_name, device_data in device_status.items():
            if not isinstance(device_data, dict):
                continue
            if "uptime_ms" in device_data:
                self.device_uptime_gauge.labels(device=device_name).set(
                    float(device_data["uptime_ms"]) / 1000.0
                )
            if "temperature_deg_c" in device_data:
                self.device_temperature_gauge.labels(device=device_name).set(
                    float(device_data["temperature_deg_c"])
                )
            if "heap_free_bytes" in device_data:
                self.device_heap_free_gauge.labels(device=device_name).set(
                    int(device_data["heap_free_bytes"])
                )
            if "heap_largest_free_block_bytes" in device_data:
                self.device_heap_largest_free_block_gauge.labels(device=device_name).set(
                    int(device_data["heap_largest_free_block_bytes"])
                )
            # Handle per-core usage keys like core_0_usage_percent,
            # core_1_usage_percent, and user_core_usage_percent.
            for key, value in device_data.items():
                if key.endswith("_usage_percent") and "core" in key:
                    core_label = key.removesuffix("_usage_percent")
                    self.device_core_usage_gauge.labels(device=device_name, core=core_label).set(
                        float(value)
                    )

    def _update_server_metrics(self, server_metrics: Dict[str, Any]) -> None:
        if not server_metrics:
            return
        feed_uris: List[str] = server_metrics.get("feed_uri") or []
        feed_mps_values: List[Any] = server_metrics.get("feed_mps") or []
        # Only export entries with non-empty feed_uri
        for uri, mps in zip(feed_uris, feed_mps_values):
            if uri:
                try:
                    value = float(mps)
                except Exception:
                    continue
                self.feed_mps_gauge.labels(feed_uri=str(uri)).set(value)

    async def _handle_single_message(self, message: str) -> None:
        try:
            payload = json.loads(message)
        except json.JSONDecodeError:
            logging.warning("Received non-JSON message; ignoring")
            return

        aircraft_metrics = payload.get("aircraft_dictionary_metrics") or {}
        server_metrics = payload.get("server_metrics") or {}
        device_status = payload.get("device_status") or {}

        if aircraft_metrics:
            self._update_gauges_from_absolute(aircraft_metrics)

        if server_metrics:
            self._update_server_metrics(server_metrics)

        if device_status:
            self._update_device_status(device_status)

    async def run_forever(self) -> None:
        start_http_server(self.exporter_port)
        logging.info("Prometheus exporter listening on port %d", self.exporter_port)

        backoff_seconds = self.reconnect_min_seconds
        while True:
            logging.info("Connecting to WebSocket: %s", self.websocket_url)
            try:
                async with websockets.connect(self.websocket_url, open_timeout=self.connect_timeout_seconds) as ws:
                    logging.info("WebSocket connected")
                    # Reset backoff after a successful connection
                    backoff_seconds = self.reconnect_min_seconds
                    while True:
                        try:
                            message = await asyncio.wait_for(
                                ws.recv(), timeout=self.receive_timeout_seconds
                            ) if self.receive_timeout_seconds else await ws.recv()
                        except asyncio.TimeoutError:
                            logging.warning("Receive timeout; attempting to ping and continue")
                            try:
                                await ws.ping()
                            except Exception:
                                logging.warning("Ping failed; breaking to reconnect")
                                break
                            continue
                        except websockets.ConnectionClosed:
                            logging.warning("WebSocket connection closed; will reconnect")
                            break
                        await self._handle_single_message(message)
            except Exception as exc:
                logging.error("WebSocket connection error: %s", exc)

            # Reconnect with exponential backoff
            logging.info("Reconnecting in %.1f seconds", backoff_seconds)
            await asyncio.sleep(backoff_seconds)
            backoff_seconds = min(backoff_seconds * 2, self.reconnect_max_seconds)


async def _main_async() -> None:
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    exporter = AdsbeeMetricsExporter()

    # Handle graceful shutdown
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _handle_signal(sig: int, frame: Any) -> None:  # type: ignore[override]
        logging.info("Received signal %s; shutting down...", sig)
        stop_event.set()

    try:
        loop.add_signal_handler(signal.SIGINT, stop_event.set)
        loop.add_signal_handler(signal.SIGTERM, stop_event.set)
    except NotImplementedError:
        # Windows
        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)

    exporter_task = asyncio.create_task(exporter.run_forever())

    await stop_event.wait()
    exporter_task.cancel()
    try:
        await exporter_task
    except asyncio.CancelledError:
        pass


def main() -> None:
    try:
        asyncio.run(_main_async())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
