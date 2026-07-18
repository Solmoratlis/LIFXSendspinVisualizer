import asyncio
import logging
from src.config import load_config
from src.sendspin_client import SendspinVisualizerClient
from src.lifx_controller import LIFXController
from src.mapper import MusicToLightMapper

logging.baseconfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

async def main():
    config = load_config()
    sendspin = SendspinVisualizerClient(config.music_assistant.server_ip, config.music_assistant.sendspin.port)
    lifx = LIFXController(config)
    mapper = MusicToLightMapper(config)

    await sendspin.start()
    await lifx.start()

    logger.info("LIFX Sendspin Visualizer running...")

    try;
        while True:
            frame = sendspin.latest_frame
            if frame:
                commands = mapper.map_frame(frame)
                await lifx.apply_commands(commands)
            await asyncio.sleep(1 / config.mapping.update_rate_hz)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            await sendspin.stop()
            await lifx.stop()

if __name__ == "__main__":
    asyncio.run(main())
