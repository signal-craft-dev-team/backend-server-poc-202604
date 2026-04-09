"""로그 문서 Pydantic 모델.

컬렉션 매핑:
  - AudioUploadLog  → audio_upload_logs
  - UploadErrorLog  → upload_error_logs
  - ServerCommLog   → server_comm_logs
  - SensorCommLog   → sensor_comm_logs
"""
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AudioUploadLog(BaseModel):
    """오디오 파일 업로드 완료 로그.

    inferred=False : COMPLETE_UPLOAD 정상 수신
    inferred=True  : 타임아웃 후 GCS에서 파일 확인됨
    """
    server_id: str
    sensor_id: str
    file_name: str
    recorded_at: datetime
    duration_ms: int
    file_size_bytes: int
    uploaded_at: Optional[datetime] = None
    inferred: bool = False
    sequence_number: Optional[int] = None
    created_at: datetime = Field(default_factory=_now)


class UploadErrorLog(BaseModel):
    """오디오 업로드 에러 로그."""
    server_id: Optional[str] = None
    file_name: Optional[str] = None
    reason: str
    occurred_at: datetime = Field(default_factory=_now)


class ServerCommLog(BaseModel):
    """엣지 서버 제어 통신 로그 (CONTROL_SERVER 명령/ACK).

    event_type 예시:
      - "CONTROL_SENT"   : 제어 명령 발행
      - "ACK_RECEIVED"   : ACK 수신
      - "ACK_TIMEOUT"    : ACK 타임아웃
    """
    server_id: str
    message_id: str
    command: str
    event_type: str
    status: Optional[str] = None        # APPLIED / FAILED
    error: Optional[str] = None
    latest_topic: Optional[str] = None
    timestamp: datetime
    created_at: datetime = Field(default_factory=_now)


class SensorCommLog(BaseModel):
    """센서 통신 로그.

    event_type 예시:
      - "UPLOAD_REQUESTED"  : 엣지에서 업로드 요청 수신
      - "URL_SENT"          : Presigned URL 발행
      - "UPLOAD_COMPLETE"   : 업로드 완료 수신
      - "UPLOAD_INFERRED"   : GCS 확인으로 완료 추론
      - "RETRY_REQUESTED"   : 재업로드 요청 발행
    """
    server_id: str
    sensor_id: Optional[str] = None
    file_name: Optional[str] = None
    event_type: str
    status: Optional[str] = None
    detail: Optional[dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=_now)
    created_at: datetime = Field(default_factory=_now)
