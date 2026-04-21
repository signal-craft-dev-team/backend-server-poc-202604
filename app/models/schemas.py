"""
MQTT 메시지 페이로드 Pydantic 스키마.

각 클래스명은 contracts/mqtt-topics.md의 시나리오 번호와 대응한다.
  - Inbound  : 백엔드가 Subscribe 하는 메시지 (엣지 → 백엔드)
  - Outbound : 백엔드가 Publish  하는 메시지 (백엔드 → 엣지)
"""

import uuid

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# 공통
# ─────────────────────────────────────────────────────────────────────────────

class ResultStatus(str):
    SUCCESS = "success"
    FAILED  = "failed"


# ─────────────────────────────────────────────────────────────────────────────
# NEW 시나리오 — 신규 설치
# ─────────────────────────────────────────────────────────────────────────────

class EdgeServerRegisterRequest(BaseModel):
    """NEW-001 | SUBSCRIBE | 엣지 서버 → 백엔드
    토픽: signalcraft/edge/{edge_server_id}/register
    """
    server_id: uuid.UUID = Field(..., description="엣지 서버 고유 식별자")
    installation_place: str | None = Field(None, description="설치 위치 설명")
    timezone: str | None = Field(None, description="현장 타임존 (예: Asia/Seoul)")


class EdgeServerRegisterResult(BaseModel):
    """NEW-002 | PUBLISH | 백엔드 → 엣지 서버
    토픽: signalcraft/edge/{edge_server_id}/register/result
    """
    status: str = Field(..., description="success | failed")
    message: str | None = Field(None, description="실패 시 사유 등 부가 메시지")


class EdgeSensorRegisterRequest(BaseModel):
    """NEW-004 | SUBSCRIBE | 엣지 서버 → 백엔드 (센서 등록 중계)
    토픽: signalcraft/edge/{edge_server_id}/sensor/{sensor_id}/register
    """
    edge_server_id: uuid.UUID = Field(..., description="요청을 중계한 엣지 서버의 DB id")
    device_name: str = Field(..., description="엣지 센서 장치명")
    sensor_type: str = Field(..., description="MICROPHONE | ACCELEROMETER | THERMOMETER")
    sensor_position: str | None = Field(None, description="센서 부착 위치")


class EdgeSensorRegisterResult(BaseModel):
    """NEW-005 | PUBLISH | 백엔드 → 엣지 서버 (센서 등록 결과)
    토픽: signalcraft/edge/{edge_server_id}/sensor/{sensor_id}/register/result
    """
    status: str = Field(..., description="success | failed")
    device_name: str = Field(..., description="등록 처리된 센서 장치명")
    message: str | None = Field(None, description="실패 시 사유 등 부가 메시지")
