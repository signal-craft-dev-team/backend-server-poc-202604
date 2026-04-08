import json
import logging
import re

import paho.mqtt.client as mqtt

from app.mqtt.ack_manager import ack_manager
from app.mqtt.upload_manager import upload_manager

logger = logging.getLogger(__name__)

# ── 토픽 패턴 ─────────────────────────────────────────────────────────────────
_ACK_TOPIC_RE            = re.compile(r"^signalcraft/control_server/([^/]+)/ack$")
_UPLOAD_AUDIO_RE         = re.compile(r"^signalcraft/upload_audio/([^/]+)$")
_COMPLETE_UPLOAD_RE      = re.compile(r"^signalcraft/complete_upload/([^/]+)$")


def on_message(client: mqtt.Client, userdata, message: mqtt.MQTTMessage) -> None:
    topic = message.topic
    payload_str = message.payload.decode("utf-8")
    logger.debug(f"[MQTT] received | topic={topic}")

    # ── CONTROL_SERVER ACK ───────────────────────────────────────────────────
    if _ACK_TOPIC_RE.match(topic):
        _route_control_ack(topic, payload_str)
        return

    # ── UPLOAD_AUDIO ─────────────────────────────────────────────────────────
    if _UPLOAD_AUDIO_RE.match(topic):
        _route_upload_audio(payload_str)
        return

    # ── COMPLETE_UPLOAD ──────────────────────────────────────────────────────
    if _COMPLETE_UPLOAD_RE.match(topic):
        _route_complete_upload(topic, payload_str)
        return

    logger.info(f"[MQTT] unhandled | topic={topic} payload={payload_str}")


def _route_control_ack(topic: str, payload_str: str) -> None:
    try:
        payload = json.loads(payload_str)
        message_id = payload.get("message_id")
        if message_id:
            ack_manager.resolve(message_id, payload)
        else:
            logger.warning(f"[MQTT] CONTROL_ACK missing message_id | topic={topic}")
    except json.JSONDecodeError as exc:
        logger.error(f"[MQTT] failed to parse CONTROL_ACK | topic={topic} error={exc}")


def _route_upload_audio(payload_str: str) -> None:
    # handle_upload_audio는 asyncio 코루틴 → run_coroutine_threadsafe로 예약
    from app.services.audio_upload import handle_upload_audio  # 지연 임포트(순환 방지)
    try:
        payload = json.loads(payload_str)
        upload_manager.schedule(handle_upload_audio(payload))
    except json.JSONDecodeError as exc:
        logger.error(f"[MQTT] failed to parse UPLOAD_AUDIO | error={exc}")


def _route_complete_upload(topic: str, payload_str: str) -> None:
    try:
        payload = json.loads(payload_str)
        file_name = payload.get("file_name")
        if file_name:
            upload_manager.resolve(file_name, payload)
        else:
            logger.warning(f"[MQTT] COMPLETE_UPLOAD missing file_name | topic={topic}")
    except json.JSONDecodeError as exc:
        logger.error(f"[MQTT] failed to parse COMPLETE_UPLOAD | topic={topic} error={exc}")


def subscribe(client: mqtt.Client, topic: str, qos: int = 0) -> None:
    client.subscribe(topic, qos=qos)
    client.on_message = on_message
    logger.info(f"[MQTT] subscribed to {topic}")
