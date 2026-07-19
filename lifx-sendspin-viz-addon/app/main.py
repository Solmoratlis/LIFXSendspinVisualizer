#!/usr/bin/env python3
"""
LIFX SendSpin Music Visualizer - Main Application
"""
import asyncio
import json
import logging
import os
import signal
import time
from typing import Any, Dict, List, Optional

from lifxlan import LifxLAN
from app.lifx_controller import LifxController
from app.effects import get_effect_mapper
from app.sendspin_client import SendspinVisualizerClient
from app.web_ui import create_ui, update_viz_data, viz_state
from app.smoothing import VisualizationSmoother
import paho.mqtt.client as mqtt

# =============================================================================
# CONFIGURATION (from environment variables set by run.sh)
# =============================================================================
SENDSPIN_URL = os.getenv("SENDSPIN_URL") or "ws://localhost:8927/sendspin"
CLIENT_NAME = os.getenv("CLIENT_NAME") or "LIFX Visualizer"
EFFECT = os.getenv("EFFECT") or "energy_pulse"

sensitivity_str = os.getenv("SENSITIVITY", "1.0")
SENSITIVITY = float(sensitivity_str) if sensitivity_str.strip() else 1.0

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("lifx-sendspin-viz")


def load_config() -> Dict[str, Any]:
    """Load config from options.json or fallback to environment variables."""
    config_path = "/data/options.json"
    if os.path.exists(config_path):
        with open(config_path) as f:
            data = json.load(f)
    else:
        data = {}

    def safe_float(key: str, default: float) -> float:
        val = os.getenv(key, str(data.get(key, default)))
        try:
            return float(val) if val.strip() else default
        except (ValueError, TypeError):
            return default

    def safe_int(key: str, default: int) -> int:
        val = os.getenv(key, str(data.get(key, default)))
        try:
            return int(val) if val.strip() else default
        except (ValueError, TypeError):
            return default

    def safe_bool(key: str, default: bool) -> bool:
        val = os.getenv(key, str(data.get(key, default))).lower()
        if val in ("true", "1", "yes"):
            return True
        if val in ("false", "0", "no"):
            return False
        return default

    return {
        "sendspin_url": os.getenv("SENDSPIN_URL", data.get("sendspin_url", "ws://homeassistant.local:8927/sendspin")),
        "client_name": os.getenv("CLIENT_NAME", data.get("client_name", "LIFX Visualizer")),
        "lifx_discover_all": safe_bool("DISCOVER_ALL", data.get("lifx_discover_all", True)),
        "lifx_light_labels": json.loads(os.getenv("LIGHT_LABELS", json.dumps(data.get("lifx_light_labels", [])))),
        "lifx_mac_addresses": json.loads(os.getenv("MAC_ADDRESSES", json.dumps(data.get("lifx_mac_addresses", [])))),
        "effect": os.getenv("EFFECT", data.get("effect", "energy_pulse")),
        "sensitivity": safe_float("SENSITIVITY", data.get("sensitivity", 1.0)),
        "update_rate_hz": safe_int("UPDATE_RATE", data.get("update_rate_hz", 12)),
        "brightness_min": safe_int("BRIGHTNESS_MIN", data.get("brightness_min", 5)),
        "brightness_max": safe_int("BRIGHTNESS_MAX", data.get("brightness_max", 100)),
        "flash_on_beat": safe_bool("FLASH_ON_BEAT", data.get("flash_on_beat", True)),
        "enabled": safe_bool("ENABLED", data.get("enabled", True)),
        "spectrum_bins": safe_int("SPECTRUM_BINS", data.get("spectrum_bins", 8)),
        "spectrum_scale": os.getenv("SPECTRUM_SCALE", data.get("spectrum_scale", "mel")),
        "f_min": safe_int("F_MIN", data.get("f_min", 20)),
        "f_max": safe_int("F_MAX", data.get("f_max", 20000)),
    }


class LifxSendspinVizApp:
    def __init__(self):
        self.config = load_config()
        self.running = True
        self.lifx: Optional[LifxController] = None
        self.sendspin: Optional[SendspinVisualizerClient] = None
        self.effect_mapper = get_effect_mapper(self.config.get("effect", "energy_pulse"))
        self.last_viz_data: Dict[str, Any] = {}
        self.stats = {"frames": 0, "beats": 0, "updates_sent": 0}

    async def setup(self):
        logger.info("Setting up LIFX SendSpin Visualizer...")

        # LIFX Controller
        self.lifx = LifxController(
            discover_all=self.config.get("lifx_discover_all", True),
            labels=self.config.get("lifx_light_labels", []),
            macs=self.config.get("lifx_mac_addresses", []),
            update_rate=self.config.get("update_rate_hz", 12),
            brightness_range=(
                self.config.get("brightness_min", 5),
                self.config.get("brightness_max", 100),
            ),
        )
        await self.lifx.discover_and_connect()
        logger.info(f"Discovered {len(self.lifx.lights)} LIFX light(s)")

        light_names = [light.get_label() or light.mac_addr for light in self.lifx.lights]
        viz_state["lights"] = light_names

        # SendSpin Client
        self.sendspin = SendspinVisualizerClient(
            url=SENDSPIN_URL,
            client_name=CLIENT_NAME,
            visualizer_support={
                "types": ["loudness", "beat", "f_peak", "spectrum", "peak"],
                "buffer_capacity": 65536,
                "rate_max": self.config.get("update_rate_hz", 12),
                "spectrum": {
                    "n_disp_bins": self.config.get("spectrum_bins", 8),
                    "scale": self.config.get("spectrum_scale", "mel"),
                    "f_min": self.config.get("f_min", 20),
                    "f_max": self.config.get("f_max", 20000),
                },
            },
        )

        self.sendspin.on_visualization = self.handle_visualization_data
        self.sendspin.on_stream_start = self.on_stream_start
        self.sendspin.on_stream_end = self.on_stream_end

        await self.sendspin.connect()
        logger.info("Connected to SendSpin server as visualizer")

        # Start NiceGUI web UI
        asyncio.create_task(self.run_status_server())

    async def handle_visualization_data(self, data: Dict[str, Any]):
        if not self.config.get("enabled", True) or not self.lifx:
            return

        self.last_viz_data = data
        self.stats["frames"] += 1

        update_viz_data(data, self.stats, connected=True)

        commands = self.effect_mapper(data, self.config)
        if commands:
            await self.lifx.apply_visualization(commands)
            self.stats["updates_sent"] += 1

        if self.stats["frames"] % 50 == 0:
            logger.debug(f"Stats: {self.stats}")

    def on_stream_start(self, info: Dict):
        logger.info(f"SendSpin stream started: {info}")

    def on_stream_end(self):
        logger.info("SendSpin stream ended — restoring previous light states")
        if self.lifx:
            asyncio.create_task(self.lifx.restore_previous_states())

    async def run_status_server(self):
        create_ui(self)

        def start_nicegui():
            from nicegui import ui
            ui.run(
                host="0.0.0.0",
                port=8099,
                title="LIFX SendSpin Music Visualizer",
                reload=False,
                show=False,
                dark=True,
            )

        import threading
        threading.Thread(target=start_nicegui, daemon=True).start()
        logger.info("NiceGUI web UI started on port 8099")

    async def run(self):
         await self.setup()

        # Main loop - Sendspin client runs its own tasks internally
         try:
            while self.running:
                await asyncio.sleep(5)
                # Periodic health check / reconnect logic could go here
                if self.sendspin and not getattr(self.sendspin, "is_connected", False):
                    logger.warning("SendSpin disconnected — attempting reconnect...")
                    await self.sendspin.connect()
         except asyncio.CancelledError:
            pass
         finally:
            await self.shutdown()
            
    async def shutdown(self):
         logger.info("Shutting down...")
         self.running = False
         if self.sendspin:
            await self.sendspin.disconnect()
         if self.lifx:
            await self.lifx.restore_previous_states()
         logger.info("Shutdown complete.")


async def main():
    app = LifxSendspinVizApp()

    def handle_signal(sig):
        logger.info(f"Received signal {sig}")
        app.running = False

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, handle_signal, sig)

    await app.run()

# =============================================================================
# ENTRY POINT - Let NiceGUI manage the event loop
# =============================================================================
if __name__ == "__main__":
  from nicegui import ui

    async def startup():
        app = LifxSendspinVizApp()
        await app.setup()

        # Keep the app alive
        while getattr(app, "running", True):
            await asyncio.sleep(1)

    # Start the app setup when NiceGUI is ready
    ui.timer(0.1, startup, once=True)

    ui.run(
    host="0.0.0.0",
    port=8099,
    title="LIFX SendSpin Music Visualizer",
    reload=False,
    show=False,
    dark=True,
    storage_secret="lifx-sendspin-secret-98765",
    uvicorn_logging_level="warning",
    # These help with reverse proxies / ingress
    forwarded_allow_ips="*",
)
  
