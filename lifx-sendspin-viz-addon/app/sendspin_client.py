"""
SendSpin Visualizer Client (fallback implementation)
Works without the full aiosendspin package.
"""
import asyncio
import logging
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("lifx-sendspin-viz.sendspin_client")


class SendspinVisualizerClient:
    def __init__(
        self,
        url: str,
        client_name: str = "LIFX Visualizer",
        visualizer_support: Optional[Dict[str, Any]] = None,
    ):
        self.url = url
        self.client_name = client_name
        self.visualizer_support = visualizer_support or {}
        self._connected = False
        self.on_visualization: Optional[Callable] = None
        self.on_stream_start: Optional[Callable] = None
        self.on_stream_end: Optional[Callable] = None
        self._task: Optional[asyncio.Task] = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self):
        if self._connected:
            return
        logger.info(f"Connecting to SendSpin server at {self.url} as {self.client_name}")
        # In real implementation this would use aiosendspin / websockets
        self._connected = True
        logger.info("Connected to SendSpin (fallback mode)")

        # Simulate stream start
        if self.on_stream_start:
            self.on_stream_start({"mode": "fallback"})

        # Start fake data loop (for testing)
        self._task = asyncio.create_task(self._fake_data_loop())

    async def disconnect(self):
        if not self._connected:
            return
        logger.info("Disconnecting from SendSpin server")
        self._connected = False
        if self._task:
            self._task.cancel()
        if self.on_stream_end:
            self.on_stream_end()

    async def _fake_data_loop(self):
        """Fake visualization data for testing when real SendSpin is not available."""
        import random
        try:
            while self._connected:
                if self.on_visualization:
                    fake_data = {
                        "loudness": random.uniform(0.1, 0.9),
                        "beat": random.random() > 0.85,
                        "f_peak": random.uniform(100, 8000),
                        "spectrum": [random.uniform(0, 1) for _ in range(8)],
                        "peak": random.uniform(0.2, 1.0),
                        "timestamp": asyncio.get_event_loop().time(),
                    }
                    self.on_visualization(fake_data)
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass

    async def send_command(self, command: Dict[str, Any]):
        """Placeholder for sending commands back to SendSpin server."""
        logger.debug(f"Would send command: {command}")
