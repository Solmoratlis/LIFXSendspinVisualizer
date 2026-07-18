import asyncio
import logging
from photons import LanTarget
from photons_messages import LightMessages
from typing import List, Dict

logger = logging.getLogger(__name__)

class LIFXController:
    def __init__(self, config):
        self.config = config
        self.target = LanTarget()
        self.sender = None
        self.beam_refs: List = []
        self.downlight_refs: List = []

    async def start(self):
        self.sender = await self.target.session().__aenter__()
        logger.info("LIFX controller started (discovery can be added later)")

    async def apply_commands(self, commands: dict):

    async def stop(self):
        if self.sender:
            await self.sender.__aexit__(None, None, None)
