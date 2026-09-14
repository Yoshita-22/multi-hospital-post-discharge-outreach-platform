from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal
from datetime import datetime

class FindingInfo(BaseModel):
    finding: str = Field(description="The extracted medical finding or symptom")
    evidence: str = Field(description="The patient's quote or text from transcript supporting this")

class RedFlagInfo(BaseModel):
    name: str = Field(description="The name of the red flag")
    evidence: str = Field(description="The evidence for this red flag")

class MatchedRuleInfo(BaseModel):
    rule_id: str
    name: str
    evidence: str

class FindingsAssessment(BaseModel):
    agent: str = "findings_assessment"
    assessment_level: Literal["URGENT", "ATTENTION", "ROUTINE"]
    findings: List[FindingInfo] = Field(default_factory=list)
    red_flags: List[RedFlagInfo] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)
    confidence: float
    reasoning: str

class ProtocolAssessment(BaseModel):
    agent: str = "protocol_assessment"
    assessment_level: Literal["URGENT", "ATTENTION", "ROUTINE"]
    matched_rules: List[MatchedRuleInfo] = Field(default_factory=list)
    red_flags: List[RedFlagInfo] = Field(default_factory=list)
    requires_human_review: bool
    recommended_action: str
    confidence: float

class SafetyAssessment(BaseModel):
    agent: str = "safety_assessment"
    assessment_level: Literal["URGENT", "ATTENTION", "ROUTINE"]
    red_flags: List[RedFlagInfo] = Field(default_factory=list)
    requires_human_review: bool
    recommended_action: str
    confidence: float

class AgentLevels(BaseModel):
    findings_assessment: str
    protocol_assessment: str
    safety_assessment: str

class ConsensusResult(BaseModel):
    consensus_level: Literal["URGENT", "ATTENTION", "ROUTINE"]
    consensus_method: str
    agent_levels: AgentLevels
    disagreement_detected: bool
    requires_human_review: bool
    reasoning: str
    evidence: List[str] = Field(default_factory=list)

class MockTriageRequest(BaseModel):
    scenario: Literal["routine", "attention", "urgent"]
    call_id: Optional[str] = None
