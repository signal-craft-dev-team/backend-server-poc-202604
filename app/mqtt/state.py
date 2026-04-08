"""Holds the shared MQTT client instance to avoid circular imports."""
from typing import Optional

import paho.mqtt.client as mqtt

_client: Optional[mqtt.Client] = None


def set_client(client: mqtt.Client) -> None:
    global _client
    _client = client


def get_client() -> Optional[mqtt.Client]:
    return _client
