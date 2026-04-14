"""CONTROL_SERVER 플로우 테스트.

시나리오:
  1. [APPLIED]  HTTP 요청 → MQTT 발행 → 엣지가 APPLIED ACK 응답 → HTTP 200
  2. [FAILED]   HTTP 요청 → MQTT 발행 → 엣지가 FAILED ACK 응답 → HTTP 200 (status=FAILED)
  3. [TIMEOUT]  HTTP 요청 → MQTT 발행 → 엣지가 응답 안 함 → HTTP 504
"""
import asyncio
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio

from tests.conftest import TEST_SERVER_ID


CONTROL_TOPIC    = f"signalcraft/control_server/{TEST_SERVER_ID}"
ACK_TOPIC        = f"signalcraft/control_server/{TEST_SERVER_ID}/ack"

CONTROL_PAYLOAD = {
    "command": "CHANGE_CAPTURE_DURATION",
    "server_id": TEST_SERVER_ID,
    "params": {"capture_duration_ms": 5000},
    "timestamp": datetime.now(timezone.utc).isoformat(),
}


@pytest.mark.asyncio
async def test_control_applied(edge, http):
    """엣지가 APPLIED ACK를 반환하면 HTTP 200 + status=APPLIED."""
    # 엣지: 클라우드가 보낼 제어 명령 구독
    cmd_queue = edge.subscribe(CONTROL_TOPIC)

    # 클라우드에 제어 명령 요청 (비동기로 동시 진행)
    async def _send_http():
        return await http.post("/mqtt/control_server", json=CONTROL_PAYLOAD, timeout=35.0)

    async def _reply_ack():
        cmd = await edge.wait_for(cmd_queue, timeout=10)
        edge.publish(ACK_TOPIC, {
            "message_id": cmd["message_id"],
            "server_id": TEST_SERVER_ID,
            "command": cmd["command"],
            "status": "APPLIED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    response, _ = await asyncio.gather(_send_http(), _reply_ack())

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "APPLIED"
    assert body["server_id"] == TEST_SERVER_ID


@pytest.mark.asyncio
async def test_control_failed(edge, http):
    """엣지가 FAILED ACK를 반환하면 HTTP 200 + status=FAILED."""
    cmd_queue = edge.subscribe(CONTROL_TOPIC)

    async def _send_http():
        return await http.post("/mqtt/control_server", json=CONTROL_PAYLOAD, timeout=35.0)

    async def _reply_ack():
        cmd = await edge.wait_for(cmd_queue, timeout=10)
        edge.publish(ACK_TOPIC, {
            "message_id": cmd["message_id"],
            "server_id": TEST_SERVER_ID,
            "command": cmd["command"],
            "status": "FAILED",
            "error": "parameter out of range",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    response, _ = await asyncio.gather(_send_http(), _reply_ack())

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "FAILED"
    assert body["error"] == "parameter out of range"


@pytest.mark.asyncio
async def test_control_ack_timeout(http):
    """엣지가 ACK를 보내지 않으면 HTTP 504."""
    # ACK 응답 없이 요청만 전송 (타임아웃은 서버 설정 30초이나
    # 테스트 환경에서 빠른 확인을 위해 timeout을 35초로 설정)
    response = await http.post(
        "/mqtt/control_server",
        json=CONTROL_PAYLOAD,
        timeout=35.0,
    )
    assert response.status_code == 504
