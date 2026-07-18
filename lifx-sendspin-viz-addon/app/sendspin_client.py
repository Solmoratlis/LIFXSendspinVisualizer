"""
Full aiosendspin integration for visualizer role.
Production-grade implementation.
"""

import asyncio
import logging
import time
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

try:
    import aiosendspin
    from aiosendspin import SendspinClient, Roles, VisualizerSupport
    AIOSENDSPIN_AVAILABLE = True
except ImportError as e:
    AIOSENDSPIN_AVAILABLE = False
    logger.error(f"aiosendspin not available: {e}")


class SendspinVisualizerClient:
    """Production SendSpin visualizer client using aiosendspin."""

    def __init__(self, url: str, client_name: str, visualizer_support: Dict[str, Any]):
        self.url = url
        self.client_name = client_name
        self.visualizer_support = visualizer_support
        self.on_visualization: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_stream_start: Optional[Callable[[Dict], None]] = None
        self.on_stream_end: Optional[Callable[[], None]] = None

        self._client: Optional[Any] = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> bool:
        if not AIOSENDSPIN_AVAILABLE:
            logger.error("aiosendspin library not installed")
            return False

        try:
            self._client = SendspinClient(
                name=self.client_name,
                client_id=f"lifx-viz-{int(time.time())}",
            )

            await self._client.connect(self.url)

            support = VisualizerSupport(
                types=self.visualizer_support.get("types", ["loudness", "beat", "f_peak", "spectrum", "peak"]),
                buffer_capacity=self.visualizer_support.get("buffer_capacity", 65536),
                rate_max=self.visualizer_support.get("rate_max", 12),
                spectrum=self.visualizer_support.get("spectrum"),
            )

            await self._client.hello(
                roles=[Roles.VISUALIZER],
                visualizer_v1_support=support
            )

            # Wire handlers
            self._client.on_binary_message = self._handle_binary_message
            self._client.on_stream_start = self._handle_stream_start
            self._client.on_stream_end = self._handle_stream_end

            self._connected = True
            logger.info(f"✓ Connected to SendSpin as visualizer: {self.client_name}")
            return True

        except Exception as e:
            logger.error(f"SendSpin connection failed: {e}")
            self._connected = False
            return False

    def _handle_binary_message(self, msg_type: int, timestamp_us: int, payload: bytes):
        data: Dict[str, Any] = {"timestamp_us": timestamp_us, "raw_type": msg_type}

        try:
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
                data["spectrum"] = [int.from_bytes(payload[i*2:(i+1)*2], "big") for i in range(n)]
            elif msg_type == 20:  # peak
                data["peak"] = payload[0]

            if self.on_visualization:
                self.on_visualization(data)

        except Exception as e:
            logger.debug(f"Binary parse error (type {msg_type}): {e}")

    def _handle_stream_start(self, info: Dict):
        logger.info(f"Stream started: {info}")
        if self.on_stream_start:
            self.on_stream_start(info)

    def _handle_stream_end(self):
        logger.info("Stream ended")
        if self.on_stream_end:
            self.on_stream_end()

    async def disconnect(self):
        self._connected = False
        if self._client:
            try:
                await self._client.disconnect()
            except Exception:
                pass
        logger.info("Disconnected from SendSpin")