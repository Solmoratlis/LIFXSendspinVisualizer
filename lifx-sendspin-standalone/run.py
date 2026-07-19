#!/usr/bin/env python3
"""
Entry point for the standalone LIFX SendSpin Visualizer.
"""
import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

# Make sure app package is importable
sys.path.insert(0, str(Path(__file__).parent))

from app.main import LifxSendspinApp


def load_config() -> dict:
    """Load configuration from YAML + environment variables."""
    config_path = os.getenv("CONFIG_PATH", "config.yaml")
    example_path = "config.example.yaml"

    data = {}
    if os.path.exists(config_path):
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
    elif os.path.exists(example_path):
        with open(example_path) as f:
            data = yaml.safe_load(f) or {}

    # Environment overrides
    sendspin = data.setdefault("sendspin", {})
    sendspin["url"] = os.getenv("SENDSPIN_URL", sendspin.get("url", "ws://homeassistant.local:8927/sendspin"))
    sendspin["client_name"] = os.getenv("CLIENT_NAME", sendspin.get("client_name", "LIFX Visualizer"))

    viz = data.setdefault("visualization", {})
    viz["effect"] = os.getenv("EFFECT", viz.get("effect", "energy_pulse"))
    viz["sensitivity"] = float(os.getenv("SENSITIVITY", viz.get("sensitivity", 1.0)))
    viz["enabled"] = os.getenv("ENABLED", str(viz.get("enabled", True))).lower() in ("true", "1", "yes")

    return data


async def main():
    config = load_config()

    logging.basicConfig(
        level=getattr(logging, config.get("logging", {}).get("level", "INFO")),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger("lifx-sendspin")

    logger.info("Starting LIFX SendSpin Visualizer (standalone)")
    logger.info(f"SendSpin URL: {config['sendspin']['url']}")
    logger.info(f"Effect: {config['visualization']['effect']}")

    app = LifxSendspinApp(config)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(app.shutdown()))

    await app.run()


if __name__ == "__main__":
    asyncio.run(main())