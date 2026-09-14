from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.audit_log import AuditLog
    from app.models.configuration import HospitalConfiguration
    from app.models.knowledge_document import KnowledgeDocument
    from app.models.protocol import Protocol
    from app.models.user import User


class HospitalStatus(str, enum.Enum):
    ONBOARDING = "ONBOARDING"
    READY = "READY"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"


class Hospital(Base, TimestampMixin):
    __tablename__ = "hospitals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    timezone: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[HospitalStatus] = mapped_column(
        SAEnum(HospitalStatus, name="hospitalstatus", create_type=True),
        default=HospitalStatus.ONBOARDING,
        nullable=False,
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                         #
    # ------------------------------------------------------------------ #
    users: Mapped[list[User]] = relationship(
        "User", back_populates="hospital", lazy="select"
    )
    configuration: Mapped[HospitalConfiguration | None] = relationship(
        "HospitalConfiguration", back_populates="hospital", uselist=False, lazy="select"
    )
    protocols: Mapped[list[Protocol]] = relationship(
        "Protocol", back_populates="hospital", lazy="select"
    )
    knowledge_documents: Mapped[list[KnowledgeDocument]] = relationship(
        "KnowledgeDocument", back_populates="hospital", lazy="select"
    )
    audit_logs: Mapped[list[AuditLog]] = relationship(
        "AuditLog", back_populates="hospital", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Hospital id={self.id} name={self.name!r} status={self.status}>"
