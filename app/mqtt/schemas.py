"""Pydantic schemas for MQTT messages."""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class ControlCommand(str, Enum):
    CHANGE_CAPTURE_DURATION = "CHANGE_CAPTURE_DURATION"
    UPDATE_UPLOAD_SCHEDULE = "UPDATE_UPLOAD_SCHEDULE"
    UPDATE_ACTIVE_HOURS = "UPDATE_ACTIVE_HOURS"


class AckStatus(str, Enum):
    APPLIED = "APPLIED"
    FAILED = "FAILED"


class ActiveHours(BaseModel):
    start: str  # "HH:MM"
    end: str    # "HH:MM"


class ControlParams(BaseModel):
    capture_duration_ms: Optional[int] = None
    upload_interval_ms: Optional[int] = None
    active_hours: Optional[ActiveHours] = None


# ---------- HTTP request body ----------

class ControlServerRequest(BaseModel):
    command: ControlCommand
    server_id: str
    target_sensor_id: Optional[str] = None
    params: ControlParams
    timestamp: datetime


# ---------- MQTT payloads ----------

class ControlServerMessage(BaseModel):
    """Payload published to signalcraft/control_server/{server_id}."""
    message_id: str = Field(default_factory=lambda: str(uuid4()))
    command: ControlCommand
    server_id: str
    target_sensor_id: Optional[str] = None
    params: ControlParams
    timestamp: datetime


class ControlAckResponse(BaseModel):
    """Payload received from signalcraft/control_server/{server_id}/ack — also returned as HTTP response."""
    message_id: str
    server_id: str
    command: ControlCommand
    target_sensor_id: Optional[str] = None
    status: AckStatus
    error: Optional[str] = None
    timestamp: datetime


# ---------- UPLOAD_AUDIO / SEND_URL / COMPLETE_UPLOAD ----------

class UploadAudioMessage(BaseModel):
    """Edge → Cloud: signalcraft/upload_audio/{server_id}"""
    server_id: str
    sensor_id: str
    file_name: str
    recorded_at: datetime
    duration_ms: int
    file_size_bytes: int
    timestamp: datetime


class SendUrlMessage(BaseModel):
    """Cloud → Edge: signalcraft/send_url/{server_id}"""
    server_id: str
    file_name: str
    signed_url: str
    expires_at: datetime
    timestamp: datetime


class CompleteUploadMessage(BaseModel):
    """Edge → Cloud: signalcraft/complete_upload/{server_id}"""
    server_id: str
    sensor_id: str
    file_name: str
    recorded_at: datetime
    duration_ms: int
    file_size_bytes: int
    timestamp: datetime


class RetryUploadMessage(BaseModel):
    """Cloud → Edge: signalcraft/retry_upload/{server_id}"""
    server_id: str
    file_name: str
    reason: str
    timestamp: datetime


# ---------- ABNORMAL / DISK_ALERT / UPLOAD_FAILED ----------

class AbnormalMessage(BaseModel):
    """Edge → Cloud: signalcraft/cloud/{server_id}/abnormal"""
    server_id: str
    sensor_id: Optional[str] = None
    event_type: str                     # e.g. "ABNORMAL", "SENSOR_OFFLINE"
    detail: Optional[str] = None
    timestamp: datetime


class DiskAlertMessage(BaseModel):
    """Edge → Cloud: signalcraft/cloud/{server_id}/disk_alert"""
    server_id: str
    disk_usage_percent: float
    threshold_percent: float
    timestamp: datetime


class UploadFailedMessage(BaseModel):
    """Edge → Cloud: signalcraft/cloud/{server_id}/upload_failed"""
    server_id: str
    sensor_id: Optional[str] = None
    file_name: Optional[str] = None
    reason: str
    timestamp: datetime
