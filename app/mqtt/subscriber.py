import json
import logging
import re

import paho.mqtt.client as mqtt

from app.mqtt.ack_manager import ack_manager

logger = logging.getLogger(__name__)

# signalcraft/control_server/{server_id}/ack
_ACK_TOPIC_RE = re.compile(r"^signalcraft/control_server/([^/]+)/ack$")

def on_message(client: mqtt.Client, userdata, message: mqtt.MQTTMessage) -> None:
    topic = message.topic
    payload_str = message.payload.decode("utf-8")
    logger.debug(f"[MQTT] received | topic={topic} payload={payload_str}")

    # CONTROL_ACK 처리
    if _ACK_TOPIC_RE.match(topic):
        try:
            payload = json.loads(payload_str)
            message_id = payload.get("message_id")
            if message_id:
                ack_manager.resolve(message_id, payload)
            else:
                logger.warning(f"[MQTT] CONTROL_ACK missing message_id | topic={topic}")
        except json.JSONDecodeError as exc:
            logger.error(f"[MQTT] failed to parse CONTROL_ACK | topic={topic} error={exc}")
        return

    # 그 외 메시지 로깅
    logger.info(f"[MQTT] received | topic={topic} payload={payload_str}")


def subscribe(client: mqtt.Client, topic: str, qos: int = 0) -> None:
    client.subscribe(topic, qos=qos)
    client.on_message = on_message
    logger.info(f"[MQTT] subscribed to {topic}")
