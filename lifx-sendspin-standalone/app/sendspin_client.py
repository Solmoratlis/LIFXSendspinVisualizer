"""
SendSpin Visualizer Client
Attempts a real connection to Music Assistant's SendSpin server.
Falls back to a high-quality simulated data stream if the real connection fails.
"""
import asyncio
import json
import logging
import random
import struct
import time
from typing import Any, Callable, Dict, Optional

import websockets

logger = logging.getLogger("lifx-sendspin.sendspin_client")


class SendspinVisualizerClient:
    def __init__(
        self,
        url: str,
        client_name: str = "LIFX Visualizer",
        psk: Optional[str] = None,
    ):
        self.url = url
        self.client_name = client_name
        self.psk = psk.encode() if isinstance(psk, str) else psk

        self._ws = None
        self._connected = False
        self._recv_task: Optional[asyncio.Task] = None
        self._fake_task: Optional[asyncio.Task] = None
        self._use_fallback = False

        self.on_visualization: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_stream_start: Optional[Callable[[Dict], None]] = None
        self.on_stream_end: Optional[Callable[[], None]] = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self):
        if self._connected:
            return

        logger.info(f"Connecting to SendSpin at {self.url} as '{self.client_name}'")

        try:
            self._ws = await asyncio.wait_for(
                websockets.connect(self.url, max_size=2**20, open_timeout=8),
                timeout=10,
            )
            # For now we treat a successful WebSocket open as connected.
            # Full Noise KKpsk2 can be added once the correct PSK / prologue is known.
            self._connected = True
            self._use_fallback = False
            logger.info("WebSocket connected to SendSpin server")

            if self.on_stream_start:
                self.on_stream_start({"mode": "websocket", "client": self.client_name})

            self._recv_task = asyncio.create_task(self._recv_loop())

        except Exception as e:
            logger.warning(f"Real SendSpin connection failed ({e}) — using high-quality fallback data")
            self._connected = True
            self._use_fallback = True
            if self.on_stream_start:
                self.on_stream_start({"mode": "fallback", "client": self.client_name})
            self._fake_task = asyncio.create_task(self._fallback_loop())

    async def _recv_loop(self):
        try:
            while self._connected and self._ws:
                raw = await self._ws.recv()
                if isinstance(raw, str):
                    try:
                        msg = json.loads(raw)
                        logger.debug(f"Control message: {msg}")
                    except Exception:
                        pass
                    continue

                parsed = self._parse_binary(raw)
                if parsed and self.on_visualization:
                    self.on_visualization(parsed)

        except websockets.ConnectionClosed:
            logger.warning("SendSpin WebSocket closed")
        except Exception as e:
            logger.error(f"Receive loop error: {e}")
        finally:
            self._connected = False
            if self.on_stream_end:
                self.on_stream_end()

    def _parse_binary(self, data: bytes) -> Optional[Dict[str, Any]]:
        """Basic parser for common SendSpin visualization message types."""
        if len(data) < 1:
            return None

        msg_type = data[0]
        payload = data[1:]

        try:
            if msg_type == 16 and len(payload) >= 4:  # loudness
                loudness = struct.unpack("<f", payload[:4])[0]
                return {"loudness": max(0.0, min(1.0, loudness)), "timestamp": time.time()}

            if msg_type == 17 and len(payload) >= 1:  # beat
                return {"beat": bool(payload[0]), "timestamp": time.time()}

            if msg_type == 18 and len(payload) >= 4:  # f_peak + spectrum
                f_peak = struct.unpack("<f", payload[:4])[0]
                spectrum = []
                for i in range(4, len(payload), 4):
                    if i + 4 <= len(payload):
                        spectrum.append(max(0.0, min(1.0, struct.unpack("<f", payload[i:i+4])[0])))
                return {
                    "f_peak": f_peak,
                    "spectrum": spectrum or [0.0] * 8,
                    "timestamp": time.time(),
                }

            if msg_type == 19 and len(payload) >= 4:  # peak
                peak = struct.unpack("<f", payload[:4])[0]
                return {"peak": max(0.0, min(1.0, peak)), "timestamp": time.time()}

        except Exception as e:
            logger.debug(f"Parse error: {e}")

        return None

    async def _fallback_loop(self):
        """High-quality simulated visualization data when real connection is unavailable."""
        t0 = time.time()
        phase = 0.0
        try:
            while self._connected and self._use_fallback:
                t = time.time() - t0
                phase += 0.12

                # Simulated music energy with some variation
                base = 0.35 + 0.25 * abs(__import__("math").sin(t * 1.7))
                energy = max(0.05, min(0.95, base + random.uniform(-0.08, 0.12)))

                beat = random.random() < (0.12 + energy * 0.18)

                # 8-band spectrum with some musical shape
                spectrum = []
                for i in range(8):
                    band = energy * (0.4 + 0.6 * abs(__import__("math").sin(phase + i * 0.7)))
                    band += random.uniform(-0.05, 0.08)
                    spectrum.append(max(0.0, min(1.0, band)))

                data = {
                    "loudness": energy,
                    "beat": beat,
                    "peak": min(1.0, energy * 1.15 + random.uniform(0, 0.1)),
                    "spectrum": spectrum,
                    "f_peak": 80 + energy * 4000 + random.uniform(-200, 400),
                    "timestamp": time.time(),
                }

                if self.on_visualization:
                    self.on_visualization(data)

                await asyncio.sleep(0.08)  # ~12.5 Hz
        except asyncio.CancelledError:
            pass

    async def disconnect(self):
        if not self._connected:
            return
        logger.info("Disconnecting from SendSpin")
        self._connected = False
        self._use_fallback = False

        if self._recv_task:
            self._recv_task.cancel()
        if self._fake_task:
            self._fake_task.cancel()
        if self._ws:
            await self._ws.close()

        if self.on_stream_end:
            self.on_stream_end()