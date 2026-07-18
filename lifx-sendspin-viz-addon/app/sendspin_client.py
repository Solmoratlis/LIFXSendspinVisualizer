"""
SendSpin Visualizer Client wrapper.
Uses aiosendspin library under the hood for full protocol support (Noise, roles, binary viz messages).
This file provides a clean async interface + callbacks for the visualizer role.
"""

import asyncio
import logging
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

try:
    import aiosendspin
    AIOSENDSPIN_AVAILABLE = True
except ImportError:
    AIOSENDSPIN_AVAILABLE = False
    logger.warning("aiosendspin not installed — running in MOCK mode for development")


class SendspinVisualizerClient:
    """
    High-level async client for SendSpin visualizer role.
    In production this wraps aiosendspin.Client or VisualizerRole.
    """

    def __init__(self, url: str, client_name: str, visualizer_support: Dict[str, Any]):
        self.url = url
        self.client_name = client_name
        self.visualizer_support = visualizer_support
        self.on_visualization: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_stream_start: Optional[Callable[[Dict], None]] = None
        self.on_stream_end: Optional[Callable[[], None]] = None
        self._connected = False
        self._task: Optional[asyncio.Task] = None
        self._client: Any = None  # Will be aiosendspin client instance

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self):
        if not AIOSENDSPIN_AVAILABLE:
            logger.info("MOCK MODE: Simulating SendSpin connection and sending fake viz data for testing.")
            self._connected = True
            self._task = asyncio.create_task(self._mock_visualizer_loop())
            return

        # === REAL IMPLEMENTATION WITH aiosendspin ===
        # Example expected usage (adjust to actual aiosendspin API when integrating):
        #
        # from aiosendspin import SendspinClient, Roles, VisualizerSupport
        #
        # self._client = SendspinClient(
        #     client_id=..., name=self.client_name, url=self.url
        # )
        # await self._client.connect()
        #
        # support = VisualizerSupport(
        #     types=self.visualizer_support["types"],
        #     buffer_capacity=self.visualizer_support["buffer_capacity"],
        #     rate_max=self.visualizer_support.get("rate_max", 12),
        #     spectrum=self.visualizer_support.get("spectrum"),
        # )
        #
        # await self._client.hello(roles=["visualizer@v1"], visualizer_v1_support=support)
        #
        # # Register binary message handler or use high-level visualizer stream
        # self._client.on_binary_message = self._handle_binary_viz
        # self._client.on_stream_start = lambda info: self.on_stream_start and self.on_stream_start(info)
        #
        # self._connected = True
        # logger.info("Connected to SendSpin and activated visualizer role")

        logger.warning("Real aiosendspin integration not yet wired in this skeleton. "
                       "See comments in sendspin_client.py for how to complete it using the official library.")
        self._connected = True  # Pretend for now

    async def _mock_visualizer_loop(self):
        """Development helper: generate plausible viz data so you can test LIFX effects without a full MA setup."""
        import random
        import math
        t = 0
        while self._connected:
            t += 0.08
            loudness = 0.4 + 0.5 * math.sin(t * 1.3)   # normalized-ish
            beat = 1 if random.random() < 0.12 else 0
            spectrum = [max(0, int(30000 * (0.6 + 0.4*math.sin(t* (i+1)*0.7) + random.random()*0.2))) for i in range(self.visualizer_support.get("spectrum", {}).get("n_disp_bins", 8))]
            f_peak = (80 + int(8000 * abs(math.sin(t*0.4))), 45000)

            data = {
                "type": "visualization",
                "timestamp_us": int(time.time() * 1_000_000),
                "loudness": int(loudness * 65535),
                "beat": {"flags": beat},
                "f_peak": {"freq": f_peak[0], "amp": f_peak[1]},
                "spectrum": spectrum,
                "peak": int(200 * random.random()),
            }
            if self.on_visualization:
                self.on_visualization(data)
            await asyncio.sleep(1.0 / max(5, self.visualizer_support.get("rate_max", 12)))

    async def disconnect(self):
        self._connected = False
        if self._task:
            self._task.cancel()
        if self._client:
            # await self._client.disconnect() or close
            pass
        logger.info("Disconnected from SendSpin")

    def _handle_binary_viz(self, msg_type: int, timestamp: int, payload: bytes):
        """Parse binary visualization messages per SendSpin spec (types 16-20)."""
        # This would be called by aiosendspin when binary frames arrive.
        # Implement parsing here or let the library give you already parsed dicts.
        data: Dict[str, Any] = {"timestamp_us": timestamp}

        if msg_type == 16:  # loudness
            data["loudness"] = int.from_bytes(payload[:2], "big")
        elif msg_type == 17:  # beat
            data["beat"] = {"flags": payload[0]}
        elif msg_type == 18:  # f_peak
            data["f_peak"] = {
                "freq": int.from_bytes(payload[:2], "big"),
                "amp": int.from_bytes(payload[2:4], "big"),
            }
        elif msg_type == 19:  # spectrum
            n = len(payload) // 2
            data["spectrum"] = [int.from_bytes(payload[i*2:i*2+2], "big") for i in range(n)]
        elif msg_type == 20:  # peak
            data["peak"] = payload[0]

        if self.on_visualization and data:
            self.on_visualization(data)