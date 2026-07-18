"""
Advanced LIFX Controller with multizone support and per-light effect mapping.
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
        per_light_config: Optional[Dict[str, Dict]] = None,
    ):
        self.discover_all = discover_all
        self.labels = labels or []
        self.macs = macs or []
        self.update_rate = max(5, min(update_rate, 25))
        self.brightness_range = brightness_range
        self.per_light_config = per_light_config or {}

        self.lan: Optional[LifxLAN] = None
        self.lights: List[Light] = []
        self.light_info: Dict[str, Dict] = {}
        self.previous_states: Dict[str, Any] = {}
        self.last_update = 0.0
        self.min_interval = 1.0 / self.update_rate

    async def discover_and_connect(self):
        def _discover():
            self.lan = LifxLAN()
            all_lights = self.lan.get_lights() or []
            selected = []

            for light in all_lights:
                label = light.get_label() or ""
                mac = getattr(light, "mac_addr", "").lower()

                if (self.discover_all and not self.labels and not self.macs) or \
                   (self.labels and label in self.labels) or \
                   (self.macs and mac in [m.lower() for m in self.macs]):
                    selected.append(light)
            return selected

        self.lights = await asyncio.to_thread(_discover)

        for light in self.lights:
            label = light.get_label() or light.mac_addr
            try:
                if hasattr(light, "get_multizone"):
                    zones = light.get_multizone() or []
                    is_multizone = len(zones) > 1
                    self.light_info[label] = {"is_multizone": is_multizone, "zone_count": len(zones)}
                else:
                    self.light_info[label] = {"is_multizone": False, "zone_count": 1}
            except Exception:
                self.light_info[label] = {"is_multizone": False, "zone_count": 1}

            try:
                self.previous_states[label] = light.get_color()
            except Exception:
                pass

        logger.info(f"Discovered {len(self.lights)} lights | Multizone: {sum(1 for v in self.light_info.values() if v.get('is_multizone'))}")

    async def apply_visualization(self, commands: Dict[str, Any], light_label: Optional[str] = None):
        now = time.monotonic()
        if now - self.last_update < self.min_interval:
            return
        self.last_update = now

        targets = [l for l in self.lights if (not light_label or (l.get_label() or l.mac_addr) == light_label)]

        for light in targets:
            label = light.get_label() or light.mac_addr
            light_cfg = self.per_light_config.get(label, {})
            final_cmd = {**commands, **light_cfg.get("override", {})}

            hue = final_cmd.get("hue", 0)
            sat = final_cmd.get("saturation", 45000)
            bright = max(int(self.brightness_range[0]/100*65535), min(int(self.brightness_range[1]/100*65535), final_cmd.get("brightness", 30000)))
            kelvin = final_cmd.get("kelvin", 3500)
            transition = final_cmd.get("transition_ms", 60)

            info = self.light_info.get(label, {})
            is_multizone = info.get("is_multizone", False)
            zone_count = info.get("zone_count", 1)

            try:
                if is_multizone and zone_count > 1 and "spectrum_norm" in final_cmd:
                    zone_colors = self._build_zone_colors(final_cmd, zone_count)
                    light.set_zone_colors(zone_colors, duration=transition)
                else:
                    if final_cmd.get("flash"):
                        light.set_color((0, 0, min(65535, bright + 25000), 9000), rapid=True)
                        await asyncio.sleep(final_cmd.get("flash_duration_ms", 70) / 1000.0)
                    light.set_color((hue, sat, bright, kelvin), duration=transition, rapid=True)
            except Exception as e:
                logger.debug(f"Update error on {label}: {e}")

    def _build_zone_colors(self, cmd: Dict, zone_count: int) -> List[Tuple[int, int, int, int]]:
        spectrum = cmd.get("spectrum_norm", [])
        if not spectrum:
            return [(cmd.get("hue", 0), cmd.get("saturation", 45000), cmd.get("brightness", 30000), 3500)] * zone_count

        colors = []
        for i in range(zone_count):
            idx = int(i * len(spectrum) / max(1, zone_count))
            mag = spectrum[min(idx, len(spectrum)-1)]
            hue = (cmd.get("hue", 0) + int(mag * 22000)) % 65535
            sat = min(65535, int(cmd.get("saturation", 45000) * (0.6 + mag * 0.6)))
            bright = int(cmd.get("brightness", 30000) * (0.5 + mag * 0.9))
            colors.append((hue, sat, bright, cmd.get("kelvin", 3500)))
        return colors

    async def restore_previous_states(self):
        for light in self.lights:
            label = light.get_label() or light.mac_addr
            if label in self.previous_states:
                try:
                    light.set_color(self.previous_states[label], duration=350)
                except Exception:
                    pass
        await asyncio.sleep(0.35)