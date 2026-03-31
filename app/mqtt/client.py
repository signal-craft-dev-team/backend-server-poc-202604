import os

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()

BROKER_HOST = os.getenv("MQTT_HOST", "localhost")
BROKER_PORT = 1883
MQTT_USER = os.getenv("MQTT_USER")
MQTT_PWD = os.getenv("MQTT_PWD")
CLIENT_ID = "signal-craft-backend"


def create_client() -> mqtt.Client:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=CLIENT_ID)
    if MQTT_USER and MQTT_PWD:
        client.username_pw_set(MQTT_USER, MQTT_PWD)
    return client


def connect(client: mqtt.Client) -> None:
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
