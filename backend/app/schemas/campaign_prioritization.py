import uuid
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class PatientPriorityFactors(BaseModel):
    clinical_risk: float
    follow_up_urgency: float
    time_since_discharge: float
    callback_request: float
    outreach_history: float
    campaign_priority: float

class PrioritizedPatientDetail(BaseModel):
    patient_id: uuid.UUID
    priority_score: float
    priority_level: str
    priority_rank: int
    factors: PatientPriorityFactors

class PrioritizationResult(BaseModel):
    campaign_id: uuid.UUID
    prioritized_count: int
    high_priority_count: int
    medium_priority_count: int
    low_priority_count: int
    prioritized_at: str
