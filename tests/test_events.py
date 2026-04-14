"""이벤트 수신 테스트 (ABNORMAL / DISK_ALERT / UPLOAD_FAILED).

시나리오: 엣지가 각 이벤트 토픽으로 메시지 발행 → 클라우드가 수신 후 MongoDB에 로그 기록
검증: HTTP 응답 없이 MQTT publish 후 MongoDB 직접 조회로 확인
"""
import asyncio
import uuid
from datetime import datetime, timezone

import pytest
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

from tests.conftest import TEST_SERVER_ID

load_dotenv()

ABNORMAL_TOPIC      = f"signalcraft/cloud/{TEST_SERVER_ID}/abnormal"
DISK_ALERT_TOPIC    = f"signalcraft/cloud/{TEST_SERVER_ID}/disk_alert"
UPLOAD_FAILED_TOPIC = f"signalcraft/cloud/{TEST_SERVER_ID}/upload_failed"

def _get_db():
    # 테스트마다 새 클라이언트 생성 — 루프가 테스트마다 교체되므로 캐싱 불가
    client = AsyncIOMotorClient(os.environ["MONGODB_URI"])
    return client[os.environ["MONGODB_DB_NAME"]]


@pytest.mark.asyncio
async def test_abnormal_event_logged(edge):
    """ABNORMAL 수신 시 sensor_comm_logs에 기록된다."""
    file_name = f"abnormal_{uuid.uuid4().hex[:8]}"

    edge.publish(ABNORMAL_TOPIC, {
        "server_id": TEST_SERVER_ID,
        "sensor_id": "test-sensor-01",
        "event_type": "SENSOR_OFFLINE",
        "detail": "microphone disconnected",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    await asyncio.sleep(2)

    db = _get_db()
    doc = await db["sensor_comm_logs"].find_one(
        {"server_id": TEST_SERVER_ID, "event_type": "SENSOR_OFFLINE"},
        sort=[("created_at", -1)],
    )
    assert doc is not None
    assert doc["status"] == "ABNORMAL"


@pytest.mark.asyncio
async def test_disk_alert_logged(edge):
    """DISK_ALERT 수신 시 sensor_comm_logs에 기록된다."""
    edge.publish(DISK_ALERT_TOPIC, {
        "server_id": TEST_SERVER_ID,
        "disk_usage_percent": 92.5,
        "threshold_percent": 90.0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    await asyncio.sleep(2)

    db = _get_db()
    doc = await db["sensor_comm_logs"].find_one(
        {"server_id": TEST_SERVER_ID, "event_type": "DISK_ALERT"},
        sort=[("created_at", -1)],
    )
    assert doc is not None
    assert doc["status"] == "WARNING"
    assert doc["detail"]["disk_usage_percent"] == 92.5


@pytest.mark.asyncio
async def test_upload_failed_logged(edge):
    """UPLOAD_FAILED 수신 시 upload_error_logs에 기록된다."""
    file_name = f"failed_{uuid.uuid4().hex[:8]}.wav"

    edge.publish(UPLOAD_FAILED_TOPIC, {
        "server_id": TEST_SERVER_ID,
        "sensor_id": "test-sensor-01",
        "file_name": file_name,
        "reason": "network timeout during PUT",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    await asyncio.sleep(2)

    db = _get_db()
    doc = await db["upload_error_logs"].find_one(
        {"server_id": TEST_SERVER_ID, "file_name": file_name},
        sort=[("occurred_at", -1)],
    )
    assert doc is not None
    assert "UPLOAD_FAILED" in doc["reason"]
