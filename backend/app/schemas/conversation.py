from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
import uuid
from datetime import datetime

class ConversationStage(str, Enum):
    INTRO = "INTRO"
    VERIFY = "VERIFY"
    PURPOSE = "PURPOSE"
    QUESTIONING = "QUESTIONING"
    CLARIFY = "CLARIFY"
    CALLBACK = "CALLBACK"
    TRANSFER = "TRANSFER"
    COMPLETE = "COMPLETE"
    DECLINED = "DECLINED"
    INTERRUPTED = "INTERRUPTED"

class ConversationAction(str, Enum):
    ASK_QUESTION = "ASK_QUESTION"
    ASK_FOLLOWUP = "ASK_FOLLOWUP"
    CLARIFY = "CLARIFY"
    COMPLETE = "COMPLETE"
    REQUEST_CALLBACK = "REQUEST_CALLBACK"
    TRANSFER = "TRANSFER"
    DECLINED = "DECLINED"
    INTERRUPTED = "INTERRUPTED"

class ConversationOutcome(str, Enum):
    COMPLETED = "COMPLETED"
    CALLBACK_REQUESTED = "CALLBACK_REQUESTED"
    PATIENT_DECLINED = "PATIENT_DECLINED"
    INTERRUPTED = "INTERRUPTED"
    TRANSFERRED = "TRANSFERRED"
    NO_ANSWER = "NO_ANSWER"

# ---------------------------------------------------------
# Agent Inputs / Context
# ---------------------------------------------------------
class PatientContext(BaseModel):
    patient_id: uuid.UUID
    patient_name: str
    preferred_language: Optional[str] = "en"
    conditions: List[str] = []
    medications: List[str] = []
    follow_up_requirements: Optional[str] = None

class OutreachContext(BaseModel):
    call_id: uuid.UUID
    campaign_id: uuid.UUID
    campaign_name: str
    outreach_purpose: str
    attempt_number: int = 1
    days_since_discharge: int = 0

class ProtocolContext(BaseModel):
    protocol_name: str
    version: str
    questions: List[Dict[str, str]] = []

# ---------------------------------------------------------
# LLM Structured Output
# ---------------------------------------------------------
class CallbackInfo(BaseModel):
    requested: bool = False
    requested_time: Optional[str] = None

class ConversationStateUpdate(BaseModel):
    next_stage: ConversationStage
    current_question_id: Optional[str] = None

class CapturedInformation(BaseModel):
    responses: Dict[str, str] = Field(default_factory=dict, description="Answers mapped to question IDs")
    symptoms: List[Dict[str, str]] = Field(default_factory=list, description="Extracted symptoms with details")
    medication_information: Dict[str, str] = Field(default_factory=dict, description="Adherence or missing medication details")
    follow_up_information: Dict[str, str] = Field(default_factory=dict)
    concerns: List[str] = Field(default_factory=list)

class StructuredAgentOutput(BaseModel):
    response: str = Field(description="The exact words the agent should speak next.")
    action: ConversationAction = Field(description="The action the agent is taking.")
    captured_information: CapturedInformation
    uncertainties: List[str] = Field(default_factory=list, description="Any unclear items needing clarification.")
    callback: CallbackInfo = Field(default_factory=CallbackInfo)
    conversation: ConversationStateUpdate

# ---------------------------------------------------------
# Overall Conversation State
# ---------------------------------------------------------
class ConversationState(BaseModel):
    stage: ConversationStage = ConversationStage.INTRO
    current_question_id: Optional[str] = None
    completed_questions: List[str] = []
    remaining_questions: List[str] = []
    transcript: List[Dict[str, str]] = []  # [{"role": "agent"/"patient", "text": "..."}]
    
    # Aggregated
    captured_data: CapturedInformation = Field(default_factory=CapturedInformation)
    clarification_count: int = 0
    callback_requested: bool = False
    callback_time: Optional[str] = None

# ---------------------------------------------------------
# Final Output
# ---------------------------------------------------------
class ConversationResult(BaseModel):
    call_id: uuid.UUID
    patient_id: uuid.UUID
    campaign_id: uuid.UUID
    outcome: ConversationOutcome
    patient_reached: bool = False
    responses: Dict[str, str] = Field(default_factory=dict)
    symptoms_reported: List[Dict[str, str]] = Field(default_factory=list)
    uncertainties: List[str] = Field(default_factory=list)
    callback_requested: bool = False
    callback_time: Optional[str] = None
    transcript: List[Dict[str, str]] = Field(default_factory=list)
    summary: str = ""
    started_at: datetime
    completed_at: datetime
