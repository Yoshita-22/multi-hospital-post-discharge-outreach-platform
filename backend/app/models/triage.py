from __future__ import annotations

import enum
import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, Float, Integer, Boolean, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.models.base import TimestampMixin

class TriageResult(Base, TimestampMixin):
    __tablename__ = "triage_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("outbound_calls.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    campaign_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    
    triage_level: Mapped[str] = mapped_column(String(50), nullable=False) # URGENT, ATTENTION, ROUTINE
    recommended_action: Mapped[str] = mapped_column(String(100), nullable=False)
    
    findings: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    red_flags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    matched_protocol_rules: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    
    reasoning_summary: Mapped[str] = mapped_column(Text, nullable=False)
    agent_assessments: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=False)
    
    consensus_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    consensus_method: Mapped[str | None] = mapped_column(String(100), nullable=True)
    disagreement_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    ehr_action_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    protocol_name: Mapped[str] = mapped_column(String(255), nullable=False)
    protocol_version: Mapped[str] = mapped_column(String(50), nullable=False)
