#!/usr/bin/env python3
"""
LIFX SendSpin Music Visualizer - Main Application
Connects to Music Assistant SendSpin server as visualizer client and drives LIFX lights.
"""

import asyncio
import json
import logging
import os
import signal
import time
from typing import Any, Dict, List, Optional

from lifxlan import LifxLAN

from .lifx_controller import LifxController
from .effects import get_effect_mapper
from .sendspin_client import SendspinVisualizerClient
from .web_ui import create_ui, update_viz_data, viz_state
from .smoothing import VisualizationSmoother
import paho.mqtt.client as mqtt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("lifx-sendspin-viz")

# Load config from env or options.json (set by run.sh / Supervisor)
def load_config() -> Dict[str, Any]:
    config_path = "/data/options.json"
    if os.path.exists(config_path):
        with open(config_path) as f:
            return json.load(f)
    # Dev fallback
    return {
        "sendspin_url": os.getenv("SENDSPIN_URL", "ws://homeassistant.local:8927/sendspin"),
        "client_name": os.getenv("CLIENT_NAME", "LIFX Visualizer"),
        "lifx_discover_all": os.getenv("DISCOVER_ALL", "true").lower() == "true",
        "lifx_light_labels": json.loads(os.getenv("LIGHT_LABELS", "[]")),
        "effect": os.getenv("EFFECT", "energy_pulse"),
        "sensitivity": float(os.getenv("SENSITIVITY", "1.0")),
        "update_rate_hz": int(os.getenv("UPDATE_RATE", "12")),
        "brightness_min": int(os.getenv("BRIGHTNESS_MIN", "5")),
        "brightness_max": int(os.getenv("BRIGHTNESS_MAX", "100")),
        "flash_on_beat": os.getenv("FLASH_ON_BEAT", "true").lower() == "true",
        "enabled": os.getenv("ENABLED", "true").lower() == "true",
        "spectrum_bins": 8,
        "spectrum_scale": "mel",
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

        # Push initial lights list to web UI
        light_names = [light.get_label() or light.mac_addr for light in self.lifx.lights]
        viz_state["lights"] = light_names

        # SendSpin Visualizer Client (aiosendspin powered)
        self.sendspin = SendspinVisualizerClient(
            url=self.config["sendspin_url"],
            client_name=self.config["client_name"],
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

        # Wire callbacks
        self.sendspin.on_visualization = self.handle_visualization_data
        self.sendspin.on_stream_start = self.on_stream_start
        self.sendspin.on_stream_end = self.on_stream_end

        await self.sendspin.connect()
        logger.info("Connected to SendSpin server as visualizer")

        # Simple status web server for ingress
        asyncio.create_task(self.run_status_server())

    async def handle_visualization_data(self, data: Dict[str, Any]):
        """Called by Sendspin client for every visualization frame."""
        if not self.config.get("enabled", True) or not self.lifx:
            return

        self.last_viz_data = data
        self.stats["frames"] += 1

        # Push live data to the NiceGUI web UI
        update_viz_data(data, self.stats, connected=True)

        # Map to LIFX commands via effect
        commands = self.effect_mapper(data, self.config)

        if commands:
            await self.lifx.apply_visualization(commands)
            self.stats["updates_sent"] += 1

        # Optional: log occasionally
        if self.stats["frames"] % 50 == 0:
            logger.debug(f"Stats: {self.stats} | Last loudness: {data.get('loudness')}")

    def on_stream_start(self, info: Dict):
        logger.info(f"SendSpin stream started: {info}")
        # Could set lights to a "viz active" scene here

    def on_stream_end(self):
        logger.info("SendSpin stream ended — restoring previous light states (if saved)")
        if self.lifx:
            asyncio.create_task(self.lifx.restore_previous_states())

    async def run_status_server(self):
        """Advanced NiceGUI web UI for ingress (real-time spectrum, controls, live metrics)."""
        # NiceGUI will serve on port 8099
        create_ui(self)

        # Start NiceGUI in the existing event loop (non-blocking)
        # We run it as a background task so the main loop can continue
        def start_nicegui():
            from nicegui import ui
            ui.run(
                host="0.0.0.0",
                port=8099,
                title="LIFX SendSpin Music Visualizer",
                reload=False,
                show=False,           # headless for add-on
                dark=True,
            )

        # Run NiceGUI in a separate thread (it manages its own loop internally)
        import threading
        threading.Thread(target=start_nicegui, daemon=True).start()
        logger.info("Advanced NiceGUI web UI started on port 8099 (ingress)")

    async def run(self):
        await self.setup()

        # Main loop - Sendspin client runs its own tasks internally
        try:
            while self.running:
                await asyncio.sleep(5)
                # Periodic health check / reconnect logic could go here
                if self.sendspin and not self.sendspin.is_connected():
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


if __name__ == "__main__":
    asyncio.run(main())