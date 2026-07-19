# LIFX SendSpin Music Visualizer

Real-time music visualization for **LIFX lights**, driven by **Music Assistant** via the **SendSpin** protocol.

This is a **standalone service** (Docker or plain Python) that follows the same architecture used by successful Hue + SendSpin visualizers.

---

## Features

- Connects to Music Assistant’s SendSpin server as a visualizer client
- Controls LIFX lights (including multizone) in real time
- **27 visualization effects**
- Polished live web UI (loudness, beat, spectrum, peak, stats)
- **Real data only** — no simulated / fallback data
- Detailed connection logging for easy troubleshooting
- Rich configuration (sensitivity, hue shift, saturation scale, beat flash, etc.)
- Runs next to Home Assistant via Docker Compose or as a plain Python process

---

## Quick Start (Docker Compose)

```bash
# 1. Extract
unzip lifx-sendspin-standalone.zip
cd lifx-sendspin-standalone

# 2. Create config
cp config.example.yaml config.yaml
# Edit config.yaml with your SendSpin URL and preferences

# 3. Start
docker compose up -d --build

# 4. Open the web UI
open http://localhost:8099
```

View logs:

```bash
docker compose logs -f
```

---

## Configuration

### Full example (`config.yaml`)

```yaml
sendspin:
  url: "ws://homeassistant.local:8927/sendspin"
  client_name: "LIFX Visualizer"
  # psk: "optional-pre-shared-key-if-required"
  reconnect_delay_sec: 5

lifx:
  discover_all: true
  # light_labels: ["Living Room", "Kitchen Island"]
  # mac_addresses: ["d0:73:d5:xx:xx:xx"]

visualization:
  effect: "energy_pulse"
  sensitivity: 1.0
  update_rate_hz: 15
  brightness_min: 5
  brightness_max: 100
  enabled: true
  default_transition_ms: 70
  saturation_scale: 1.0
  hue_shift_deg: 0
  force_beat_flash: false
  spectrum_bins: 8
  spectrum_weight: 1.0

web:
  host: "0.0.0.0"
  port: 8099

logging:
  level: "INFO"
```

### Visualization options

| Option                  | Description                                         | Default |
|-------------------------|-----------------------------------------------------|---------|
| `effect`                | Name of the effect to use                           | `energy_pulse` |
| `sensitivity`           | Overall reactivity (0.1 – 3.0+)                     | `1.0`   |
| `update_rate_hz`        | Max color updates sent to LIFX per second           | `15`    |
| `brightness_min`        | Minimum brightness %                                | `5`     |
| `brightness_max`        | Maximum brightness %                                | `100`   |
| `default_transition_ms` | Fallback transition when effect does not set one    | `70`    |
| `saturation_scale`      | Multiply effect saturation (0.5 – 1.5)              | `1.0`   |
| `hue_shift_deg`         | Global hue offset in degrees (0 – 360)              | `0`     |
| `force_beat_flash`      | Force full-brightness flash on every beat           | `false` |
| `spectrum_weight`       | How strongly spectrum influences relevant effects   | `1.0`   |
| `enabled`               | Master on/off                                       | `true`  |

### Environment variable overrides

| Variable        | Description                          | Default                                      |
|-----------------|--------------------------------------|----------------------------------------------|
| `SENDSPIN_URL`  | Music Assistant SendSpin WebSocket   | `ws://homeassistant.local:8927/sendspin`     |
| `CLIENT_NAME`   | Name shown to Music Assistant        | `LIFX Visualizer`                            |
| `EFFECT`        | Visualization effect                 | `energy_pulse`                               |
| `SENSITIVITY`   | 0.1 – 3.0                            | `1.0`                                        |
| `ENABLED`       | Enable / disable visualization       | `true`                                       |

---

## Available Effects (27)

| Effect              | Style / Vibe                          |
|---------------------|---------------------------------------|
| `energy_pulse`      | Classic energy-driven color pulse     |
| `spectrum_bands`    | Hue follows dominant spectrum band    |
| `dominant_hue`      | Color from dominant frequency         |
| `beat_strobe`       | Strong flash on every beat            |
| `rainbow_energy`    | Smooth rainbow driven by energy       |
| `bass_punch`        | Red punch on bass / low energy        |
| `calm_ambient`      | Soft, slow ambient wash               |
| `party_strobe`      | High-energy party strobe              |
| `fire_pulse`        | Warm flickering fire                  |
| `ice_cool`          | Cold blue / cyan                      |
| `synthwave`         | Pink + cyan retrowave                 |
| `galaxy_swirl`      | Slow deep-space swirl                 |
| `matrix_rain`       | Green digital rain                    |
| `heartbeat_pulse`   | Red heartbeat on beats                |
| `neon_grid`         | Sharp neon cyberpunk                  |
| `disco_ball`        | Classic disco color flashes           |
| `frequency_sweep`   | Hue follows dominant frequency        |
| `sunrise_sunset`    | Warm → cool progression by energy     |
| `ocean_wave`        | Slow blue-green undulation            |
| `lava_lamp`         | Warm orange / magenta morph           |
| `cyberpunk`         | Magenta + electric blue               |
| `aurora`            | Soft greens / teals / purples         |
| `pulse_chase`       | Moving pulse / chase feel             |
| `mono_white`        | Neutral white brightness only         |
| `mono_warm`         | Warm white (2700 K)                   |
| `mono_cool`         | Cool white (6500 K)                   |
| `random_hue`        | Random color change on beat           |

---

## Running without Docker

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp config.example.yaml config.yaml
# edit config.yaml
python run.py
```

---

## Web UI

Once running, open:

```
http://localhost:8099
```

You will see:

- Live loudness and peak meters
- Beat indicator
- 8-band spectrum
- Connection status
- Frame / beat / update counters
- Current effect and dominant frequency

---

## Connection & Logging

The client logs every important connection step:

```
[CONNECT] Attempt #1
[CONNECT] URL          : ws://homeassistant.local:8927/sendspin
[CONNECT] Client name  : LIFX Visualizer
[CONNECT] Opening WebSocket...
[CONNECT] WebSocket OPEN in 42 ms
[CONNECT] Status: CONNECTED (waiting for visualization frames)
[RECV] Listening for frames...
[RECV] First binary frame received (37 bytes)
```

If something fails you will see clear messages such as:

- Connection refused
- Timeout
- Invalid handshake (possible Noise / PSK requirement)
- Network errors

### Important note about SendSpin / Noise

Music Assistant’s SendSpin server may require a **Noise KKpsk2** handshake and a pre-shared key (PSK).

- If a plain WebSocket connection is accepted, you get real data immediately.
- If the server requires the full Noise handshake, you will see a handshake / connection error in the logs.
- In that case, obtain the correct PSK / prologue from the Music Assistant team and configure it under `sendspin.psk`.

This project uses **real data only**. It will never generate simulated visualization data.

---

## Architecture

```
Music Assistant (SendSpin server)
        │
        │  WebSocket (visualization frames)
        ▼
LIFX SendSpin Visualizer (this service)
        │
        ├── Effect mapper (27 effects)
        ├── LIFX controller (lifxlan)
        └── Web UI (port 8099)
        │
        ▼
LIFX lights
```

This is the same pattern used by the working Hue + SendSpin visualizers: a standalone service that can freely install Python packages and talk directly to Music Assistant.

---

## Troubleshooting

| Symptom | What to check |
|---------|----------------|
| Web UI shows DISCONNECTED | Look at the container / process logs for `[CONNECT]` errors |
| No lights reacting | Confirm lights are discovered, effect is enabled, and frames are arriving (`[RECV] First binary frame...`) |
| Connection refused | Music Assistant running? Correct host/port in `sendspin.url`? |
| Handshake / InvalidHandshake | Server may require Noise PSK — see note above |
| Lights discovered = 0 | Check network (host network mode recommended in Docker) |

---

## License

Apache 2.0
