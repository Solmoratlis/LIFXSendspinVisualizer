"""
Simple, reliable web UI for the standalone visualizer.
"""
import logging
from typing import Any, Dict

from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

logger = logging.getLogger("lifx-sendspin.web_ui")

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
    viz_state["loudness"] = float(data.get("loudness", 0.0))
    viz_state["beat"] = bool(data.get("beat", False))
    viz_state["spectrum"] = data.get("spectrum", [0.0] * 8)
    viz_state["peak"] = float(data.get("peak", 0.0))
    viz_state["stats"] = stats
    viz_state["connected"] = connected


async def status(request):
    return JSONResponse(viz_state)


async def index(request):
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LIFX SendSpin Visualizer</title>
<script src="https://cdn.tailwindcss.com"></script>
<style>
  body{background:#0f172a;color:#e2e8f0}
  .bar{transition:height 80ms linear}
  .beat-flash{animation:flash 120ms ease-out}
  @keyframes flash{0%{background:#f87171;box-shadow:0 0 12px #f87171}100%{background:#334155}}
</style>
</head>
<body class="min-h-screen p-6">
<div class="max-w-4xl mx-auto">
  <div class="flex justify-between items-center mb-8">
    <div>
      <h1 class="text-3xl font-bold">LIFX SendSpin</h1>
      <p class="text-slate-400 text-sm">Music Visualizer</p>
    </div>
    <div id="status" class="px-3 py-1 rounded-full text-xs font-medium bg-red-500/20 text-red-400">DISCONNECTED</div>
  </div>

  <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
    <div class="bg-slate-800 rounded-2xl p-5">
      <div class="flex justify-between mb-2">
        <span class="text-xs text-slate-400">LOUDNESS</span>
        <span id="loud" class="text-2xl font-mono font-bold">0.00</span>
      </div>
      <div class="h-3 bg-slate-700 rounded-full overflow-hidden">
        <div id="loud-bar" class="h-3 bg-gradient-to-r from-cyan-400 to-blue-500 rounded-full" style="width:0%"></div>
      </div>
    </div>
    <div class="bg-slate-800 rounded-2xl p-5">
      <div class="flex justify-between mb-2">
        <span class="text-xs text-slate-400">BEAT</span>
        <span id="beat" class="text-2xl font-mono font-bold">—</span>
      </div>
      <div id="beat-box" class="h-3 bg-slate-700 rounded-full flex items-center justify-center text-[10px] text-slate-400">LISTENING</div>
    </div>
    <div class="bg-slate-800 rounded-2xl p-5">
      <div class="flex justify-between mb-2">
        <span class="text-xs text-slate-400">PEAK</span>
        <span id="peak" class="text-2xl font-mono font-bold">0.00</span>
      </div>
      <div class="h-3 bg-slate-700 rounded-full overflow-hidden">
        <div id="peak-bar" class="h-3 bg-gradient-to-r from-violet-400 to-fuchsia-500 rounded-full" style="width:0%"></div>
      </div>
    </div>
  </div>

  <div class="bg-slate-800 rounded-2xl p-5 mb-6">
    <div class="flex justify-between mb-3">
      <span class="text-sm font-medium">SPECTRUM</span>
      <span class="text-xs text-slate-500">8 BANDS</span>
    </div>
    <div id="spec" class="flex items-end gap-2 h-48"></div>
  </div>

  <div class="flex justify-between text-xs text-slate-400">
    <div>Effect: <span id="effect" class="text-white font-mono">—</span></div>
    <div>Frames: <span id="frames" class="text-white font-mono">0</span> · Updates: <span id="updates" class="text-white font-mono">0</span></div>
  </div>
</div>

<script>
let lastBeat=false;
function update(d){
  const l=d.loudness||0;
  document.getElementById('loud').innerText=l.toFixed(2);
  document.getElementById('loud-bar').style.width=(l*100)+'%';
  const beat=!!d.beat;
  const box=document.getElementById('beat-box');
  const bv=document.getElementById('beat');
  if(beat&&!lastBeat){
    box.classList.add('beat-flash','!bg-red-500','!text-white');
    box.innerText='BEAT!'; bv.innerText='YES';
    setTimeout(()=>{box.classList.remove('beat-flash','!bg-red-500','!text-white');box.innerText='LISTENING';},150);
  } else if(!beat) bv.innerText='—';
  lastBeat=beat;
  const p=d.peak||0;
  document.getElementById('peak').innerText=p.toFixed(2);
  document.getElementById('peak-bar').style.width=(p*100)+'%';
  const s=d.spectrum||[0,0,0,0,0,0,0,0];
  const c=document.getElementById('spec');
  c.innerHTML='';
  s.forEach(v=>{
    const b=document.createElement('div');
    b.className='flex-1 bg-gradient-to-t from-cyan-400 to-blue-500 rounded-t bar';
    b.style.height=Math.max(4,(v||0)*180)+'px';
    c.appendChild(b);
  });
  document.getElementById('effect').innerText=d.effect||'—';
  const st=d.stats||{};
  document.getElementById('frames').innerText=st.frames||0;
  document.getElementById('updates').innerText=st.updates_sent||0;
  const stEl=document.getElementById('status');
  if(d.connected){
    stEl.className='px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/20 text-emerald-400';
    stEl.innerText='CONNECTED';
  } else {
    stEl.className='px-3 py-1 rounded-full text-xs font-medium bg-red-500/20 text-red-400';
    stEl.innerText='DISCONNECTED';
  }
}
async function poll(){try{const r=await fetch('/status');if(r.ok)update(await r.json())}catch(e){}}
window.onload=()=>{poll();setInterval(poll,200)};
</script>
</body>
</html>"""
    return HTMLResponse(html)


def create_ui(host: str = "0.0.0.0", port: int = 8099):
    app = Starlette(routes=[
        Route("/", index),
        Route("/status", status),
    ])
    import uvicorn
    config = uvicorn.Config(app, host=host, port=port, log_level="warning", access_log=False)
    server = uvicorn.Server(config)
    import threading
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    logger.info(f"Web UI available at http://{host}:{port}")
    return server