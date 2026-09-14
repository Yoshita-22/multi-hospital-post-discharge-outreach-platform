from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.hospital import Hospital
    from app.models.user import User


class AuditLog(Base):
    """
    Immutable audit trail — no updated_at; these records are never modified.

    Every important action in the platform produces an AuditLog entry answering:
        WHO   → actor_user_id
        WHAT  → action  (e.g. HOSPITAL_CREATED)
        WHERE → hospital_id
        WHICH → resource_type + resource_id
        WHEN  → created_at
    """

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    hospital_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hospitals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    # Immutable timestamp only
    from datetime import datetime
    from sqlalchemy import DateTime, func
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                         #
    # ------------------------------------------------------------------ #
    hospital: Mapped[Hospital | None] = relationship(
        "Hospital", back_populates="audit_logs", lazy="select"
    )
    actor: Mapped[User | None] = relationship(
        "User", foreign_keys=[actor_user_id], lazy="select"
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog action={self.action!r} actor={self.actor_user_id} "
            f"hospital={self.hospital_id}>"
        )
