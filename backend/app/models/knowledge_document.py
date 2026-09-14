from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.hospital import Hospital
    from app.models.protocol import Protocol


class KnowledgeDocumentStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class KnowledgeDocument(Base, TimestampMixin):
    """
    Hospital-scoped knowledge document.

    Phase 1: Plain-text storage in PostgreSQL.
    Future: content will also be embedded into a vector store,
            always filtered by hospital_id to enforce tenant isolation.
    """

    __tablename__ = "knowledge_documents"

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
    # Optional link to a specific protocol
    protocol_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("protocols.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[KnowledgeDocumentStatus] = mapped_column(
        SAEnum(KnowledgeDocumentStatus, name="knowledgedocumentstatus", create_type=True),
        default=KnowledgeDocumentStatus.ACTIVE,
        nullable=False,
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                         #
    # ------------------------------------------------------------------ #
    hospital: Mapped[Hospital] = relationship(
        "Hospital", back_populates="knowledge_documents", lazy="select"
    )
    protocol: Mapped[Protocol | None] = relationship(
        "Protocol", back_populates="knowledge_documents", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<KnowledgeDocument id={self.id} title={self.title!r} hospital={self.hospital_id}>"
