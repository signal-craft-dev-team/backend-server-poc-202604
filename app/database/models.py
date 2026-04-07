import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ServerStatus(enum.Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"


class Customer(Base):
    __tablename__ = "customer"
    __table_args__ = {"schema": "service"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_name = Column(String(100))
    contact_email = Column(String(100))
    contact_phone = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Place(Base):
    __tablename__ = "place"
    __table_args__ = {"schema": "service"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("service.customer.id"))
    place_name = Column(String(100))
    place_address = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EdgeServer(Base):
    __tablename__ = "edgeserver"
    __table_args__ = {"schema": "service"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    server_id = Column(String(100), unique=True, nullable=False)
    place_id = Column(UUID(as_uuid=True), ForeignKey("service.place.id"), nullable=True)
    server_status = Column(Enum(ServerStatus, name="serverstatus"))
    capture_duration_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    timezone = Column(String(20))
