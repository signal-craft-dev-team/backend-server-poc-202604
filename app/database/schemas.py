from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.database.models import ServerStatus, SensorType


# ── Customer ──────────────────────────────────────────────

class CustomerCreate(BaseModel):
    customer_name: str
    contact_email: str
    contact_phone: Optional[str] = None


class CustomerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_name: str
    contact_email: str
    contact_phone: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ── Place ─────────────────────────────────────────────────

class PlaceCreate(BaseModel):
    customer_id: UUID
    place_name: str
    place_address: str


class PlaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    place_name: str
    place_address: str
    created_at: datetime
    updated_at: datetime


# ── EdgeServer ────────────────────────────────────────────

class EdgeServerCreate(BaseModel):
    server_id: str
    place_id: Optional[UUID] = None
    server_status: ServerStatus
    capture_duration_ms: int
    timezone: str
    installation_place: Optional[str] = None


class EdgeServerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    server_id: str
    place_id: Optional[UUID] = None
    server_status: ServerStatus
    capture_duration_ms: int
    timezone: str
    installation_place: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ── EdgeSensor ────────────────────────────────────────────

class EdgeSensorCreate(BaseModel):
    server_id: str
    device_name: str
    sensor_type: SensorType
    sensor_position: Optional[str] = None


class EdgeSensorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    edge_server_id: UUID
    device_name: str
    sensor_type: SensorType
    sensor_position: Optional[str] = None
    created_at: datetime
    updated_at: datetime
