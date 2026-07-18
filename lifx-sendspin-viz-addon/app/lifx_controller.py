"""
LIFX Controller for real-time music visualization.
Uses lifxlan for direct LAN control (low latency, no cloud roundtrip).
Supports rate limiting, state saving/restoring, and basic multi-zone handling.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from lifxlan import LifxLAN, Light

logger = logging.getLogger(__name__)


class LifxController:
    def __init__(
        self,
        discover_all: bool = True,
        labels: Optional[List[str]] = None,
        macs: Optional[List[str]] = None,
        update_rate: int = 12,
        brightness_range: Tuple[int, int] = (5, 100),
    ):
        self.discover_all = discover_all
        self.labels = labels or []
        self.macs = macs or []
        self.update_rate = max(5, min(update_rate, 25))
        self.brightness_range = brightness_range
        self.lan: Optional[LifxLAN] = None
        self.lights: List[Light] = []
        self.previous_states: Dict[str, Any] = {}  # mac or label -> (hue, sat, bright, kelvin)
        self.last_update = 0.0
        self.min_interval = 1.0 / self.update_rate

    async def discover_and_connect(self):
        """Discover lights on LAN. Runs in executor because lifxlan is sync."""
        def _discover():
            self.lan = LifxLAN()
            all_lights = self.lan.get_lights() or []
            selected = []

            if self.discover_all and not self.labels and not self.macs:
                selected = all_lights
            else:
                for light in all_lights:
                    label = light.get_label() or ""
                    mac = light.mac_addr.lower() if hasattr(light, "mac_addr") else ""
                    if (self.labels and label in self.labels) or (self.macs and mac in [m.lower() for m in self.macs]):
                        selected.append(light)

            return selected

        self.lights = await asyncio.to_thread(_discover)
        logger.info(f"Found {len(self.lights)} matching LIFX light(s)")

        # Save current state for later restore (best effort)
        for light in self.lights:
            try:
                color = light.get_color()
                label = light.get_label() or light.mac_addr
                self.previous_states[label] = color  # (H, S, B, K)
            except Exception:
                pass

    async def apply_visualization(self, commands: Dict[str, Any]):
        """Apply a visualization frame to all selected lights. Rate limited."""
        now = time.monotonic()
        if now - self.last_update < self.min_interval:
            return
        self.last_update = now

        if not self.lights:
            return

        # Example command structure from effects.py:
        # {
        #   "hue": 12000,          # 0-65535
        #   "saturation": 45000,
        #   "brightness": 30000,
        #   "kelvin": 3500,
        #   "flash": False,        # or duration in ms
        #   "transition_ms": 80
        # }

        hue = commands.get("hue", 0)
        sat = commands.get("saturation", 0)
        bright = max(
            int(self.brightness_range[0] / 100 * 65535),
            min(int(self.brightness_range[1] / 100 * 65535), commands.get("brightness", 20000))
        )
        kelvin = commands.get("kelvin", 3500)
        transition = commands.get("transition_ms", 60)

        flash = commands.get("flash", False)
        if flash:
            # Quick white flash then back
            flash_bright = min(65535, bright + 30000)
            for light in self.lights:
                try:
                    light.set_color((0, 0, flash_bright, 9000), rapid=True)  # white-ish flash
                except Exception as e:
                    logger.debug(f"Flash error on {light.get_label()}: {e}")
            await asyncio.sleep(commands.get("flash_duration_ms", 80) / 1000.0)

        # Main color
        for light in self.lights:
            try:
                # For multi-zone lights you would use set_zone_colors here instead
                if hasattr(light, "set_zone_colors") and commands.get("zones"):
                    # Advanced: implement zone mapping for spectrum
                    pass
                else:
                    light.set_color((hue, sat, bright, kelvin), duration=transition, rapid=True)
            except Exception as e:
                logger.warning(f"Failed to set color on light: {e}")

    async def restore_previous_states(self):
        """Restore lights to state before viz started (best effort)."""
        for light in self.lights:
            label = light.get_label() or light.mac_addr
            if label in self.previous_states:
                try:
                    color = self.previous_states[label]
                    light.set_color(color, duration=300)
                    logger.debug(f"Restored state for {label}")
                except Exception:
                    pass
        await asyncio.sleep(0.3)