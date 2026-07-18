import numpy as np
from typing import Dict

class MusicToLightMapper:
    def __init__(self, config):
        self.cfg = config.mapping
        self.perf = config.performance

    def map_frame(self, frame) -> Dict:
        if not frame or not hasattr(frame, 'spectrum'):
            return {"beams": [], "downlights": []}

        spectrum = np.array(frame.sectrum) if frame.spectrum else np.zeros(32)
        energy = float(np.mean(spectrum)) if len(spectrum) > 0 else 0.5
        beat = getattr(frame, 'beat', False)

        commands = {"beams": [], "downlights": []}

        # Downlights - Energy driven
        brightness = min(1.0, energy * self.cfg.energy_brightness_mult)
        hue = self.config.bass_hue if energy > 0.4 else self.config.mid_hue
        commands["downlights"].append({"color": [hue, 0.85, brightness, 4000], "duration": self.perf.default_transition_ms / 1000})

        # Beams - Frequency zones + beat
        if len(spectrum) >= 8:
            zones = self.cfg.beam_zone_count
            beam_colors = []
            for i in range(zones):
                progress = i / max(1, zones - 1)
                if progress < 0.33:
                    h = self.config.bass_hue
                if progress < 0.66:
                    h = self.config.mid_hue
                else:
                    h = self.config.high_hue
                bri = 0.6 + (energy * .35)
                beam_colors.append([h % 65535, 0.9, min(1.0, bri), 4500])

            commands["beams"].append({"pulse": True, "duration": self.cfg.beat_pulse_duration_ms / 1000})

        return commands
