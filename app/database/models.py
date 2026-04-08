import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ServerStatus(enum.Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"


class SensorType(enum.Enum):
    MICROPHONE = "MICROPHONE"
    ACCELEROMETER = "ACCELEROMETER"
    THERMOMETER = "THERMOMETER"


class Customer(Base):
    __tablename__ = "customer"
    __table_args__ = {"schema": "service"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_name = Column(String(100))
    contact_email = Column(String(100))
    contact_phone = Column(String(20))
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class Place(Base):
    __tablename__ = "place"
    __table_args__ = {"schema": "service"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("service.customer.id"))
    place_name = Column(String(100))
    place_address = Column(String(100))
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class EdgeServer(Base):
    __tablename__ = "edgeserver"
    __table_args__ = {"schema": "service"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    server_id = Column(String(100), unique=True, nullable=False)
    place_id = Column(UUID(as_uuid=True), ForeignKey("service.place.id"), nullable=True)
    server_status = Column(Enum(ServerStatus, name="serverstatus"))
    capture_duration_ms = Column(Integer, nullable=True)
    upload_interval_ms = Column(Integer, nullable=True)
    active_hours_start = Column(String(5), nullable=True)   # "HH:MM"
    active_hours_end = Column(String(5), nullable=True)     # "HH:MM"
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    timezone = Column(String(20))
    installation_place = Column(String(50), nullable=True)


class EdgeSensor(Base):
    __tablename__ = "edgesensor"
    __table_args__ = {"schema": "service"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    edge_server_id = Column(UUID(as_uuid=True), ForeignKey("service.edgeserver.id", ondelete="CASCADE"), nullable=False)
    device_name = Column(String(50), nullable=False)
    sensor_type = Column(Enum(SensorType, name="sensortype", schema="service"), nullable=False)
    sensor_position = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
