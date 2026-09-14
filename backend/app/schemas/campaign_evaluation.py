import uuid
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class ValidationErrorDetail(BaseModel):
    field: str
    message: str

class ValidationResult(BaseModel):
    campaign_id: uuid.UUID
    valid: bool
    errors: List[ValidationErrorDetail] = []
    warnings: List[str] = []

class EligiblePatientDetail(BaseModel):
    patient_id: uuid.UUID
    external_patient_id: Optional[str] = None
    risk_level: Optional[str] = None
    matched_rules: List[str]

class EligibilityResult(BaseModel):
    campaign_id: uuid.UUID
    evaluated_count: int
    eligible_count: int
    evaluation_timestamp: str
    patients: List[EligiblePatientDetail]
