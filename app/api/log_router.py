"""로그 관련 라우터 (연결 테스트 포함)."""
from datetime import datetime, timezone

from fastapi import APIRouter

from app.log.client import get_db
from app.log.models import AudioUploadLog, SensorCommLog, ServerCommLog, UploadErrorLog
from app.log.upload_log import (
    write_audio_upload_log,
    write_error_log,
    write_sensor_comm_log,
    write_server_comm_log,
)

router = APIRouter(prefix="/log", tags=["log"])


@router.get("/health-check")
async def log_health_check():
    """MongoDB 연결 상태 확인."""
    try:
        await get_db().command("ping")
        return {"status": "ok"}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


@router.post("/test/audio-upload")
async def test_audio_upload_log():
    """AudioUploadLog 기록 테스트."""
    await write_audio_upload_log(AudioUploadLog(
        server_id="test-server-01",
        sensor_id="test-sensor-01",
        file_name="test_audio_20260409.wav",
        recorded_at=datetime.now(timezone.utc),
        duration_ms=5000,
        file_size_bytes=102400,
        uploaded_at=datetime.now(timezone.utc),
        inferred=False,
    ))
    return {"status": "ok", "collection": "audio_upload_logs"}


@router.post("/test/upload-error")
async def test_upload_error_log():
    """UploadErrorLog 기록 테스트."""
    await write_error_log(UploadErrorLog(
        server_id="test-server-01",
        file_name="test_audio_20260409.wav",
        reason="테스트 에러 로그",
    ))
    return {"status": "ok", "collection": "upload_error_logs"}


@router.post("/test/server-comm")
async def test_server_comm_log():
    """ServerCommLog 기록 테스트."""
    await write_server_comm_log(ServerCommLog(
        server_id="test-server-01",
        message_id="test-message-id-001",
        command="CHANGE_CAPTURE_DURATION",
        event_type="ACK_RECEIVED",
        status="APPLIED",
        timestamp=datetime.now(timezone.utc),
    ))
    return {"status": "ok", "collection": "server_comm_logs"}


@router.post("/test/sensor-comm")
async def test_sensor_comm_log():
    """SensorCommLog 기록 테스트."""
    await write_sensor_comm_log(SensorCommLog(
        server_id="test-server-01",
        sensor_id="test-sensor-01",
        file_name="test_audio_20260409.wav",
        event_type="UPLOAD_REQUESTED",
        detail={"note": "테스트 센서 통신 로그"},
    ))
    return {"status": "ok", "collection": "sensor_comm_logs"}
