"""
Visualization effects for LIFX lights driven by SendSpin data.
"""
import math
import random
import time
from typing import Any, Callable, Dict


def _brightness_from_energy(energy: float, cfg: Dict[str, Any]) -> int:
    sens = float(cfg.get("sensitivity", 1.0))
    energy = max(0.0, min(1.0, energy * sens))
    b_min = int(cfg.get("brightness_min", 5))
    b_max = int(cfg.get("brightness_max", 100))
    pct = b_min + energy * (b_max - b_min)
    return int(pct / 100 * 65535)


def energy_pulse(data: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    energy = float(data.get("loudness", data.get("peak", 0.5)))
    brightness = _brightness_from_energy(energy, cfg)
    hue = int((time.time() * 30) % 65535)
    return {
        "hue": hue,
        "saturation": 50000,
        "brightness": brightness,
        "kelvin": 0,
        "transition_ms": 80,
    }


def spectrum_bands(data: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    spectrum = data.get("spectrum") or [0.5]
    energy = sum(spectrum) / max(1, len(spectrum))
    brightness = _brightness_from_energy(energy, cfg)
    # Dominant band determines hue
    if spectrum:
        idx = max(range(len(spectrum)), key=lambda i: spectrum[i])
        hue = int(idx / max(1, len(spectrum) - 1) * 65535)
    else:
        hue = 30000
    return {
        "hue": hue,
        "saturation": 55000,
        "brightness": brightness,
        "kelvin": 0,
        "transition_ms": 60,
    }


def dominant_hue(data: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    energy = float(data.get("loudness", 0.5))
    brightness = _brightness_from_energy(energy, cfg)
    f_peak = float(data.get("f_peak", 1000))
    # Map frequency to hue (low = red, high = blue/violet)
    hue = int(min(65535, max(0, (math.log10(max(20, f_peak)) - 1.3) / 3.0 * 65535)))
    return {
        "hue": hue,
        "saturation": 48000,
        "brightness": brightness,
        "kelvin": 0,
        "transition_ms": 100,
    }


def beat_strobe(data: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    energy = float(data.get("loudness", 0.5))
    brightness = _brightness_from_energy(energy, cfg)
    flash = bool(data.get("beat", False))
    hue = int((time.time() * 90) % 65535) if flash else int((time.time() * 20) % 65535)
    return {
        "hue": hue,
        "saturation": 65000 if flash else 40000,
        "brightness": 65535 if flash else brightness,
        "kelvin": 0,
        "transition_ms": 30 if flash else 90,
    }


def rainbow_energy(data: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    energy = float(data.get("loudness", 0.5))
    brightness = _brightness_from_energy(energy, cfg)
    hue = int((time.time() * 40 + energy * 10000) % 65535)
    return {
        "hue": hue,
        "saturation": 60000,
        "brightness": brightness,
        "kelvin": 0,
        "transition_ms": 70,
    }


def bass_punch(data: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    spectrum = data.get("spectrum") or [0.5]
    bass = spectrum[0] if spectrum else float(data.get("loudness", 0.5))
    energy = float(data.get("loudness", 0.5))
    brightness = _brightness_from_energy(max(bass, energy * 0.7), cfg)
    return {
        "hue": 0,  # red
        "saturation": 65000,
        "brightness": brightness,
        "kelvin": 0,
        "transition_ms": 40,
    }


def calm_ambient(data: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    energy = float(data.get("loudness", 0.4)) * 0.6
    brightness = _brightness_from_energy(energy, cfg)
    hue = int((time.time() * 8 + 20000) % 65535)
    return {
        "hue": hue,
        "saturation": 30000,
        "brightness": brightness,
        "kelvin": 0,
        "transition_ms": 200,
    }


def party_strobe(data: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    energy = float(data.get("loudness", 0.6))
    brightness = _brightness_from_energy(energy * 1.2, cfg)
    flash = bool(data.get("beat", False))
    hue = random.randint(0, 65535) if flash else int((time.time() * 100) % 65535)
    return {
        "hue": hue,
        "saturation": 70000,
        "brightness": brightness,
        "kelvin": 0,
        "transition_ms": 25,
    }


def fire_pulse(data: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    energy = float(data.get("loudness", 0.5))
    brightness = _brightness_from_energy(energy, cfg)
    hue = 3000 + int(random.uniform(-2000, 4000))
    return {
        "hue": hue % 65535,
        "saturation": 60000,
        "brightness": brightness,
        "kelvin": 2200,
        "transition_ms": 50,
    }


def ice_cool(data: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    energy = float(data.get("loudness", 0.4))
    brightness = _brightness_from_energy(energy * 0.9, cfg)
    hue = int((time.time() * 12 + 42000) % 65535)
    return {
        "hue": hue,
        "saturation": 45000,
        "brightness": brightness,
        "kelvin": 0,
        "transition_ms": 160,
    }


EFFECTS: Dict[str, Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]] = {
    "energy_pulse": energy_pulse,
    "spectrum_bands": spectrum_bands,
    "dominant_hue": dominant_hue,
    "beat_strobe": beat_strobe,
    "rainbow_energy": rainbow_energy,
    "bass_punch": bass_punch,
    "calm_ambient": calm_ambient,
    "party_strobe": party_strobe,
    "fire_pulse": fire_pulse,
    "ice_cool": ice_cool,
}


def get_effect_mapper(name: str) -> Callable:
    return EFFECTS.get(name, energy_pulse)