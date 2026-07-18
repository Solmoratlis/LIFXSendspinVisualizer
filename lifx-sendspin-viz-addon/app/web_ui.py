"""
Advanced Web UI for LIFX SendSpin Music Visualizer using NiceGUI.
Provides a beautiful real-time dashboard with live spectrum visualization,
controls, and status.
"""

import asyncio
from typing import Any, Dict, List

from nicegui import ui, app

# Shared state (will be updated from main.py)
viz_state: Dict[str, Any] = {
    "connected": False,
    "last_data": {},
    "lights": [],
    "effect": "energy_pulse",
    "sensitivity": 1.0,
    "enabled": True,
    "frames": 0,
    "updates_sent": 0,
}

def create_ui(app_instance: Any = None):
    """Create the NiceGUI interface. Call this once at startup."""

    ui.page_title("LIFX SendSpin Music Visualizer")
    ui.dark_mode()

    with ui.header().classes("bg-zinc-900"):
        ui.label("🎵 LIFX Music Visualizer").classes("text-2xl font-bold")
        ui.space()
        ui.label("Powered by SendSpin + Music Assistant").classes("text-sm opacity-70")

    with ui.row().classes("w-full gap-4 p-4"):
        # === Left column: Status & Controls ===
        with ui.card().classes("w-80"):
            ui.label("Status").classes("text-lg font-semibold mb-2")

            status_label = ui.label().bind_text_from(
                viz_state, "connected",
                backward=lambda c: "🟢 Connected to SendSpin" if c else "🔴 Disconnected"
            )

            ui.separator()

            with ui.row():
                ui.label("Effect:")
                effect_select = ui.select(
                    ["energy_pulse", "spectrum_bands", "dominant_hue", "beat_strobe"],
                    value=viz_state["effect"],
                    on_change=lambda e: update_config("effect", e.value)
                ).classes("w-full")

            with ui.row().classes("items-center"):
                ui.label("Sensitivity")
                sensitivity_slider = ui.slider(
                    min=0.1, max=3.0, step=0.1, value=viz_state["sensitivity"],
                    on_change=lambda e: update_config("sensitivity", e.value)
                ).classes("w-full")
                ui.label().bind_text_from(sensitivity_slider, "value", lambda v: f"{v:.1f}")

            ui.switch("Visualization Enabled", value=viz_state["enabled"],
                      on_change=lambda e: update_config("enabled", e.value))

            ui.button("Reconnect to SendSpin", on_click=reconnect).classes("w-full mt-2")

            ui.separator().classes("my-2")

            ui.label("Statistics").classes("font-semibold")
            ui.label().bind_text_from(
                viz_state, "frames", lambda f: f"Frames processed: {f}"
            )
            ui.label().bind_text_from(
                viz_state, "updates_sent", lambda u: f"Light updates sent: {u}"
            )

        # === Middle: Live Spectrum ===
        with ui.card().classes("flex-1"):
            ui.label("Live Spectrum Analyzer").classes("text-lg font-semibold mb-2")

            spectrum_container = ui.row().classes("w-full h-48 items-end gap-1 px-2")

            # Create 8 initial bars (will be updated dynamically)
            bars: List[ui.element] = []
            for i in range(8):
                bar = ui.element("div").classes(
                    "flex-1 bg-gradient-to-t from-blue-500 to-cyan-400 rounded-t transition-all duration-75"
                ).style("height: 10%; min-height: 4px;")
                bars.append(bar)

            # Store bars in state for updating
            viz_state["_bars"] = bars

            ui.label("Low → High Frequency").classes("text-xs text-center opacity-60 mt-1")

            # Current metrics row
            with ui.row().classes("w-full justify-between mt-4 text-sm"):
                ui.label().bind_text_from(
                    viz_state, "last_data",
                    backward=lambda d: f"Loudness: {int(d.get('loudness', 0) / 65535 * 100)}%"
                )
                ui.label().bind_text_from(
                    viz_state, "last_data",
                    backward=lambda d: f"Dominant: {d.get('f_peak', {}).get('freq', 0)} Hz"
                )
                beat_label = ui.label().bind_text_from(
                    viz_state, "last_data",
                    backward=lambda d: "🥁 BEAT!" if d.get("beat", {}).get("flags", 0) else ""
                ).classes("text-red-400 font-bold")

        # === Right: Controlled Lights ===
        with ui.card().classes("w-72"):
            ui.label("Controlled Lights").classes("text-lg font-semibold mb-2")

            lights_container = ui.column().classes("w-full")

            def refresh_lights():
                lights_container.clear()
                for light_name in viz_state.get("lights", []):
                    with lights_container:
                        with ui.row().classes("items-center"):
                            ui.icon("lightbulb", color="amber").classes("mr-2")
                            ui.label(light_name)

            refresh_lights()
            ui.button("Refresh Lights", on_click=refresh_lights).classes("w-full mt-2 text-xs")

    # Footer
    with ui.footer().classes("bg-zinc-900"):
        ui.label("Tip: Play music in Music Assistant → lights react automatically").classes("text-xs opacity-60")

    # Periodic UI updater
    async def update_ui():
        while True:
            await asyncio.sleep(0.15)  # ~7 fps UI refresh is smooth enough

            # Update spectrum bars from last_data
            last = viz_state.get("last_data", {})
            spectrum = last.get("spectrum", [])
            bars = viz_state.get("_bars", [])

            if spectrum and bars:
                n = min(len(spectrum), len(bars))
                for i in range(n):
                    magnitude = spectrum[i] / 65535.0
                    height = max(4, int(magnitude * 180))  # px
                    bars[i].style(f"height: {height}px;")

            # Force NiceGUI to refresh bindings
            ui.refresh()

    # Start the background updater
    ui.timer(0.2, update_ui, active=True)

    # Expose a way to update state from outside (called by main.py)
    app.on_startup(lambda: None)  # placeholder


def update_config(key: str, value: Any):
    """Update config and notify main app (in real version this would call back)."""
    viz_state[key] = value
    print(f"[WebUI] Config updated: {key} = {value}")
    # In a full implementation, this would trigger the main app to reload config


async def reconnect():
    """Trigger reconnect from UI."""
    print("[WebUI] Reconnect requested")
    # This would call into the main app's reconnect logic
    viz_state["connected"] = False  # temporary visual feedback
    await asyncio.sleep(1)
    viz_state["connected"] = True


# Convenience function to update visualization data from main loop
def update_viz_data(data: Dict[str, Any], stats: Dict[str, int], connected: bool = True):
    """Call this from main.py whenever new visualization data arrives."""
    viz_state["last_data"] = data
    viz_state["frames"] = stats.get("frames", 0)
    viz_state["updates_sent"] = stats.get("updates_sent", 0)
    viz_state["connected"] = connected

    # Also update lights list if provided
    if "lights" in data:
        viz_state["lights"] = data["lights"]