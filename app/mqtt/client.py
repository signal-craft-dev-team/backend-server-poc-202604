import os
import paho.mqtt.client as mqtt

BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))
CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "signal-craft-backend")


def create_client() -> mqtt.Client:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=CLIENT_ID)
    return client


def connect(client: mqtt.Client) -> None:
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
