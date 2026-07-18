"""
Advanced smoothing, attack, and decay envelopes for music visualization.
Provides musically pleasing response instead of raw jumps.
"""

import time
from typing import List, Dict, Any


class EnvelopeSmoother:
    """Per-channel smoother with attack and decay."""

    def __init__(self, attack: float = 0.6, decay: float = 0.25, peak_hold: float = 0.4):
        self.attack = attack      # How fast it rises (0-1, higher = faster)
        self.decay = decay        # How fast it falls
        self.peak_hold = peak_hold
        self.value = 0.0
        self.peak = 0.0
        self.last_update = time.monotonic()

    def update(self, target: float) -> float:
        now = time.monotonic()
        dt = min(now - self.last_update, 0.1)  # cap dt
        self.last_update = now

        if target > self.value:
            # Attack
            self.value += (target - self.value) * self.attack * (dt * 20)
        else:
            # Decay
            self.value += (target - self.value) * self.decay * (dt * 20)

        # Peak hold
        if target > self.peak:
            self.peak = target
        else:
            self.peak = max(0, self.peak - self.peak_hold * (dt * 10))

        return max(0.0, min(1.0, self.value))


class VisualizationSmoother:
    """Full smoother for all visualization features."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        decay = config.get("decay", 0.75)
        self.loudness = EnvelopeSmoother(attack=0.7, decay=decay * 0.8)
        self.energy = EnvelopeSmoother(attack=0.65, decay=decay)
        self.spectrum_smoothers: List[EnvelopeSmoother] = []
        self.peak_hold = EnvelopeSmoother(attack=0.9, decay=0.15, peak_hold=0.6)
        self.beat_flash = 0.0

    def process(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process raw SendSpin data into smoothed values."""
        smoothed = raw_data.copy()

        # Loudness
        loud = raw_data.get("loudness", 0) / 65535.0
        smoothed["loudness_norm"] = self.loudness.update(loud)

        # Overall energy (from loudness + peak)
        peak = raw_data.get("peak", 0) / 255.0
        energy = max(loud, peak)
        smoothed["energy_norm"] = self.energy.update(energy)

        # Spectrum
        spectrum = raw_data.get("spectrum", [])
        if not self.spectrum_smoothers or len(self.spectrum_smoothers) != len(spectrum):
            self.spectrum_smoothers = [EnvelopeSmoother(attack=0.55, decay=self.config.get("decay", 0.75)) 
                                       for _ in spectrum]

        smoothed_spectrum = []
        for i, val in enumerate(spectrum):
            norm = val / 65535.0
            smoothed_spectrum.append(self.spectrum_smoothers[i].update(norm))
        smoothed["spectrum_norm"] = smoothed_spectrum

        # Peak hold (for visual flair)
        smoothed["peak_norm"] = self.peak_hold.update(peak)

        # Beat handling with flash envelope
        beat = raw_data.get("beat", {}).get("flags", 0) if isinstance(raw_data.get("beat"), dict) else raw_data.get("beat", 0)
        if beat:
            self.beat_flash = 1.0
        else:
            self.beat_flash = max(0, self.beat_flash - 0.25)

        smoothed["beat_flash"] = self.beat_flash
        smoothed["is_beat"] = bool(beat)

        # Dominant frequency (pass through)
        smoothed["f_peak"] = raw_data.get("f_peak", {})

        return smoothed