from app.schemas.triage import ConsensusResult
from pydantic import BaseModel

class SafetyRuleResult(BaseModel):
    final_level: str
    requires_human_review: bool
    recommended_action: str
    safety_override_applied: bool

class SafetyRuleEngine:
    def evaluate(self, consensus: ConsensusResult, clinical_rules: list) -> SafetyRuleResult:
        override_applied = False
        final_level = consensus.consensus_level
        
        if final_level == "URGENT":
            recommended_action = "IMMEDIATE_CLINICIAN_REVIEW"
            requires_human_review = True
        elif final_level == "ATTENTION":
            recommended_action = "CLINICIAN_REVIEW"
            requires_human_review = True
        else:
            recommended_action = "NO_ACTION_REQUIRED"
            requires_human_review = False
            
        return SafetyRuleResult(
            final_level=final_level,
            requires_human_review=requires_human_review or consensus.requires_human_review,
            recommended_action=recommended_action,
            safety_override_applied=override_applied
        )
