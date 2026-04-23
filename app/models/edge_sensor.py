import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.sql import Base

class SensorType(str, enum.Enum):
    MICROPHONE = "MICROPHONE"
    ACCELEROMETER = "ACCELEROMETER"
    THERMOMETER = "THERMOMETER"


if TYPE_CHECKING:
    from app.models.edge_server import EdgeServer


class EdgeSensor(Base):
    __tablename__ = "edgesensor"
    __table_args__ = {"schema": "service"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    edge_server_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service.edgeserver.id"), nullable=False
    )
    device_name: Mapped[str] = mapped_column(String, nullable=False)
    sensor_type: Mapped[SensorType] = mapped_column(
        Enum(SensorType, name="sensortype", schema="service"), nullable=False,
    )
    sensor_position: Mapped[str | None] = mapped_column(String, nullable=True)
    installation_machine: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now(), onupdate=func.now()
    )

    edge_server: Mapped["EdgeServer"] = relationship(
        "EdgeServer", back_populates="edge_sensors", lazy="raise"
    )
