import enum
import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, Integer, Enum, Float, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampMixin
from app.db.database import Base

class QueueItemStatus(str, enum.Enum):
    PENDING = "PENDING"
    CLAIMED = "CLAIMED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class OutboundQueue(Base, TimestampMixin):
    __tablename__ = "outbound_queue"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True, nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True, nullable=False)
    hospital_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hospitals.id", ondelete="CASCADE"), index=True, nullable=False)
    
    priority_score: Mapped[float] = mapped_column(Float, nullable=False)
    priority_level: Mapped[str] = mapped_column(String(50), nullable=False)
    priority_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    
    status: Mapped[QueueItemStatus] = mapped_column(
        Enum(QueueItemStatus, name="queueitemstatus_enum", create_type=True),
        nullable=False,
        default=QueueItemStatus.PENDING,
        index=True
    )
    
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint('campaign_id', 'patient_id', name='uq_outbound_queue_campaign_patient'),
    )
