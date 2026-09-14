import uuid
from datetime import datetime

from sqlalchemy import String, ForeignKey, DateTime, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampMixin
from app.db.database import Base


class CampaignPatient(Base, TimestampMixin):
    __tablename__ = "campaign_patients"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True, nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True, nullable=False)
    
    eligibility_status: Mapped[str] = mapped_column(String(50), nullable=False)
    eligibility_reason: Mapped[str] = mapped_column(Text, nullable=True)
    
    priority_score: Mapped[float | None] = mapped_column(nullable=True)
    priority_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    priority_rank: Mapped[int | None] = mapped_column(nullable=True)
    prioritized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    priority_factors: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint('campaign_id', 'patient_id', name='uq_campaign_patient'),
    )
