import json
import logging

import aiomqtt

from app.db.mongo import insert_error_log, insert_sensor_status_log, insert_server_status_log
from app.models.schemas import CtrlServerResultPayload, EdgeSensorRegisterRequest, EdgeServerRegisterRequest
from app.mqtt.publish import publish_register_sensor, publish_register_server
from app.mqtt.topics import (
    SUBSCRIBE_FORWARD_SENSOR_INIT,
    SUBSCRIBE_REQUEST_UPLOAD_AUDIO,
    SUBSCRIBE_RESULT_PARAMETERS_SENSOR,
    SUBSCRIBE_RESULT_PARAMETERS_SERVER,
    SUBSCRIBE_SERVER_INIT,
    SUBSCRIBE_UPLOAD_RESULT,
)
from app.services.registration import register_edge_sensor, register_edge_server
from app.utils.retry import async_retry

logger = logging.getLogger(__name__)


# ─── 라우터 ───────────────────────────────────────────────────────────────────

async def dispatch(message: aiomqtt.Message) -> None:
    topic = str(message.topic)
    parts = topic.split("/")  # ["signalcraft", "{action}", "{server_id}", "cloud"]

    if len(parts) != 4 or parts[0] != "signalcraft" or parts[-1] != "cloud":
        logger.warning("[MQTT] Unexpected topic format: %s", topic)
        return

    try:
        payload = json.loads(message.payload)
    except (json.JSONDecodeError, ValueError):
        logger.warning("[MQTT] Non-JSON payload on topic %s", topic)
        return

    match parts[1]:
        case "server_init":               await handle_server_init(topic, payload)
        case "forward_sensor_init":       await handle_sensor_init(topic, payload)
        case "request_upload_audio":      await handle_audio_upload_request(topic, payload)
        case "upload_result":             await handle_upload_result(topic, payload)
        case "result_parameters_server":  await handle_result_parameters_server(topic, payload)
        case "result_parameters_sensor":  await handle_result_parameters_sensor(topic, payload)
        case _:                           logger.warning("[MQTT] Unhandled topic: %s", topic)


# ─── 핸들러 ───────────────────────────────────────────────────────────────────
async def handle_server_init(topic: str, payload: dict) -> None:
    """NEW-001 | signalcraft/server_init/{server_id}/cloud"""
    server_id_str = topic.split("/")[2]

    try:
        req = EdgeServerRegisterRequest(**payload)
    except Exception as exc:
        logger.error("[MQTT] Invalid server_init payload: %s", exc)
        return

    try:
        server = await async_retry(
            lambda: register_edge_server(server_id_str, req.timezone, req.installation_machine),
            max_attempts=3,
        )
        await insert_server_status_log(
            server_id=server_id_str,
            server_status=server.server_status.value,
        )
    except Exception as exc:
        await insert_error_log(
            event="server_registration",
            server_id=server_id_str,
            error=str(exc),
            attempts=3,
        )
        logger.error("[MQTT] Server registration failed: %s | %s", server_id_str, exc)
        return

    try:
        await publish_register_server(server_id_str, {"status": "success"})
        logger.info("[MQTT] Server registered: %s", server_id_str)
    except Exception as exc:
        logger.warning("[MQTT] Registration OK but publish failed for %s: %s", server_id_str, exc)


async def handle_sensor_init(topic: str, payload: dict) -> None:
    """NEW-004 | signalcraft/forward_sensor_init/{server_id}/cloud"""
    server_id_str = topic.split("/")[2]

    try:
        req = EdgeSensorRegisterRequest(**payload)
    except Exception as exc:
        logger.error("[MQTT] Invalid sensor_init payload: %s", exc)
        return

    try:
        sensor = await async_retry(
            lambda: register_edge_sensor(
                server_id_str,
                req.device_name,
                req.sensor_type,
                req.sensor_position,
                req.installation_machine,
            ),
            max_attempts=3,
        )
        await insert_sensor_status_log(
            server_id=server_id_str,
            device_name=sensor.device_name,
            sensor_type=sensor.sensor_type.value if sensor.sensor_type else None,
            sensor_position=sensor.sensor_position,
            installation_machine=sensor.installation_machine,
        )
    except Exception as exc:
        await insert_error_log(
            event="sensor_registration",
            server_id=server_id_str,
            error=str(exc),
            attempts=3,
        )
        logger.error("[MQTT] Sensor registration failed: %s | %s", server_id_str, exc)
        return

    try:
        await publish_register_sensor(
            server_id_str,
            {"status": "success", "device_name": sensor.device_name},
        )
        logger.info("[MQTT] Sensor registered: %s / %s", server_id_str, sensor.device_name)
    except Exception as exc:
        logger.warning("[MQTT] Sensor registration OK but publish failed for %s: %s", server_id_str, exc)


async def handle_audio_upload_request(topic: str, payload: dict) -> None:
    """AUDIO-005 | signalcraft/request_upload_audio/{server_id}/cloud"""
    pass


async def handle_upload_result(topic: str, payload: dict) -> None:
    """AUDIO-010 | signalcraft/upload_result/{server_id}/cloud"""
    pass


async def handle_result_parameters_server(topic: str, payload: dict) -> None:
    """CTRL-SERVER-002 | signalcraft/result_parameters_server/{server_id}/cloud"""
    server_id_str = topic.split("/")[2]

    try:
        result = CtrlServerResultPayload(**payload)
    except Exception as exc:
        logger.error("[MQTT] Invalid result_parameters_server payload: %s", exc)
        return

    if result.status == "failed":
        await insert_error_log(
            event="ctrl_server_result",
            server_id=server_id_str,
            error=result.message or "No message provided",
            attempts=1,
        )
        logger.warning("[MQTT] Ctrl result failed: %s | %s", server_id_str, result.message)
    else:
        logger.info("[MQTT] Ctrl result success: %s", server_id_str)


async def handle_result_parameters_sensor(topic: str, payload: dict) -> None:
    """CTRL-SENSOR-004 | signalcraft/result_parameters_sensor/{server_id}/cloud"""
    pass
