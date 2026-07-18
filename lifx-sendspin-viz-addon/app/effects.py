"""
Visualization effect mappers.
Convert SendSpin visualizer data (loudness, spectrum, beat, f_peak, peak)
into LIFX HSBK + flash commands.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def get_effect_mapper(effect_name: str):
    """Factory returning the mapper function for the chosen effect."""
    mappers = {
        "energy_pulse": energy_pulse_effect,
        "spectrum_bands": spectrum_bands_effect,
        "dominant_hue": dominant_hue_effect,
        "beat_strobe": beat_strobe_effect,
        "custom": custom_effect,
    }
    return mappers.get(effect_name, energy_pulse_effect)


def _normalize(val: int | float, min_in=0, max_in=65535, min_out=0.0, max_out=1.0) -> float:
    if max_in == min_in:
        return min_out
    return min_out + (max_out - min_out) * (val - min_in) / (max_in - min_in)


def energy_pulse_effect(data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Brightness pulses with loudness + strong flash on beat/peak."""
    loudness = data.get("loudness", 20000)
    beat = data.get("beat", {}).get("flags", 0) if isinstance(data.get("beat"), dict) else data.get("beat", 0)
    peak = data.get("peak", 0)

    # Loudness normalized roughly to 0-1
    energy = _normalize(loudness, 0, 65535, 0.0, 1.0)
    sensitivity = config.get("sensitivity", 1.0)
    energy = min(1.0, energy * sensitivity)

    brightness = int(energy * (config.get("brightness_max", 100) - config.get("brightness_min", 5)) + config.get("brightness_min", 5))
    brightness = int(brightness / 100 * 65535)

    # Hue can slowly shift or be fixed; here we use a base + some energy influence
    hue = (config.get("hue_shift", 0) * 182) % 65535   # rough conversion

    sat = 45000
    flash = bool(beat or peak > 120) and config.get("flash_on_beat", True)

    return {
        "hue": hue,
        "saturation": sat,
        "brightness": brightness,
        "kelvin": 3500,
        "flash": flash,
        "flash_duration_ms": config.get("flash_duration_ms", 80),
        "transition_ms": 70,
    }


def spectrum_bands_effect(data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Map spectrum bins to different aspects (simple version: average + centroid hue)."""
    spectrum = data.get("spectrum", [])
    if not spectrum:
        return energy_pulse_effect(data, config)

    n = len(spectrum)
    # Simple energy from average magnitude
    avg = sum(spectrum) / n
    energy = _normalize(avg, 0, 65535, 0.0, 1.0) * config.get("sensitivity", 1.0)

    # Dominant "color" from weighted bin index (low freq = warmer hue)
    if n > 0:
        weighted = sum(i * spectrum[i] for i in range(n))
        centroid = weighted / (sum(spectrum) or 1)
        hue = int((centroid / n) * 40000 + config.get("hue_shift", 0) * 182) % 65535
    else:
        hue = config.get("hue_shift", 0) * 182

    brightness = int(energy * (config.get("brightness_max", 100) - 10) + 10)
    brightness = int(brightness / 100.0 * 65535)

    return {
        "hue": hue,
        "saturation": 50000,
        "brightness": brightness,
        "kelvin": 4000,
        "flash": False,
        "transition_ms": 90,
    }


def dominant_hue_effect(data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Hue follows dominant frequency (bass = red/orange, mids=green, highs=blue)."""
    f_peak = data.get("f_peak", {})
    freq = f_peak.get("freq", 440) if isinstance(f_peak, dict) else 440
    amp = f_peak.get("amp", 20000) if isinstance(f_peak, dict) else 20000

    # Map freq roughly to hue (log-ish perception)
    if freq < 150:
        hue = 0          # red
    elif freq < 400:
        hue = 5000       # orange
    elif freq < 1200:
        hue = 12000      # yellow-green
    elif freq < 4000:
        hue = 25000      # cyan
    else:
        hue = 45000      # blue-purple

    hue = (hue + config.get("hue_shift", 0) * 182) % 65535

    energy = _normalize(amp, 0, 65535, 0.2, 1.0) * config.get("sensitivity", 1.0)
    brightness = int(energy * (config.get("brightness_max", 100) - config.get("brightness_min", 5)) + config.get("brightness_min", 5))
    brightness = int(brightness / 100 * 65535)

    return {
        "hue": hue,
        "saturation": 55000,
        "brightness": brightness,
        "kelvin": 0,  # use hue instead of kelvin for color
        "flash": False,
        "transition_ms": 120,
    }


def beat_strobe_effect(data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Strong beat-driven strobe with energy color underneath."""
    base = energy_pulse_effect(data, config)
    beat = data.get("beat", {}).get("flags", 0) if isinstance(data.get("beat"), dict) else 0
    peak = data.get("peak", 0)

    if beat or peak > 150:
        base["flash"] = True
        base["brightness"] = min(65535, base.get("brightness", 30000) + 25000)
        base["hue"] = 0  # white flash
        base["saturation"] = 0
    return base


def custom_effect(data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Placeholder for user-defined mapping. Extend this function."""
    logger.info("Using custom effect placeholder — returning energy_pulse")
    return energy_pulse_effect(data, config)