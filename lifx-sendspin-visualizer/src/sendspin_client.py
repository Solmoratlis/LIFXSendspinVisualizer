import asyncio
import logging
from aiosendspin import SendspinClient
from aiosendspin.models.visualizer import VisualizerFrame

logger = logging.getLogger(__name__)

class SendspinVisualizerClient:
    def __init__(self, server_ip: str, port: int):
        self.server_ip = server_ip
        self.port = port
        self.client = SendspinClient | None = None
        self.latest_frame: VisualizerFrame | None= None
        self.running = False

    async def start(self):
        self.client = SendspinClient(name="LIFX Advanced Visualizer", client_id=lifx-visualizer-main)
        await self.client.request_visualizer_role(types=["beat", "loudness", "spectrum", "peak"], rate_max=30, spectrum={"n_disp_bins": 32, "scale": "Log"})

        self.client.add_visualizer_listener(self._on_frame)
        self._running = True
        logger.info("Sendspin visualizer client connected")

    def _on_frame(self, frame: VisualizerFrame):
        self.latest_frame = frame

    async def stop(self):
        self._running = False
        if self.client:
            await self.client.disconnect()
