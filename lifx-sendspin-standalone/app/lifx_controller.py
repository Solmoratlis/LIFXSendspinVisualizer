"""
LIFX light controller with multizone support and state save/restore.
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

from lifxlan import LifxLAN, Light, MultiZoneLight

logger = logging.getLogger("lifx-sendspin.lifx")


class LifxController:
    def __init__(
        self,
        discover_all: bool = True,
        labels: Optional[List[str]] = None,
        macs: Optional[List[str]] = None,
        update_rate: int = 15,
        brightness_range: Tuple[int, int] = (5, 100),
    ):
        self.discover_all = discover_all
        self.labels = labels or []
        self.macs = macs or []
        self.update_rate = max(5, min(30, update_rate))
        self.brightness_min, self.brightness_max = brightness_range

        self.lan: Optional[LifxLAN] = None
        self.lights: List[Light] = []
        self._previous_states: Dict[str, Any] = {}
        self._last_update = 0.0
        self._lock = asyncio.Lock()

    async def discover_and_connect(self):
        logger.info("Discovering LIFX lights on the network...")
        self.lan = LifxLAN()

        # Run discovery in a thread because lifxlan is synchronous
        loop = asyncio.get_running_loop()
        devices = await loop.run_in_executor(None, self.lan.get_lights)

        selected = []
        for light in devices:
            try:
                label = light.get_label()
                mac = light.get_mac_addr()
            except Exception:
                continue

            if self.discover_all:
                selected.append(light)
            elif self.labels and label in self.labels:
                selected.append(light)
            elif self.macs and mac in self.macs:
                selected.append(light)

        self.lights = selected
        logger.info(f"Selected {len(self.lights)} light(s)")

        # Save original states
        for light in self.lights:
            try:
                color = light.get_color()
                self._previous_states[light.get_mac_addr()] = color
            except Exception as e:
                logger.debug(f"Could not save state for {light}: {e}")

    async def apply_visualization(self, commands: Dict[str, Any]):
        """Apply a visualization command to all controlled lights."""
        if not self.lights:
            return

        now = asyncio.get_event_loop().time()
        min_interval = 1.0 / self.update_rate
        if now - self._last_update < min_interval:
            return
        self._last_update = now

        hue = int(commands.get("hue", 0)) % 65535
        saturation = int(commands.get("saturation", 0))
        brightness = int(commands.get("brightness", 0))
        kelvin = int(commands.get("kelvin", 3500))
        duration = int(commands.get("transition_ms", 50))

        # Clamp brightness to configured range
        b_min = int(self.brightness_min / 100 * 65535)
        b_max = int(self.brightness_max / 100 * 65535)
        brightness = max(b_min, min(b_max, brightness))

        color = [hue, saturation, brightness, kelvin]

        async with self._lock:
            loop = asyncio.get_running_loop()
            tasks = []
            for light in self.lights:
                tasks.append(
                    loop.run_in_executor(
                        None,
                        lambda l=light, c=color, d=duration: self._set_color(l, c, d),
                    )
                )
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    def _set_color(self, light: Light, color: List[int], duration: int):
        try:
            # Multizone support
            if isinstance(light, MultiZoneLight) or hasattr(light, "set_zone_colors"):
                try:
                    # Simple single-color for multizone for now
                    light.set_color(color, duration=duration, rapid=True)
                    return
                except Exception:
                    pass
            light.set_color(color, duration=duration, rapid=True)
        except Exception as e:
            logger.debug(f"Failed to set color on {light}: {e}")

    async def restore_previous_states(self):
        if not self._previous_states:
            return
        logger.info("Restoring previous light states...")
        loop = asyncio.get_running_loop()
        for light in self.lights:
            mac = light.get_mac_addr()
            if mac in self._previous_states:
                try:
                    color = self._previous_states[mac]
                    await loop.run_in_executor(
                        None,
                        lambda l=light, c=color: l.set_color(c, duration=1000),
                    )
                except Exception as e:
                    logger.debug(f"Restore failed for {mac}: {e}")
        logger.info("Previous states restored")