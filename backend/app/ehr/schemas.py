from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import date, datetime
import uuid


class EHRBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Patient ---

class PatientName(EHRBaseModel):
    given: List[str]
    family: str


class PatientSchema(EHRBaseModel):
    resourceType: str = "Patient"
    id: str
    hospital_id: str
    name: List[PatientName]
    gender: Optional[str] = None
    birthDate: Optional[date] = None
    telecom: Optional[List[dict]] = None  # e.g. {"system": "phone", "value": "123"}


# --- Encounter ---

class EncounterSchema(EHRBaseModel):
    resourceType: str = "Encounter"
    id: str
    hospital_id: str
    patient_id: str
    status: Optional[str] = None
    class_: Optional[dict] = Field(default=None, alias="class") # care_setting
    type: Optional[List[dict]] = None
    period: Optional[dict] = None # start and end


# --- Discharge (Extension to Encounter/Separate) ---

class DischargeSchema(EHRBaseModel):
    resourceType: str = "Discharge"
    id: str
    hospital_id: str
    patient_id: str
    encounter_id: str
    discharge_timestamp: datetime
    discharge_status: Optional[str] = None
    discharge_instructions: Optional[str] = None
    follow_up_required: bool
    follow_up_start: Optional[datetime] = None
    follow_up_deadline: Optional[datetime] = None
    risk_level: Optional[str] = None
    risk_indicators: Optional[list] = None


# --- Condition ---

class ConditionSchema(EHRBaseModel):
    resourceType: str = "Condition"
    id: str
    hospital_id: str
    patient_id: str
    encounter_id: Optional[str] = None
    clinicalStatus: Optional[dict] = None
    code: Optional[dict] = None
    onsetDateTime: Optional[datetime] = None


# --- Medication ---

class MedicationSchema(EHRBaseModel):
    resourceType: str = "Medication"
    id: str
    hospital_id: str
    patient_id: str
    encounter_id: Optional[str] = None
    code: Optional[dict] = None # name
    status: Optional[str] = None
    dosageInstruction: Optional[List[dict]] = None
    effectivePeriod: Optional[dict] = None


# --- Observation ---

class ObservationSchema(EHRBaseModel):
    resourceType: str = "Observation"
    id: str
    hospital_id: str
    patient_id: str
    encounter_id: Optional[str] = None
    status: Optional[str] = None
    code: Optional[dict] = None
    valueQuantity: Optional[dict] = None
    effectiveDateTime: Optional[datetime] = None


# --- CarePlan ---

class CarePlanSchema(EHRBaseModel):
    resourceType: str = "CarePlan"
    id: str
    hospital_id: str
    patient_id: str
    encounter_id: Optional[str] = None
    status: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    period: Optional[dict] = None


# --- Communication ---

class CommunicationCreate(EHRBaseModel):
    communication_type: str
    content: str

class CommunicationSchema(EHRBaseModel):
    resourceType: str = "Communication"
    id: str
    hospital_id: str
    patient_id: str
    encounter_id: Optional[str] = None
    status: str = "completed"
    category: Optional[List[dict]] = None
    payload: Optional[List[dict]] = None
    sent: Optional[datetime] = None


# --- Task ---

class TaskCreate(EHRBaseModel):
    task_type: str
    description: str
    due_at: Optional[datetime] = None

class TaskSchema(EHRBaseModel):
    resourceType: str = "Task"
    id: str
    hospital_id: str
    patient_id: str
    encounter_id: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    executionPeriod: Optional[dict] = None


class EncounterUpdate(EHRBaseModel):
    status: Optional[str] = None
    care_setting: Optional[str] = None


class OutreachOutcomeCreate(EHRBaseModel):
    outcome_status: str
    notes: Optional[str] = None

class ObservationCreate(EHRBaseModel):
    code: str
    display: str
    value: str
    unit: str
    status: str = "final"
