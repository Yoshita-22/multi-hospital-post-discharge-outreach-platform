from __future__ import annotations

import enum
import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, Float, Integer, Boolean, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.models.base import TimestampMixin
from app.schemas.conversation import ConversationOutcome

class OutboundCall(Base, TimestampMixin):
    __tablename__ = "outbound_calls"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Store the actual enum value from schemas as string in DB
    outcome: Mapped[str] = mapped_column(String(50), nullable=False)
    
    patient_reached: Mapped[bool] = mapped_column(Boolean, default=False)
    
    responses: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    symptoms_reported: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    uncertainties: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    
    callback_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    callback_time: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    transcript: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
