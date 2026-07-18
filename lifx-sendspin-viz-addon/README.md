# LIFX SendSpin Music Visualizer Add-on for Home Assistant

Real-time music visualization for your LIFX lights, driven by Music Assistant via the open SendSpin protocol.

This add-on connects to your Music Assistant SendSpin server as a **visualizer** client, receives real-time audio analysis data (spectrum, loudness, beat, peaks), and translates it into dynamic color, brightness, and effects on your LIFX smart lights — perfectly in sync with your multi-room audio.

## Features
- Native SendSpin `visualizer@v1` role support (via aiosendspin library)
- Direct low-latency control of LIFX bulbs via LAN protocol (no cloud, no HA light service latency)
- Multiple visualization effects: energy pulse, beat flash, spectrum-to-color mapping, dominant frequency hue
- Supports single-zone and multi-zone LIFX lights (e.g. LIFX Z, Beam)
- Smooth fading, sensitivity control, per-effect tuning
- Auto-discovery of LIFX lights or manual selection by label/MAC
- **Advanced NiceGUI Web UI** (ingress) with live animated spectrum analyzer, real-time metrics (loudness, dominant frequency, beat detection), on-the-fly controls (effect, sensitivity, toggle), and controlled lights list
- Fully configurable via Home Assistant add-on options
- Runs alongside Music Assistant — no extra audio capture needed

## Requirements
- Home Assistant with Supervisor (add-ons supported)
- Music Assistant add-on or integration with SendSpin provider enabled (it runs the SendSpin server on port 8927 by default)
- LIFX lights on the same local network as Home Assistant
- (Optional but recommended) Several LIFX bulbs or a multi-zone strip for richer viz

## Installation Instructions

### Prerequisites
- Home Assistant with Supervisor
- Music Assistant with SendSpin provider enabled (port 8927)
- LIFX lights on the same local network
- (Recommended) MQTT broker enabled in Home Assistant

### Step-by-Step Installation

**Option 1: Add as Custom Repository (Recommended)**

1. Download and extract the `lifx-sendspin-viz-addon.zip` file.
2. Upload the `lifx-sendspin-viz-addon` folder to your Home Assistant server (e.g. `/addons/lifx-sendspin-viz-addon` via Samba or SSH).
3. In Home Assistant go to:
   **Settings → Add-ons → Add-on Store → ⋮ (top right) → Repositories → Add**
4. Add this repository URL (or your fork):
   `https://github.com/your-org/lifx-sendspin-viz-addon`
5. Refresh the page, find **"LIFX SendSpin Music Visualizer"**, and click **Install**.
6. After installation, configure it (see below) and click **Start**.

**Option 2: Local / Manual Install**

```bash
# Via SSH on your HA server
cd /addons
# Copy or clone the folder here
```

Then reload the Add-on Store.

### Configuration

In the add-on **Configuration** tab, set at minimum:

| Option                    | Example Value                              | Description |
|---------------------------|--------------------------------------------|-----------|
| `sendspin_url`            | `ws://homeassistant.local:8927/sendspin`  | Your Music Assistant SendSpin address |
| `client_name`             | `LIFX Visualizer`                         | Name visible in Music Assistant |
| `lifx_discover_all`       | `true`                                    | Or use specific labels below |
| `effect`                  | `energy_pulse`                            | Starting visualization style |
| `sensitivity`             | `1.0`                                     | Reactivity (0.1 – 3.0) |
| `mqtt_host`               | `homeassistant.local`                     | Enables HA auto-discovery entities |

Click **Save**, then **Start** the add-on.

### Accessing the Web UI

Once running, click the **Web UI** button on the add-on page.  
You will get a beautiful real-time dashboard with:
- Live spectrum analyzer
- Loudness, dominant frequency & beat detection
- On-the-fly effect & sensitivity controls
- List of controlled lights

### Home Assistant Entities (Auto-Discovery)

If MQTT is configured, these entities appear automatically:
- `switch.lifx_music_viz_enabled`
- `sensor.lifx_music_viz_loudness`
- `sensor.lifx_music_viz_beat`

You can use them in dashboards and automations.

### Testing

Play any music through Music Assistant (SendSpin-backed players).  
The lights and Web UI should react in real time.

## Visualization Effects (configurable)

| Effect              | Description                                      | Best for                  |
|---------------------|--------------------------------------------------|---------------------------|
| `energy_pulse`      | Brightness follows loudness + beat flashes      | Ambient + party           |
| `spectrum_bands`    | Different lights or zones react to freq bands   | Multi-bulb or multi-zone  |
| `dominant_hue`      | Hue shifts with dominant frequency (bass=warm)  | Color mood sync           |
| `beat_strobe`       | Strong white flashes on beats + energy color    | High energy parties       |

You can extend `app/effects.py` with custom mappings.

## How SendSpin Visualization Works

The add-on registers as a `visualizer@v1` client.

It receives binary messages with:
- `loudness` (A-weighted, scaled)
- `beat` + downbeat flags
- `f_peak` (dominant freq + amplitude)
- `spectrum` (configurable number of mel/log/lin bins)
- `peak` (onset strength)

Data is timestamped for perfect sync with audio timeline. The client smooths and maps these features to LIFX HSBK commands at your chosen rate.

See the official spec: https://www.sendspin-audio.com/spec or GitHub Sendspin/spec

## Development / Extending

The core logic is in `app/`:

- `sendspin_client.py`: Handles aiosendspin connection + visualizer role + parsing binary viz data
- `lifx_controller.py`: Discovery, rate-limited color updates, multi-zone support using `lifxlan`
- `effects.py`: Mapping functions (loudness→brightness, spectrum→hue/sat, beat→flash)
- `main.py`: Async orchestration, config reload, status web server (for ingress)

To add a new effect or improve smoothing, edit `effects.py` and the mapping in `main.py`.

Pull requests welcome!

## Troubleshooting

- **No lights reacting**: Check logs for LIFX discovery (UDP 56700 must be open), verify bulb labels exactly match (case sensitive). Test with `lifxlan` examples.
- **No SendSpin connection**: Ensure Music Assistant SendSpin provider is running and port 8927 is reachable from the add-on container. Use `auto` for mDNS if supported.
- **Choppy / high latency**: Lower `update_rate_hz` (bulbs have ~10-20 updates/sec practical limit). Increase smoothing.
- **Lights stuck in viz mode**: The add-on releases control when viz is disabled or stream ends. You can also use HA's LIFX integration alongside (they coexist reasonably).
- Logs are in add-on Log tab.

## License
Apache 2.0 (same as SendSpin / aiosendspin)

Built with ❤️ for the Open Home ecosystem and LIFX users who want their lights to *feel* the music.

---

**Note**: This is an initial implementation. Full production-ready version would include more robust error handling, persistent light state restoration, MQTT/Home Assistant entity exposure for enabling viz per room, and a polished NiceGUI or custom frontend for live spectrum visualizer. Contributions encouraged!