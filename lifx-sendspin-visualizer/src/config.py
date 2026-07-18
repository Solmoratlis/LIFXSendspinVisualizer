from pydantic import BaseModel, Field
from typing import List
import yaml

class MusicAssistantConfig(BaseModel):
    server_ip: str
    sendspin_port: int = 8927

class LightsConfig(BaseModel):
    beams: List[str]
    downlights: List[str]

class MappingConfig(BaseModel):
    mode: str = "advanced"
    bass_hue: int = 0
    mid_hue: int = 120
    high_hue: int = 240
    beat_pulse_duration_ms: int = 120
    energy_brightness_mult: float = 1.3
    beam_zone_count: int = 10
    update_rate_hz: int = 25

class PerformanceConfig(BaseModel):
    max_messages_per_sec: int = 18
    default_transition_ms: int = 70

class AppConfig(BaseModel):
    music_assistant: MusicAssistantConfig
    lights: LightsConfig
    mapping: MappingConfig = MappingConfig()
    performance: PerformanceConfig = PerformanceConfig()

def load_config(path: str = "config.yaml") -> AppConfig:
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    return AppConfig(**data)
