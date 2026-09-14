from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.hospital import Hospital


class HospitalConfiguration(Base, TimestampMixin):
    __tablename__ = "hospital_configurations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # One configuration per hospital
    hospital_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hospitals.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Calling window (stored as "HH:MM" strings for portability)
    calling_start_time: Mapped[str] = mapped_column(String(5), nullable=False, default="09:00")
    calling_end_time: Mapped[str] = mapped_column(String(5), nullable=False, default="18:00")

    # Capacity / retry limits
    max_calling_capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    # Future extensible fields
    notification_preferences: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    ehr_settings: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # ------------------------------------------------------------------ #
    # Relationships                                                         #
    # ------------------------------------------------------------------ #
    hospital: Mapped[Hospital] = relationship(
        "Hospital", back_populates="configuration", lazy="select"
    )

    def __repr__(self) -> str:
        return (
            f"<HospitalConfiguration hospital_id={self.hospital_id} "
            f"window={self.calling_start_time}–{self.calling_end_time}>"
        )
