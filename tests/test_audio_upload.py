"""UPLOAD_AUDIO 플로우 테스트.

시나리오:
  1. [COMPLETE]  엣지가 UPLOAD_AUDIO 발행 → 클라우드가 SEND_URL 응답 → 엣지가 COMPLETE_UPLOAD 발행
  2. [TIMEOUT]   엣지가 UPLOAD_AUDIO 발행 → 클라우드가 SEND_URL 응답 → COMPLETE_UPLOAD 없음
                 → 클라우드가 retry_upload 발행 (GCS에 파일 없는 경우)
"""
import asyncio
import uuid
from datetime import datetime, timezone

import pytest

from tests.conftest import TEST_SERVER_ID

TEST_SENSOR_ID  = "test-sensor-01"
UPLOAD_TOPIC    = f"signalcraft/upload_audio/{TEST_SERVER_ID}"
SEND_URL_TOPIC  = f"signalcraft/send_url/{TEST_SERVER_ID}"
COMPLETE_TOPIC  = f"signalcraft/complete_upload/{TEST_SERVER_ID}"
RETRY_TOPIC     = f"signalcraft/retry_upload/{TEST_SERVER_ID}"


def _make_upload_payload(file_name: str) -> dict:
    return {
        "server_id": TEST_SERVER_ID,
        "sensor_id": TEST_SENSOR_ID,
        "file_name": file_name,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "duration_ms": 5000,
        "file_size_bytes": 102400,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@pytest.mark.asyncio
async def test_upload_audio_complete(edge):
    """정상 플로우: UPLOAD_AUDIO → SEND_URL 수신 → COMPLETE_UPLOAD 발행."""
    file_name = f"test_{uuid.uuid4().hex[:8]}.wav"

    # 엣지: 클라우드가 보낼 SEND_URL 구독
    url_queue = edge.subscribe(SEND_URL_TOPIC)

    # 엣지: UPLOAD_AUDIO 발행
    edge.publish(UPLOAD_TOPIC, _make_upload_payload(file_name))

    # 엣지: SEND_URL 수신 대기
    send_url_msg = await edge.wait_for(url_queue, timeout=15)
    assert send_url_msg["file_name"] == file_name
    assert "signed_url" in send_url_msg
    assert send_url_msg["signed_url"].startswith("https://")

    # 엣지: COMPLETE_UPLOAD 발행
    edge.publish(COMPLETE_TOPIC, {
        "server_id": TEST_SERVER_ID,
        "sensor_id": TEST_SENSOR_ID,
        "file_name": file_name,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "duration_ms": 5000,
        "file_size_bytes": 102400,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    # COMPLETE_UPLOAD 발행 후 서버가 처리할 시간 부여
    await asyncio.sleep(2)


@pytest.mark.asyncio
async def test_upload_audio_timeout_retry(edge):
    """타임아웃 플로우: COMPLETE_UPLOAD 미발행 → GCS 파일 없음 → retry_upload 수신."""
    file_name = f"test_missing_{uuid.uuid4().hex[:8]}.wav"

    url_queue    = edge.subscribe(SEND_URL_TOPIC)
    retry_queue  = edge.subscribe(RETRY_TOPIC)

    # 엣지: UPLOAD_AUDIO 발행 (COMPLETE_UPLOAD는 보내지 않음)
    edge.publish(UPLOAD_TOPIC, _make_upload_payload(file_name))

    # SEND_URL 수신 확인
    send_url_msg = await edge.wait_for(url_queue, timeout=15)
    assert send_url_msg["file_name"] == file_name

    # 타임아웃(30초) 후 retry_upload 대기
    retry_msg = await edge.wait_for(retry_queue, timeout=40)
    assert retry_msg["server_id"] == TEST_SERVER_ID
    assert retry_msg["file_name"] == file_name
    assert "reason" in retry_msg


@pytest.mark.asyncio
async def test_send_url_contains_expiry(edge):
    """SEND_URL 메시지에 expires_at 필드가 포함되어야 한다."""
    file_name = f"test_expiry_{uuid.uuid4().hex[:8]}.wav"
    url_queue = edge.subscribe(SEND_URL_TOPIC)

    edge.publish(UPLOAD_TOPIC, _make_upload_payload(file_name))
    send_url_msg = await edge.wait_for(url_queue, timeout=15)

    assert "expires_at" in send_url_msg
    # COMPLETE_UPLOAD 발행으로 정리
    edge.publish(COMPLETE_TOPIC, {
        "server_id": TEST_SERVER_ID,
        "sensor_id": TEST_SENSOR_ID,
        "file_name": file_name,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "duration_ms": 5000,
        "file_size_bytes": 102400,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    await asyncio.sleep(1)
