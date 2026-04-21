import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.sql import Base

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.edge_server import EdgeServer


class Place(Base):
    __tablename__ = "place"
    __table_args__ = {"schema": "service"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service.customer.id"), nullable=False
    )
    place_name: Mapped[str] = mapped_column(String, nullable=False)
    place_address: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now(), onupdate=func.now()
    )

    customer: Mapped["Customer"] = relationship("Customer", back_populates="places", lazy="raise")
    edge_servers: Mapped[list["EdgeServer"]] = relationship(
        "EdgeServer", back_populates="place", lazy="raise"
    )
