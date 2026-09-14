import uuid
from datetime import datetime

from sqlalchemy import String, ForeignKey, DateTime, Text, UniqueConstraint
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
    
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint('campaign_id', 'patient_id', name='uq_campaign_patient'),
    )
