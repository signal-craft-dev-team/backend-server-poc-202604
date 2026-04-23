import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.sql import Base

if TYPE_CHECKING:
    from app.models.edge_sensor import EdgeSensor
    from app.models.place import Place


class EdgeServerStatus(str, enum.Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"


class EdgeServer(Base):
    __tablename__ = "edgeserver"
    __table_args__ = {"schema": "service"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    server_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    place_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service.place.id"), nullable=True
    )
    server_status: Mapped[EdgeServerStatus] = mapped_column(
        Enum(EdgeServerStatus, name="serverstatus"),
        nullable=False,
        default=EdgeServerStatus.ONLINE,
    )
    capture_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timezone: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    installation_machine: Mapped[str | None] = mapped_column(String, nullable=True)
    upload_interval_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active_hours_start: Mapped[str | None] = mapped_column(String(5), nullable=True)
    active_hours_end: Mapped[str | None] = mapped_column(String(5), nullable=True)

    place: Mapped["Place | None"] = relationship("Place", back_populates="edge_servers", lazy="raise")
    edge_sensors: Mapped[list["EdgeSensor"]] = relationship(
        "EdgeSensor", back_populates="edge_server", lazy="raise"
    )
