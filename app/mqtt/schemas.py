"""Pydantic schemas for MQTT control messages."""
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
