from app.schemas.triage import (
    FindingsAssessment,
    ProtocolAssessment,
    SafetyAssessment,
    ConsensusResult,
    AgentLevels
)

class ConsensusEngine:
    def compute_consensus(
        self,
        findings: FindingsAssessment,
        protocol: ProtocolAssessment,
        safety: SafetyAssessment
    ) -> ConsensusResult:
        
        levels = [findings.assessment_level, protocol.assessment_level, safety.assessment_level]
        
        has_urgent = "URGENT" in levels
        has_attention = "ATTENTION" in levels
        
        disagreement_detected = len(set(levels)) > 1
        
        if has_urgent:
            final_level = "URGENT"
        elif has_attention:
            final_level = "ATTENTION"
        else:
            final_level = "ROUTINE"
            
        requires_human_review = final_level != "ROUTINE" or disagreement_detected or protocol.requires_human_review or safety.requires_human_review
        
        reasoning = f"Findings: {findings.assessment_level}, Protocol: {protocol.assessment_level}, Safety: {safety.assessment_level}."
        if disagreement_detected:
            reasoning += " Disagreement detected; falling back to highest severity."
            
        evidence = []
        for agent in [findings, protocol, safety]:
            for rf in getattr(agent, "red_flags", []):
                evidence.append(f"{agent.agent} Red Flag: {rf.name}")
        
        return ConsensusResult(
            consensus_level=final_level,
            consensus_method="deterministic_highest_severity",
            agent_levels=AgentLevels(
                findings_assessment=findings.assessment_level,
                protocol_assessment=protocol.assessment_level,
                safety_assessment=safety.assessment_level
            ),
            disagreement_detected=disagreement_detected,
            requires_human_review=requires_human_review,
            reasoning=reasoning,
            evidence=evidence
        )
