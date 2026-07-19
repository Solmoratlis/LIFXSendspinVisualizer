"""
Simple, reliable web UI for LIFX SendSpin Visualizer
Works well through Home Assistant Ingress (no ES modules issues)
Uses Starlette + Tailwind CSS
"""
import asyncio
import json
import logging
from typing import Any, Dict

from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

logger = logging.getLogger("lifx-sendspin-viz.web_ui")

# Shared state - updated by main.py via update_viz_data()
viz_state: Dict[str, Any] = {
    "loudness": 0.0,
    "beat": False,
    "spectrum": [0.0] * 8,
    "peak": 0.0,
    "effect": "energy_pulse",
    "enabled": True,
    "lights": [],
    "stats": {"frames": 0, "beats": 0, "updates_sent": 0},
    "connected": False,
}


def update_viz_data(data: Dict[str, Any], stats: Dict[str, Any], connected: bool = True):
    """Called from main.py to push live visualization data to the UI."""
    viz_state["loudness"] = float(data.get("loudness", 0.0))
    viz_state["beat"] = bool(data.get("beat", False))
    viz_state["spectrum"] = data.get("spectrum", [0.0] * 8)
    viz_state["peak"] = float(data.get("peak", 0.0))
    viz_state["stats"] = stats
    viz_state["connected"] = connected


async def status_endpoint(request):
    """JSON endpoint for the frontend to poll."""
    return JSONResponse(viz_state)


async def index(request):
    """Main dashboard HTML page."""
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LIFX SendSpin • Visualizer</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background-color: #0f172a; color: #e2e8f0; font-family: system_ui, sans-serif; }
        .bar { transition: height 80ms linear; }
        .beat-flash { animation: flash 120ms ease-out; }
        @keyframes flash {
            0% { background-color: #f87171; box-shadow: 0 0 15px #f87171; }
            100% { background-color: #334155; }
        }
        .metric { font-variant-numeric: tabular-nums; }
    </style>
</head>
<body class="min-h-screen bg-slate-950 text-slate-200 p-6">
    <div class="max-w-[1100px] mx-auto">
        
        <!-- Header -->
        <div class="flex items-center justify-between mb-8">
            <div class="flex items-center gap-3">
                <div class="w-9 h-9 bg-gradient-to-br from-cyan-400 to-blue-500 rounded-xl flex items-center justify-center">
                    <span class="text-slate-950 font-black text-xl">L</span>
                </div>
                <div>
                    <h1 class="text-3xl font-semibold tracking-tight">LIFX SendSpin</h1>
                    <p class="text-xs text-slate-500 -mt-1">Music Visualizer</p>
                </div>
            </div>
            
            <div class="flex items-center gap-3">
                <div id="conn-status"
                     class="text-xs px-3 py-1.5 rounded-full font-medium flex items-center gap-2 bg-red-500/10 text-red-400 border border-red-500/30">
                    <div class="w-1.5 h-1.5 bg-red-400 rounded-full animate-pulse"></div>
                    DISCONNECTED
                </div>
            </div>
        </div>

        <!-- Metrics Row -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            
            <!-- Loudness -->
            <div class="bg-slate-900 border border-slate-800 rounded-3xl p-5">
                <div class="flex justify-between items-baseline mb-3">
                    <div class="text-xs tracking-[1px] text-slate-500">LOUDNESS</div>
                    <div id="loudness-val" class="metric text-4xl font-semibold text-white tabular-nums">0.00</div>
                </div>
                <div class="h-2.5 bg-slate-800 rounded-full overflow-hidden">
                    <div id="loudness-bar" 
                         class="h-2.5 bg-gradient-to-r from-cyan-400 via-blue-400 to-indigo-400 rounded-full transition-all duration-100"
                         style="width:0%"></div>
                </div>
            </div>

            <!-- Beat -->
            <div class="bg-slate-900 border border-slate-800 rounded-3xl p-5">
                <div class="flex justify-between items-baseline mb-3">
                    <div class="text-xs tracking-[1px] text-slate-500">BEAT</div>
                    <div id="beat-val" class="metric text-4xl font-semibold text-white">—</div>
                </div>
                <div id="beat-box"
                     class="h-2.5 bg-slate-800 rounded-full flex items-center justify-center text-[10px] font-mono tracking-[1.5px] text-slate-500">
                    LISTENING
                </div>
            </div>

            <!-- Peak -->
            <div class="bg-slate-900 border border-slate-800 rounded-3xl p-5">
                <div class="flex justify-between items-baseline mb-3">
                    <div class="text-xs tracking-[1px] text-slate-500">PEAK</div>
                    <div id="peak-val" class="metric text-4xl font-semibold text-white tabular-nums">0.00</div>
                </div>
                <div class="h-2.5 bg-slate-800 rounded-full overflow-hidden">
                    <div id="peak-bar" 
                         class="h-2.5 bg-gradient-to-r from-violet-400 to-fuchsia-400 rounded-full transition-all duration-100"
                         style="width:0%"></div>
                </div>
            </div>
        </div>

        <!-- Spectrum -->
        <div class="bg-slate-900 border border-slate-800 rounded-3xl p-6 mb-6">
            <div class="flex items-center justify-between mb-4">
                <div>
                    <span class="text-sm font-medium">SPECTRUM</span>
                    <span class="ml-2 text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-500">8 BANDS</span>
                </div>
                <div class="text-[10px] text-slate-500">LOW → HIGH</div>
            </div>
            
            <div class="flex items-end justify-between gap-2 h-[210px]" id="spectrum-container">
                <!-- Populated by JS -->
            </div>
        </div>

        <!-- Bottom bar -->
        <div class="flex items-center justify-between text-xs text-slate-400 px-1">
            <div>
                Effect: <span id="effect-name" class="font-mono text-white">—</span>
            </div>
            <div class="flex gap-6">
                <div>Frames: <span id="stat-frames" class="font-mono text-white">0</span></div>
                <div>Updates: <span id="stat-updates" class="font-mono text-white">0</span></div>
            </div>
            <div id="light-count">0 lights connected</div>
        </div>

    </div>

    <script>
        let lastBeat = false;

        function updateUI(data) {
            // Loudness
            const l = data.loudness || 0;
            document.getElementById('loudness-val').innerText = l.toFixed(2);
            document.getElementById('loudness-bar').style.width = (l * 100) + '%';

            // Beat
            const beat = !!data.beat;
            const beatBox = document.getElementById('beat-box');
            const beatVal = document.getElementById('beat-val');
            
            if (beat && !lastBeat) {
                beatBox.classList.add('beat-flash', '!bg-red-500', '!text-white');
                beatBox.innerText = 'BEAT!';
                beatVal.innerText = 'YES';
                setTimeout(() => {
                    beatBox.classList.remove('beat-flash', '!bg-red-500', '!text-white');
                    beatBox.innerText = 'LISTENING';
                }, 160);
            } else if (!beat) {
                beatVal.innerText = '—';
            }
            lastBeat = beat;

            // Peak
            const p = data.peak || 0;
            document.getElementById('peak-val').innerText = p.toFixed(2);
            document.getElementById('peak-bar').style.width = (p * 100) + '%';

            // Spectrum
            const spec = data.spectrum || [0,0,0,0,0,0,0,0];
            const container = document.getElementById('spectrum-container');
            container.innerHTML = '';
            
            spec.forEach(val => {
                const bar = document.createElement('div');
                bar.className = 'flex-1 bg-gradient-to-t from-cyan-400 to-blue-500 rounded-t bar min-h-[3px]';
                bar.style.height = Math.max(3, (val || 0) * 100) + '%';
                container.appendChild(bar);
            });

            // Effect
            document.getElementById('effect-name').innerText = data.effect || '—';

            // Stats
            const st = data.stats || {};
            document.getElementById('stat-frames').innerText = st.frames || 0;
            document.getElementById('stat-updates').innerText = st.updates_sent || 0;

            // Lights
            document.getElementById('light-count').innerText = (data.lights || []).length + ' lights';

            // Connection
            const conn = document.getElementById('conn-status');
            if (data.connected) {
                conn.className = 'text-xs px-3 py-1.5 rounded-full font-medium flex items-center gap-2 bg-emerald-500/10 text-emerald-400 border border-emerald-500/30';
                conn.innerHTML = `<div class="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse"></div> CONNECTED`;
            } else {
                conn.className = 'text-xs px-3 py-1.5 rounded-full font-medium flex items-center gap-2 bg-red-500/10 text-red-400 border border-red-500/30';
                conn.innerHTML = `<div class="w-1.5 h-1.5 bg-red-400 rounded-full animate-pulse"></div> DISCONNECTED`;
            }
        }

        async function poll() {
            try {
                const r = await fetch('/status');
                if (r.ok) {
                    const d = await r.json();
                    updateUI(d);
                }
            } catch (_) {}
        }

        function init() {
            // Create 8 empty bars initially
            const c = document.getElementById('spectrum-container');
            for (let i = 0; i < 8; i++) {
                const b = document.createElement('div');
                b.className = 'flex-1 bg-slate-700 rounded-t bar min-h-[3px]';
                b.style.height = '3px';
                c.appendChild(b);
            }
            poll();
            setInterval(poll, 220);
        }

        window.onload = init;
    </script>
</body>
</html>"""
    return HTMLResponse(html)


def create_ui(app_context=None):
    """Start the simple web UI server (call this from main.py)."""
    routes = [
        Route("/", index),
        Route("/status", status_endpoint),
    ]

    app = Starlette(routes=routes)

    import uvicorn
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8099,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)

    import threading
    t = threading.Thread(target=server.run, daemon=True)
    t.start()

    logger.info("Simple web UI ready on port 8099 (Ingress compatible)")
    return server
