"""
MQTT + Home Assistant auto-discovery helper.
Creates switch + sensors automatically in HA when MQTT is configured.
"""

import json
import logging
from typing import Any, Dict, Optional

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class MQTTClient:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.mqtt_host = config.get("mqtt_host", "homeassistant.local")
        self.mqtt_port = config.get("mqtt_port", 1883)
        self.mqtt_user = config.get("mqtt_user")
        self.mqtt_pass = config.get("mqtt_pass")
        self.discovery_prefix = config.get("mqtt_discovery_prefix", "homeassistant")
        self.base_topic = config.get("mqtt_base_topic", "lifx_viz")

        self.client: Optional[mqtt.Client] = None
        self.connected = False

    def connect(self):
        if not self.mqtt_host:
            logger.info("No MQTT host configured — skipping MQTT integration")
            return False

        try:
            self.client = mqtt.Client(client_id="lifx-sendspin-viz")
            if self.mqtt_user:
                self.client.username_pw_set(self.mqtt_user, self.mqtt_pass)

            self.client.on_connect = self._on_connect
            self.client.connect(self.mqtt_host, self.mqtt_port, 60)
            self.client.loop_start()
            return True
        except Exception as e:
            logger.warning(f"MQTT connection failed: {e}")
            return False

    def _on_connect(self, client, userdata, flags, rc):
        self.connected = True
        logger.info("Connected to MQTT broker")
        self._publish_discovery()

    def _publish_discovery(self):
        """Publish Home Assistant MQTT discovery payloads."""
        device = {
            "identifiers": ["lifx_sendspin_viz"],
            "name": "LIFX SendSpin Music Visualizer",
            "manufacturer": "Open Home + Custom",
            "model": "SendSpin Visualizer Add-on",
        }

        # Switch for enabling viz
        switch_config = {
            "name": "LIFX Music Viz Enabled",
            "unique_id": "lifx_viz_enabled",
            "state_topic": f"{self.base_topic}/enabled/state",
            "command_topic": f"{self.base_topic}/enabled/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "device": device,
        }
        self._publish(f"{self.discovery_prefix}/switch/lifx_viz_enabled/config", switch_config)

        # Sensor: Loudness
        loudness_config = {
            "name": "LIFX Viz Loudness",
            "unique_id": "lifx_viz_loudness",
            "state_topic": f"{self.base_topic}/loudness/state",
            "unit_of_measurement": "%",
            "device": device,
        }
        self._publish(f"{self.discovery_prefix}/sensor/lifx_viz_loudness/config", loudness_config)

        # Sensor: Beat
        beat_config = {
            "name": "LIFX Viz Beat",
            "unique_id": "lifx_viz_beat",
            "state_topic": f"{self.base_topic}/beat/state",
            "device": device,
        }
        self._publish(f"{self.discovery_prefix}/sensor/lifx_viz_beat/config", beat_config)

    def _publish(self, topic: str, payload: Any):
        if self.client and self.connected:
            try:
                self.client.publish(topic, json.dumps(payload), retain=True)
            except Exception as e:
                logger.debug(f"MQTT publish error: {e}")

    def publish_state(self, topic: str, value: Any):
        if self.client and self.connected:
            try:
                self.client.publish(f"{self.base_topic}/{topic}/state", str(value))
            except Exception:
                pass

    def disconnect(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()