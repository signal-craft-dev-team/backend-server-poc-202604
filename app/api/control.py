"""HTTP router for CONTROL_SERVER scenario.

POST /mqtt/control_server
  1. server_id DB 존재 확인
  2. MQTT publish → signalcraft/control_server/{server_id}
  3. CONTROL_ACK 대기 (ACK_TIMEOUT_SEC)
  4. ACK status == APPLIED이면 DB 갱신
  5. ACK 결과 HTTP 응답으로 반환
"""
import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.client import get_db
from app.database.models import EdgeServer
from app.log.models import ServerCommLog
from app.log.upload_log import write_server_comm_log
from app.mqtt.ack_manager import ack_manager
from app.mqtt.publisher import publish
from app.mqtt.schemas import (
    AckStatus,
    ControlAckResponse,
    ControlCommand,
    ControlServerMessage,
    ControlServerRequest,
)
from app.mqtt.state import get_client
from app.mqtt.topics import control_topic

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mqtt", tags=["mqtt"])

ACK_TIMEOUT_SEC = 30


async def _apply_ack_to_db(
    db: AsyncSession,
    ack: ControlAckResponse,
    request: ControlServerRequest,
) -> None:
    """ACK status가 APPLIED일 때 EdgeServer 설정값을 DB에 반영."""
    try:
        result = await db.execute(
            select(EdgeServer).where(EdgeServer.server_id == ack.server_id)
        )
        server = result.scalar_one_or_none()
        if server is None:
            logger.error(f"[DB] EdgeServer not found for ACK update | server_id={ack.server_id}")
            return

        params = request.params

        if ack.command == ControlCommand.CHANGE_CAPTURE_DURATION:
            if params.capture_duration_ms is not None:
                server.capture_duration_ms = params.capture_duration_ms

        elif ack.command == ControlCommand.UPDATE_UPLOAD_SCHEDULE:
            if params.upload_interval_ms is not None:
                server.upload_interval_ms = params.upload_interval_ms

        elif ack.command == ControlCommand.UPDATE_ACTIVE_HOURS:
            if params.active_hours is not None:
                server.active_hours_start = params.active_hours.start
                server.active_hours_end = params.active_hours.end

        server.updated_at = datetime.now(timezone.utc)
        await db.commit()
        logger.info(f"[DB] EdgeServer updated | server_id={ack.server_id} command={ack.command}")
    except Exception as exc:
        logger.error(f"[DB] Failed to apply ACK to DB | server_id={ack.server_id} error={exc}")
        await db.rollback()


@router.post(
    "/control_server",
    response_model=ControlAckResponse,
    summary="엣지 서버 파라미터 제어 (CONTROL_SERVER)",
)
async def control_server(
    request: ControlServerRequest,
    db: AsyncSession = Depends(get_db),
) -> ControlAckResponse:
    # 1. server_id DB 검증
    result = await db.execute(
        select(EdgeServer).where(EdgeServer.server_id == request.server_id)
    )
    server = result.scalar_one_or_none()
    if server is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"EdgeServer '{request.server_id}' not found",
        )

    # 2. MQTT 메시지 생성 (message_id는 UUID 자동 생성)
    message = ControlServerMessage(
        command=request.command,
        server_id=request.server_id,
        target_sensor_id=request.target_sensor_id,
        params=request.params,
        timestamp=request.timestamp,
    )

    # 3. ACK 대기 큐 등록 (publish 전에 등록해야 race condition 방지)
    ack_queue = ack_manager.register(message.message_id)

    # 4. MQTT publish
    client = get_client()
    if client is None:
        ack_manager.unregister(message.message_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MQTT client is not available",
        )

    topic = control_topic(request.server_id)
    try:
        await publish(client, topic, message.model_dump_json())
    except Exception as exc:
        ack_manager.unregister(message.message_id)
        logger.error(f"[MQTT] publish failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to publish MQTT message",
        )

    # 5. CONTROL_SENT 로그
    await write_server_comm_log(ServerCommLog(
        server_id=request.server_id,
        message_id=message.message_id,
        command=request.command,
        event_type="CONTROL_SENT",
        latest_topic=topic,
        timestamp=datetime.now(timezone.utc),
    ))

    # 6. CONTROL_ACK 대기
    try:
        ack_payload = await asyncio.wait_for(ack_queue.get(), timeout=ACK_TIMEOUT_SEC)
    except asyncio.TimeoutError:
        await write_server_comm_log(ServerCommLog(
            server_id=request.server_id,
            message_id=message.message_id,
            command=request.command,
            event_type="ACK_TIMEOUT",
            latest_topic=topic,
            timestamp=datetime.now(timezone.utc),
        ))
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"No ACK received from edge server within {ACK_TIMEOUT_SEC}s",
        )
    finally:
        ack_manager.unregister(message.message_id)

    ack = ControlAckResponse(**ack_payload)

    # 7. ACK_RECEIVED 로그
    await write_server_comm_log(ServerCommLog(
        server_id=ack.server_id,
        message_id=ack.message_id,
        command=ack.command,
        event_type="ACK_RECEIVED",
        status=ack.status,
        error=ack.error,
        latest_topic=topic,
        timestamp=ack.timestamp,
    ))

    # 8. APPLIED일 때만 DB 갱신
    if ack.status == AckStatus.APPLIED:
        await _apply_ack_to_db(db, ack, request)

    return ack
