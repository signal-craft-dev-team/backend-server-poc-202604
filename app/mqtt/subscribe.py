import json
import logging

import aiomqtt

from app.db.mongo import insert_edge_alert_log, insert_error_log, insert_sensor_status_log
from app.models.schemas import AudioUploadResult, CtrlServerResultPayload, EdgeAlertPayload, EdgeSensorRegisterRequest, EdgeServerRegisterRequest, EdgeServerStatus
from app.mqtt.publish import publish_register_sensor, publish_register_server, publish_upload_audio_url
from app.services.audio import check_upload_anomaly, issue_presigned_url, record_upload_result
from app.services.registration import register_edge_sensor, register_edge_server
from app.services.update import update_edge_server
from app.utils.retry import async_retry

logger = logging.getLogger(__name__)


# ─── 라우터 ───────────────────────────────────────────────────────────────────

async def dispatch(message: aiomqtt.Message) -> None:
    topic = str(message.topic)
    parts = topic.split("/")

    if len(parts) != 4 or parts[0] != "signalcraft":
        logger.warning("[MQTT] Unexpected topic format: %s", topic)
        return

    try:
        payload = json.loads(message.payload)
    except (json.JSONDecodeError, ValueError):
        logger.warning("[MQTT] Non-JSON payload on topic %s", topic)
        return

    # alert topic: signalcraft/cloud/{server_id}/alert
    if parts[1] == "cloud" and parts[3] == "alert":
        await handle_alert(topic, payload)
        return

    # existing subscribe topics: signalcraft/{action}/{server_id}/cloud
    if parts[3] != "cloud":
        logger.warning("[MQTT] Unexpected topic format: %s", topic)
        return

    match parts[1]:
        case "server_init":
            await handle_server_init(topic, payload)
        case "forward_sensor_init":
            await handle_sensor_init(topic, payload)
        case "request_upload_audio":
            await handle_audio_upload_request(topic, payload)
        case "upload_result":
            await handle_upload_result(topic, payload)
        case "result_parameters_server":
            await handle_result_parameters_server(topic, payload)
        case "result_parameters_sensor":
            await handle_result_parameters_sensor(topic, payload)
        case "lwt":
            await handle_lwt(topic, payload)
        case _:
            logger.warning("[MQTT] Unhandled topic: %s", topic)


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
        await async_retry(
            lambda: register_edge_server(server_id_str, req.timezone, req.installation_machine),
            max_attempts=3,
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
    server_id_str = topic.split("/")[2]

    if await check_upload_anomaly(server_id_str):
        await insert_error_log(
            event="upload_missing",
            server_id=server_id_str,
            error="Upload interval exceeded 3x threshold during active hours",
            attempts=0,
        )
        logger.warning("[MQTT] Upload anomaly detected: %s", server_id_str)

    try:
        gcs_path, presigned_url, expires_at = await issue_presigned_url(server_id_str)
    except Exception as exc:
        await insert_error_log(
            event="presigned_url_failed",
            server_id=server_id_str,
            error=str(exc),
            attempts=1,
        )
        logger.error("[MQTT] Presigned URL generation failed: %s | %s", server_id_str, exc)
        return

    try:
        await publish_upload_audio_url(
            server_id_str,
            {"presigned_url": presigned_url, "gcs_path": gcs_path, "expires_at": expires_at},
        )
        logger.info("[MQTT] Presigned URL issued: %s → %s", server_id_str, gcs_path)
    except Exception as exc:
        logger.warning("[MQTT] URL issued but publish failed for %s: %s", server_id_str, exc)


async def handle_upload_result(topic: str, payload: dict) -> None:
    """AUDIO-010 | signalcraft/upload_result/{server_id}/cloud"""
    server_id_str = topic.split("/")[2]

    try:
        result = AudioUploadResult(**payload)
    except Exception as exc:
        logger.error("[MQTT] Invalid upload_result payload: %s", exc)
        return

    try:
        await record_upload_result(
            gcs_path=result.gcs_path,
            status=result.status,
            sensor_map=result.sensor_map,
            message=result.message,
        )
    except Exception as exc:
        await insert_error_log(
            event="audio_record_update_failed",
            server_id=server_id_str,
            error=str(exc),
            attempts=1,
        )
        logger.error("[MQTT] Failed to update audio record: %s | %s", server_id_str, exc)
        return

    if result.status == "failed":
        await insert_error_log(
            event="audio_upload_failed",
            server_id=server_id_str,
            error=result.message or "No message provided",
            attempts=1,
        )
        logger.warning("[MQTT] Audio upload failed: %s | %s", server_id_str, result.gcs_path)
    else:
        logger.info("[MQTT] Audio upload success: %s → %s", server_id_str, result.gcs_path)


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


async def handle_alert(topic: str, payload: dict) -> None:
    """ALERT | signalcraft/cloud/{server_id}/alert"""
    server_id_str = topic.split("/")[2]

    try:
        alert = EdgeAlertPayload(**payload)
    except Exception as exc:
        logger.error("[MQTT] Invalid alert payload: %s", exc)
        return

    await insert_edge_alert_log(
        server_id=server_id_str,
        level=alert.level,
        event=alert.event,
        edge_timestamp=alert.timestamp,
        detail=alert.detail,
    )
    logger.log(
        logging.ERROR if alert.level == "error" else logging.WARNING if alert.level == "warning" else logging.INFO,
        "[MQTT] Alert from %s: [%s] %s%s",
        server_id_str,
        alert.event,
        alert.level,
        f" | {alert.detail}" if alert.detail else "",
    )

async def handle_lwt(topic: str, payload: dict) -> None:
    """LWT-001/002 | signalcraft/lwt/{server_id}/cloud"""
    server_id_str = topic.split("/")[2]
    status_str = payload.get("status", "").upper()

    if status_str not in ("ONLINE", "OFFLINE"):
        logger.warning("[MQTT] Unknown LWT status: %s | %s", server_id_str, status_str)
        return

    status = EdgeServerStatus.ONLINE if status_str == "ONLINE" else EdgeServerStatus.OFFLINE
    server = await update_edge_server(server_id_str, server_status=status)                                                                       
    if server is None:
        logger.warning("[MQTT] LWT received for unknown server: %s", server_id_str)                                                                  
        return
    logger.info("[MQTT] LWT status update: %s → %s", server_id_str, status.value)