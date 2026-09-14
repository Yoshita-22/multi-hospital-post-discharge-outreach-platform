import uuid
from datetime import date, datetime
from sqlalchemy import (
    String,
    DateTime,
    Date,
    ForeignKey,
    JSON,
    Index,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.base import TimestampMixin


class Patient(Base, TimestampMixin):
    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False)
    external_patient_id: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[str] = mapped_column(String(255), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[str | None] = mapped_column(String(50))
    phone: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(255))
    preferred_contact_method: Mapped[str | None] = mapped_column(String(50))

    __table_args__ = (
        Index("ix_patients_hospital_id", "hospital_id"),
    )


class Encounter(Base, TimestampMixin):
    __tablename__ = "encounters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    external_encounter_id: Mapped[str | None] = mapped_column(String(255))
    encounter_type: Mapped[str | None] = mapped_column(String(100))
    care_setting: Mapped[str | None] = mapped_column(String(100))
    admission_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    discharge_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str | None] = mapped_column(String(50))

    __table_args__ = (
        Index("ix_encounters_hospital_id_patient_id", "hospital_id", "patient_id"),
    )


class Discharge(Base, TimestampMixin):
    __tablename__ = "discharges"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    encounter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False)
    
    discharge_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    discharge_status: Mapped[str | None] = mapped_column(String(100))
    discharge_instructions: Mapped[str | None] = mapped_column(Text)
    
    follow_up_required: Mapped[bool] = mapped_column(default=False)
    follow_up_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    follow_up_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    risk_level: Mapped[str | None] = mapped_column(String(50))
    risk_indicators: Mapped[list | None] = mapped_column(JSONB)

    __table_args__ = (
        Index("ix_discharges_hospital_id_patient_id", "hospital_id", "patient_id"),
        Index("ix_discharges_encounter_id", "encounter_id"),
    )


class Condition(Base, TimestampMixin):
    __tablename__ = "conditions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("encounters.id", ondelete="CASCADE"))
    
    code: Mapped[str | None] = mapped_column(String(100))
    display: Mapped[str | None] = mapped_column(String(255))
    clinical_status: Mapped[str | None] = mapped_column(String(50))
    onset_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_conditions_hospital_id_patient_id", "hospital_id", "patient_id"),
    )


class Medication(Base, TimestampMixin):
    __tablename__ = "medications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("encounters.id", ondelete="CASCADE"))
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    dosage: Mapped[str | None] = mapped_column(String(255))
    route: Mapped[str | None] = mapped_column(String(100))
    frequency: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str | None] = mapped_column(String(50))
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_medications_hospital_id_patient_id", "hospital_id", "patient_id"),
    )


class Observation(Base, TimestampMixin):
    __tablename__ = "observations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("encounters.id", ondelete="CASCADE"))
    
    code: Mapped[str | None] = mapped_column(String(100))
    display: Mapped[str | None] = mapped_column(String(255))
    value: Mapped[str | None] = mapped_column(String(255))
    unit: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str | None] = mapped_column(String(50))
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_observations_hospital_id_patient_id", "hospital_id", "patient_id"),
    )


class CarePlan(Base, TimestampMixin):
    __tablename__ = "care_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("encounters.id", ondelete="CASCADE"))
    
    title: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(String(50))
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_care_plans_hospital_id_patient_id", "hospital_id", "patient_id"),
    )


class Communication(Base, TimestampMixin):
    __tablename__ = "communications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("encounters.id", ondelete="CASCADE"))
    
    communication_type: Mapped[str | None] = mapped_column(String(100))
    content: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("ix_communications_hospital_id_patient_id", "hospital_id", "patient_id"),
    )


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("encounters.id", ondelete="CASCADE"))
    
    task_type: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_tasks_hospital_id_patient_id", "hospital_id", "patient_id"),
    )
