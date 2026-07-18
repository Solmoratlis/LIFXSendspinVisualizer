"""
Visualization effect mappers with advanced smoothing support.
"""

import logging
from typing import Any, Dict, Optional

from .smoothing import VisualizationSmoother

logger = logging.getLogger(__name__)

_global_smoother: Optional[VisualizationSmoother] = None

def get_smoother(config: Dict) -> VisualizationSmoother:
    global _global_smoother
    if _global_smoother is None:
        _global_smoother = VisualizationSmoother(config)
    return _global_smoother


def get_effect_mapper(effect_name: str):
    """Factory returning the mapper function for the chosen effect."""
    mappers = {
        "energy_pulse": energy_pulse_effect,
        "spectrum_bands": spectrum_bands_effect,
        "dominant_hue": dominant_hue_effect,
        "beat_strobe": beat_strobe_effect,
        "rainbow_energy": rainbow_energy_effect,
        "bass_punch": bass_punch_effect,
        "frequency_sweep": frequency_sweep_effect,
        "calm_ambient": calm_ambient_effect,
        "party_strobe": party_strobe_effect,
        "custom": custom_effect,
    }
    return mappers.get(effect_name, energy_pulse_effect)


def _normalize(val: int | float, min_in=0, max_in=65535, min_out=0.0, max_out=1.0) -> float:
    if max_in == min_in:
        return min_out
    return min_out + (max_out - min_out) * (val - min_in) / (max_in - min_in)


def energy_pulse_effect(data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Brightness pulses with loudness + strong flash on beat/peak. Uses smoothed data when available."""
    smoother = get_smoother(config)
    smoothed = smoother.process(data)

    energy = smoothed.get("energy_norm", 0.5) * config.get("sensitivity", 1.0)
    energy = min(1.0, max(0.0, energy))

    brightness = int(energy * (config.get("brightness_max", 100) - config.get("brightness_min", 5)) + config.get("brightness_min", 5))
    brightness = int(brightness / 100 * 65535)

    hue = (config.get("hue_shift", 0) * 182) % 65535
    sat = 45000

    is_beat = smoothed.get("is_beat", False) or smoothed.get("beat_flash", 0) > 0.6
    flash = is_beat and config.get("flash_on_beat", True)

    return {
        "hue": hue,
        "saturation": sat,
        "brightness": brightness,
        "kelvin": 3500,
        "flash": flash,
        "flash_duration_ms": config.get("flash_duration_ms", 80),
        "transition_ms": 70,
        "spectrum_norm": smoothed.get("spectrum_norm", []),
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


# ===================== NEW EFFECTS =====================

def rainbow_energy_effect(data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Hue slowly cycles while brightness follows energy. Great party effect."""
    smoother = get_smoother(config)
    smoothed = smoother.process(data)

    energy = smoothed.get("energy_norm", 0.5) * config.get("sensitivity", 1.0)
    brightness = int(energy * (config.get("brightness_max", 100) - 10) + 10)
    brightness = int(brightness / 100 * 65535)

    # Slowly rotating hue based on time + energy
    import time
    base_hue = int((time.time() * 40) % 65535)
    hue = (base_hue + int(energy * 8000)) % 65535

    return {
        "hue": hue,
        "saturation": 55000,
        "brightness": brightness,
        "kelvin": 0,
        "flash": False,
        "transition_ms": 80,
    }


def bass_punch_effect(data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Strong response to bass / low frequencies. Good for drums and bass-heavy music."""
    smoother = get_smoother(config)
    smoothed = smoother.process(data)

    energy = smoothed.get("energy_norm", 0.4) * config.get("sensitivity", 1.2)
    brightness = int(energy * (config.get("brightness_max", 100) - 5) + 5)
    brightness = int(brightness / 100 * 65535)

    # Warm colors for bass
    hue = (config.get("hue_shift", 0) + 10) * 182 % 65535
    sat = 60000

    flash = smoothed.get("is_beat", False) and config.get("flash_on_beat", True)

    return {
        "hue": hue,
        "saturation": sat,
        "brightness": brightness,
        "kelvin": 2700,
        "flash": flash,
        "flash_duration_ms": 60,
        "transition_ms": 50,
    }


def frequency_sweep_effect(data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Color smoothly sweeps based on dominant frequency movement."""
    f_peak = data.get("f_peak", {})
    freq = f_peak.get("freq", 440) if isinstance(f_peak, dict) else 440
    amp = f_peak.get("amp", 20000) if isinstance(f_peak, dict) else 20000

    # Map frequency to hue (low = warm, high = cool)
    if freq < 200:
        hue = 0
    elif freq < 800:
        hue = 8000
    elif freq < 3000:
        hue = 20000
    else:
        hue = 45000

    hue = (hue + config.get("hue_shift", 0) * 182) % 65535

    energy = _normalize(amp, 0, 65535, 0.3, 1.0) * config.get("sensitivity", 1.0)
    brightness = int(energy * (config.get("brightness_max", 100) - 15) + 15)
    brightness = int(brightness / 100 * 65535)

    return {
        "hue": hue,
        "saturation": 48000,
        "brightness": brightness,
        "kelvin": 0,
        "flash": False,
        "transition_ms": 120,
    }


def calm_ambient_effect(data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Gentle, slow pulsing with soft pastel colors. Nice for background listening."""
    smoother = get_smoother(config)
    smoothed = smoother.process(data)

    energy = smoothed.get("energy_norm", 0.35) * config.get("sensitivity", 0.8)
    brightness = int(energy * (config.get("brightness_max", 60) - 20) + 20)
    brightness = int(brightness / 100 * 65535)

    # Soft shifting pastel colors
    import time
    hue = int((time.time() * 8 + energy * 3000) % 65535)

    return {
        "hue": hue,
        "saturation": 30000,
        "brightness": brightness,
        "kelvin": 4000,
        "flash": False,
        "transition_ms": 300,
    }


def party_strobe_effect(data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """High-energy strobe with rapid color changes. For parties and high BPM tracks."""
    smoother = get_smoother(config)
    smoothed = smoother.process(data)

    energy = smoothed.get("energy_norm", 0.6) * config.get("sensitivity", 1.3)
    brightness = int(energy * (config.get("brightness_max", 100) - 5) + 5)
    brightness = int(brightness / 100 * 65535)

    import time
    hue = int((time.time() * 120) % 65535)  # Fast color cycling

    flash = smoothed.get("is_beat", False) or smoothed.get("beat_flash", 0) > 0.5

    return {
        "hue": hue,
        "saturation": 65000,
        "brightness": brightness,
        "kelvin": 0,
        "flash": flash,
        "flash_duration_ms": 40,
        "transition_ms": 30,
    }


# ===================== EVEN MORE EFFECTS =====================

def fire_pulse_effect(data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Warm flickering fire-like effect. Great for cozy or intense moments."""
    smoother = get_smoother(config)
    smoothed = smoother.process(data)

    energy = smoothed.get("energy_norm", 0.5) * config.get("sensitivity", 1.1)
    brightness = int(energy * (config.get("brightness_max", 90) - 15) + 15)
    brightness = int(brightness / 100 * 65535)

    import time, random
    # Flicker + warm orange/red tones
    flicker = random.uniform(-8000, 8000)
    hue = (5000 + int(flicker)) % 65535

    return {
        "hue": hue,
        "saturation": 62000,
        "brightness": brightness,
        "kelvin": 2200,
        "flash": smoothed.get("is_beat", False),
        "flash_duration_ms": 50,
        "transition_ms": 40,
    }


def ice_cool_effect(data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Cold blue/cyan pulsing. Perfect for chill or electronic tracks."""
    smoother = get_smoother(config)
    smoothed = smoother.process(data)

    energy = smoothed.get("energy_norm", 0.45) * config.get("sensitivity", 0.9)
    brightness = int(energy * (config.get("brightness_max", 85) - 10) + 10)
    brightness = int(brightness / 100 * 65535)

    import time
    hue = int((time.time() * 15 + 28000) % 65535)  # Cool blue-cyan range

    return {
        "hue": hue,
        "saturation": 48000,
        "brightness": brightness,
        "kelvin": 0,
        "flash": False,
        "transition_ms": 180,
    }


def synthwave_effect(data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """80s synthwave / retrowave aesthetic. Pink + cyan vibes."""
    smoother = get_smoother(config)
    smoothed = smoother.process(data)

    energy = smoothed.get("energy_norm", 0.55) * config.get("sensitivity", 1.0)
    brightness = int(energy * (config.get("brightness_max", 95) - 5) + 5)
    brightness = int(brightness / 100 * 65535)

    import time
    # Alternate between pink and cyan
    t = time.time()
    if int(t) % 2 == 0:
        hue = 58000   # Pink
    else:
        hue = 42000   # Cyan

    return {
        "hue": hue,
        "saturation": 70000,
        "brightness": brightness,
        "kelvin": 0,
        "flash": smoothed.get("beat_flash", 0) > 0.7,
        "flash_duration_ms": 35,
        "transition_ms": 60,
    }


def pulse_chase_effect(data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Creates a pulsing 'wave' that chases across multizone lights."""
    smoother = get_smoother(config)
    smoothed = smoother.process(data)

    energy = smoothed.get("energy_norm", 0.5) * config.get("sensitivity", 1.0)
    brightness = int(energy * (config.get("brightness_max", 100) - 10) + 10)
    brightness = int(brightness / 100 * 65535)

    import time
    hue = int((time.time() * 25) % 65535)

    return {
        "hue": hue,
        "saturation": 55000,
        "brightness": brightness,
        "kelvin": 0,
        "flash": False,
        "transition_ms": 70,
        # Note: Multizone lights will interpret this as a chasing wave
    }


def beat_color_shift_effect(data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Changes color on every beat. Very reactive and fun."""
    smoother = get_smoother(config)
    smoothed = smoother.process(data)

    energy = smoothed.get("energy_norm", 0.5) * config.get("sensitivity", 1.2)
    brightness = int(energy * (config.get("brightness_max", 100) - 5) + 5)
    brightness = int(brightness / 100 * 65535)

    import time
    # Shift hue significantly on beat
    base = int(time.time() * 10)
    if smoothed.get("is_beat", False):
        base += 18000

    hue = (base * 1200) % 65535

    return {
        "hue": hue,
        "saturation": 60000,
        "brightness": brightness,
        "kelvin": 0,
        "flash": smoothed.get("is_beat", False),
        "flash_duration_ms": 55,
        "transition_ms": 45,
    }