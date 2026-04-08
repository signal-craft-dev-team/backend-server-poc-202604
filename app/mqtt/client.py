import logging
import os
import uuid

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

BROKER_HOST = os.getenv("MQTT_HOST", "localhost")
BROKER_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USER")
MQTT_PWD = os.getenv("MQTT_PWD")
# 고정 ID를 쓰면 재시작 시 브로커가 이전 세션을 끊으면서 무한 disconnect 루프 발생.
# MQTT_CLIENT_ID 환경변수로 고정하거나, 기본값으로 매 시작마다 유니크한 ID 사용.
CLIENT_ID = os.getenv("MQTT_CLIENT_ID", f"signal-craft-backend-{uuid.uuid4().hex[:8]}")

# paho v2 연결 결과 코드
_RC_MESSAGES = {
    0: "Connection accepted",
    1: "Refused — incorrect protocol version",
    2: "Refused — invalid client identifier",
    3: "Refused — server unavailable",
    4: "Refused — bad username or password",
    5: "Refused — not authorised",
}


def _on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        logger.info(f"[MQTT] connected to {BROKER_HOST}:{BROKER_PORT}")
    else:
        msg = _RC_MESSAGES.get(int(reason_code), f"unknown code {reason_code}")
        logger.error(f"[MQTT] connection failed — {msg} (code={reason_code})")


def _on_disconnect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        logger.info("[MQTT] disconnected cleanly")
    else:
        logger.warning(f"[MQTT] unexpected disconnect (code={reason_code})")


def create_client() -> mqtt.Client:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=CLIENT_ID)
    if MQTT_USER and MQTT_PWD:
        client.username_pw_set(MQTT_USER, MQTT_PWD)
    client.on_connect = _on_connect
    client.on_disconnect = _on_disconnect
    return client


def connect(client: mqtt.Client) -> None:
    logger.info(f"[MQTT] connecting to {BROKER_HOST}:{BROKER_PORT} ...")
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
