"""
MQTT 메시지 페이로드 Pydantic 스키마.

각 클래스명은 contracts/mqtt-topics.md의 시나리오 번호와 대응한다.
  - Inbound  : 백엔드가 Subscribe 하는 메시지 (엣지 → 백엔드)
  - Outbound : 백엔드가 Publish  하는 메시지 (백엔드 → 엣지)
"""

from pydantic import BaseModel, Field
import uuid
from app.models.edge_sensor import SensorType
from app.models.edge_server import EdgeServerStatus

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
    토픽: signalcraft/server_init/{server_id}/cloud
    """
    server_id: str = Field(..., description="엣지 서버 고유 식별자")
    installation_machine: str | None = Field(None, description="설치 장비(혹은 위치) 설명")
    timezone: str | None = Field(None, description="현장 타임존 (예: Asia/Seoul)")


class EdgeServerRegisterResult(BaseModel):
    """NEW-002 | PUBLISH | 백엔드 → 엣지 서버
    토픽: signalcraft/register_server/cloud/{server_id}
    """
    status: str = Field(..., description="success | failed")
    message: str | None = Field(None, description="실패 시 사유 등 부가 메시지")


class EdgeSensorRegisterRequest(BaseModel):
    """NEW-004 | SUBSCRIBE | 엣지 서버 → 백엔드 (센서 등록 중계)
    토픽: signalcraft/forward_sensor_init/{server_id}/cloud
    edge_server_id는 토픽의 server_id로 DB 조회하여 획득 (payload 불필요)
    """
    device_name: str | None = Field(None, description="엣지 센서 장치명")
    sensor_type: str | None = Field(None, description="MICROPHONE | ACCELEROMETER | THERMOMETER")
    sensor_position: str | None = Field(None, description="센서 부착 위치")
    installation_machine: str | None = Field(None, description="센서가 설치된 장비명")


class EdgeSensorRegisterResult(BaseModel):
    """NEW-005 | PUBLISH | 백엔드 → 엣지 서버 (센서 등록 결과)
    토픽: signalcraft/register_sensor/cloud/{server_id}
    """
    status: str = Field(..., description="success | failed")
    device_name: str = Field(..., description="등록 처리된 센서 장치명")
    message: str | None = Field(None, description="실패 시 사유 등 부가 메시지")

# ─────────────────────────────────────────────────────────────────────────────
# AUDIO 시나리오 — 오디오 수집
# ─────────────────────────────────────────────────────────────────────────────

class AudioUploadRequest(BaseModel):
    """AUDIO-005 | SUBSCRIBE | 엣지 서버 → 백엔드
    토픽: signalcraft/request_upload_audio/{server_id}/cloud
    페이로드 없음 — server_id는 토픽에서 추출
    """
    pass


class AudioUrlPayload(BaseModel):
    """AUDIO-007 | PUBLISH | 백엔드 → 엣지 서버
    토픽: signalcraft/upload_audio_url/cloud/{server_id}
    """
    presigned_url: str = Field(..., description="GCS PUT Presigned URL")
    gcs_path: str = Field(..., description="GCS 오브젝트 경로")
    expires_at: str = Field(..., description="URL 만료 시각 (ISO8601)")


class AudioUploadResult(BaseModel):
    """AUDIO-010 | SUBSCRIBE | 엣지 서버 → 백엔드
    토픽: signalcraft/upload_result/{server_id}/cloud
    """
    gcs_path: str = Field(..., description="업로드된 GCS 경로")
    status: str = Field(..., description="success | failed")
    message: str | None = Field(None, description="실패 시 사유")
    sensor_map: list[str] = Field(default_factory=list, description="녹음된 센서 device_name 목록")


# ─────────────────────────────────────────────────────────────────────────────
# CTRL 시나리오 — 파라미터 제어 결과
# ─────────────────────────────────────────────────────────────────────────────

class CtrlServerResultPayload(BaseModel):
    """CTRL-SERVER-002 | SUBSCRIBE | 엣지 서버 → 백엔드
    토픽: signalcraft/result_parameters_server/{server_id}/cloud
    """
    status: str = Field(..., description="success | failed")
    message: str | None = Field(None, description="실패 시 사유")


# ─────────────────────────────────────────────────────────────────────────────
# API 시나리오
# ─────────────────────────────────────────────────────────────────────────────

class UpdateServerParametersRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": [
        {
            "server_id": "test-server-0001",
            "server_status": "ONLINE",
            "capture_duration_ms": 5000,
            "timezone": "Asia/Seoul",
            "installation_machine": "raspberry-pi-4",
            "upload_interval_ms": 60000,
            "active_hours_start": "08:00",
            "active_hours_end": "22:00",
        }
    ]}}

    server_id: str
    place_id: uuid.UUID | None = None
    server_status: EdgeServerStatus | None = None
    capture_duration_ms: int | None = None
    timezone: str | None = None
    installation_machine: str | None = None
    upload_interval_ms: int | None = None
    active_hours_start: str | None = None
    active_hours_end: str | None = None


class UpdateServerParametersResponse(BaseModel):
    status: str
    server_id: str
    mqtt_published: bool


class UpdateSensorParametersRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": [
        {
            "server_id": "test-server-0001",
            "device_name": "mic-1000",
            "sensor_type": "MICROPHONE",
            "sensor_position": "천장 좌측",
            "installation_machine": "밀링 머신",
        }
    ]}}

    server_id: str
    device_name: str
    sensor_type: SensorType | None = None
    sensor_position: str | None = None
    installation_machine: str | None = None


class UpdateSensorParametersResponse(BaseModel):
    status: str
    server_id: str
    device_name: str
