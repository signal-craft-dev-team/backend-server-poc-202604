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
_ABNORMAL_RE             = re.compile(r"^signalcraft/cloud/([^/]+)/abnormal$")
_DISK_ALERT_RE           = re.compile(r"^signalcraft/cloud/([^/]+)/disk_alert$")
_UPLOAD_FAILED_RE        = re.compile(r"^signalcraft/cloud/([^/]+)/upload_failed$")


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

    # ── ABNORMAL ─────────────────────────────────────────────────────────────
    if _ABNORMAL_RE.match(topic):
        _route_abnormal(topic, payload_str)
        return

    # ── DISK_ALERT ───────────────────────────────────────────────────────────
    if _DISK_ALERT_RE.match(topic):
        _route_disk_alert(topic, payload_str)
        return

    # ── UPLOAD_FAILED ────────────────────────────────────────────────────────
    if _UPLOAD_FAILED_RE.match(topic):
        _route_upload_failed(topic, payload_str)
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


def _route_abnormal(topic: str, payload_str: str) -> None:
    from app.mqtt.schemas import AbnormalMessage
    from app.log.models import SensorCommLog
    from app.log.upload_log import write_sensor_comm_log
    try:
        payload = json.loads(payload_str)
        msg = AbnormalMessage(**payload)
        upload_manager.schedule(write_sensor_comm_log(SensorCommLog(
            server_id=msg.server_id,
            sensor_id=msg.sensor_id,
            event_type=msg.event_type,
            status="ABNORMAL",
            detail={"detail": msg.detail} if msg.detail else None,
            timestamp=msg.timestamp,
        )))
    except Exception as exc:
        logger.error(f"[MQTT] failed to handle ABNORMAL | topic={topic} error={exc}")


def _route_disk_alert(topic: str, payload_str: str) -> None:
    from app.mqtt.schemas import DiskAlertMessage
    from app.log.models import SensorCommLog
    from app.log.upload_log import write_sensor_comm_log
    try:
        payload = json.loads(payload_str)
        msg = DiskAlertMessage(**payload)
        upload_manager.schedule(write_sensor_comm_log(SensorCommLog(
            server_id=msg.server_id,
            sensor_id=None,
            event_type="DISK_ALERT",
            status="WARNING",
            detail={
                "disk_usage_percent": msg.disk_usage_percent,
                "threshold_percent": msg.threshold_percent,
            },
            timestamp=msg.timestamp,
        )))
    except Exception as exc:
        logger.error(f"[MQTT] failed to handle DISK_ALERT | topic={topic} error={exc}")


def _route_upload_failed(topic: str, payload_str: str) -> None:
    from app.mqtt.schemas import UploadFailedMessage
    from app.log.models import UploadErrorLog
    from app.log.upload_log import write_error_log
    try:
        payload = json.loads(payload_str)
        msg = UploadFailedMessage(**payload)
        upload_manager.schedule(write_error_log(UploadErrorLog(
            server_id=msg.server_id,
            file_name=msg.file_name,
            reason=f"[UPLOAD_FAILED] {msg.reason}",
        )))
    except Exception as exc:
        logger.error(f"[MQTT] failed to handle UPLOAD_FAILED | topic={topic} error={exc}")


def subscribe(client: mqtt.Client, topic: str, qos: int = 0) -> None:
    client.subscribe(topic, qos=qos)
    client.on_message = on_message
    logger.info(f"[MQTT] subscribed to {topic}")
