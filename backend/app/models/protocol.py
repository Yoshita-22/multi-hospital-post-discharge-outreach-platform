from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.hospital import Hospital
    from app.models.knowledge_document import KnowledgeDocument
    from app.models.user import User


class ProtocolStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class Protocol(Base, TimestampMixin):
    __tablename__ = "protocols"
    __table_args__ = (
        # A hospital cannot have two protocols with the same name+version
        UniqueConstraint("hospital_id", "name", "version", name="uq_protocol_hospital_name_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    hospital_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hospitals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[ProtocolStatus] = mapped_column(
        SAEnum(ProtocolStatus, name="protocolstatus", create_type=True),
        default=ProtocolStatus.DRAFT,
        nullable=False,
    )
    # Flexible clinical content: questions, red_flags, instructions, etc.
    content: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Structured rules for deterministic safety and protocol evaluation
    clinical_rules: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                         #
    # ------------------------------------------------------------------ #
    hospital: Mapped[Hospital] = relationship(
        "Hospital", back_populates="protocols", lazy="select"
    )
    creator: Mapped[User | None] = relationship(
        "User", foreign_keys=[created_by], lazy="select"
    )
    knowledge_documents: Mapped[list[KnowledgeDocument]] = relationship(
        "KnowledgeDocument", back_populates="protocol", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Protocol id={self.id} name={self.name!r} v{self.version} status={self.status}>"
