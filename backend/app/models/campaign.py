import enum
import uuid
from datetime import datetime
from typing import Optional, Any, Dict

from sqlalchemy import String, ForeignKey, DateTime, Integer, Enum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampMixin
from app.db.database import Base


class CampaignStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    READY = "READY"
    SCHEDULED = "SCHEDULED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class CampaignValidationStatus(str, enum.Enum):
    NOT_VALIDATED = "NOT_VALIDATED"
    VALID = "VALID"
    INVALID = "INVALID"



class Campaign(Base, TimestampMixin):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    hospital_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hospitals.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus, name="campaignstatus_enum", create_type=True),
        nullable=False,
        default=CampaignStatus.DRAFT,
        index=True
    )
    
    validation_status: Mapped[CampaignValidationStatus] = mapped_column(
        Enum(CampaignValidationStatus, name="campaignvalidationstatus_enum", create_type=True),
        nullable=False,
        default=CampaignValidationStatus.NOT_VALIDATED
    )
    
    eligibility_rules: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    follow_up_window: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    calling_hours: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    priority_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    calling_capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    
    start_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    end_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    hospital: Mapped["Hospital"] = relationship("Hospital", foreign_keys=[hospital_id])
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])
