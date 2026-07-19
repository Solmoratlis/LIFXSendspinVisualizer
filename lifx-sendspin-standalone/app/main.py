"""
Main application for the standalone LIFX SendSpin Visualizer.
"""
import asyncio
import logging
from typing import Any, Dict, Optional

from .sendspin_client import SendspinVisualizerClient
from .lifx_controller import LifxController
from .effects import get_effect_mapper
from .web_ui import create_ui, update_viz_data

logger = logging.getLogger("lifx-sendspin")


class LifxSendspinApp:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.running = True
        self.lifx: Optional[LifxController] = None
        self.sendspin: Optional[SendspinVisualizerClient] = None

        viz = config.get("visualization", {})
        self.effect_mapper = get_effect_mapper(viz.get("effect", "energy_pulse"))
        self.stats = {"frames": 0, "beats": 0, "updates_sent": 0}

    async def setup(self):
        logger.info("Setting up LIFX controller...")
        lifx_cfg = self.config.get("lifx", {})
        viz_cfg = self.config.get("visualization", {})

        self.lifx = LifxController(
            discover_all=lifx_cfg.get("discover_all", True),
            labels=lifx_cfg.get("light_labels", []),
            macs=lifx_cfg.get("mac_addresses", []),
            update_rate=viz_cfg.get("update_rate_hz", 15),
            brightness_range=(
                viz_cfg.get("brightness_min", 5),
                viz_cfg.get("brightness_max", 100),
            ),
        )
        await self.lifx.discover_and_connect()
        logger.info(f"Found {len(self.lifx.lights)} LIFX light(s)")

        # SendSpin client
        ss_cfg = self.config.get("sendspin", {})
        self.sendspin = SendspinVisualizerClient(
            url=ss_cfg.get("url", "ws://homeassistant.local:8927/sendspin"),
            client_name=ss_cfg.get("client_name", "LIFX Visualizer"),
            psk=ss_cfg.get("psk"),
        )
        self.sendspin.on_visualization = self.handle_visualization
        self.sendspin.on_stream_start = lambda info: logger.info(f"Stream started: {info}")
        self.sendspin.on_stream_end = self._on_stream_end

        await self.sendspin.connect()
        logger.info("Connected to SendSpin server")

        # Start web UI
        web_cfg = self.config.get("web", {})
        create_ui(
            host=web_cfg.get("host", "0.0.0.0"),
            port=web_cfg.get("port", 8099),
        )

    async def handle_visualization(self, data: Dict[str, Any]):
        viz_cfg = self.config.get("visualization", {})
        if not viz_cfg.get("enabled", True) or not self.lifx:
            return

        self.stats["frames"] += 1
        if data.get("beat"):
            self.stats["beats"] += 1

        # Push to web UI
        update_viz_data(data, self.stats, connected=True)

        # Map to light commands
        commands = self.effect_mapper(data, {
            **viz_cfg,
            "sensitivity": viz_cfg.get("sensitivity", 1.0),
        })
        if commands:
            await self.lifx.apply_visualization(commands)
            self.stats["updates_sent"] += 1

    def _on_stream_end(self):
        logger.info("SendSpin stream ended")
        if self.lifx:
            asyncio.create_task(self.lifx.restore_previous_states())

    async def run(self):
        await self.setup()
        try:
            while self.running:
                await asyncio.sleep(3)
                if self.sendspin and not self.sendspin.is_connected:
                    logger.warning("SendSpin disconnected — reconnecting...")
                    try:
                        await self.sendspin.connect()
                    except Exception as e:
                        logger.error(f"Reconnect failed: {e}")
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
        logger.info("Shutdown complete")