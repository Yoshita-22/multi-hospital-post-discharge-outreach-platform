import logging
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.schemas.conversation import ConversationResult
from app.models.triage import TriageResult
from app.models.campaign import Campaign
from app.models.ehr import Patient
from app.models.protocol import Protocol
from app.core.tenant_context import TenantContext

from .agents import FindingsAssessmentAgent, ProtocolAssessmentAgent, SafetyAssessmentAgent
from .consensus import ConsensusEngine
from .safety_engine import SafetyRuleEngine
from .escalation import EscalationService

logger = logging.getLogger(__name__)

class TriageOrchestrator:
    def __init__(self):
        self.findings_agent = FindingsAssessmentAgent()
        self.protocol_agent = ProtocolAssessmentAgent()
        self.safety_agent = SafetyAssessmentAgent()
        self.consensus_engine = ConsensusEngine()
        self.safety_engine = SafetyRuleEngine()
        self.escalation_service = EscalationService()

    async def process(self, result: ConversationResult, db: AsyncSession, tenant: TenantContext) -> dict:
        logger.info(f"Starting TriageOrchestrator for Call ID {result.call_id}")
        
        # 1. Fetch Context
        stmt = select(Patient).where(Patient.id == result.patient_id)
        pat_res = await db.execute(stmt)
        patient = pat_res.scalars().first()
        
        stmt_camp = select(Campaign).options(selectinload(Campaign.protocol)).where(Campaign.id == result.campaign_id)
        camp_res = await db.execute(stmt_camp)
        campaign = camp_res.scalars().first()
        
        protocol = campaign.protocol
        protocol_rules = protocol.clinical_rules if protocol else []
        patient_info = f"{patient.first_name} {patient.last_name}"
        
        # 2. Run Agents
        findings = await self.findings_agent.analyze(result, patient_info)
        protocol_assessment = await self.protocol_agent.analyze(findings, protocol_rules)
        safety = await self.safety_agent.analyze(result, findings)
        
        # 3. Consensus Engine
        consensus = self.consensus_engine.compute_consensus(findings, protocol_assessment, safety)
        
        # 4. Safety Rule Engine
        safety_eval = self.safety_engine.evaluate(consensus, protocol_rules)
        
        # 5. DB Persistence
        triage_record = TriageResult(
            call_id=result.call_id,
            patient_id=result.patient_id,
            campaign_id=result.campaign_id,
            triage_level=safety_eval.final_level,
            recommended_action=safety_eval.recommended_action,
            findings=[f.model_dump() for f in findings.findings],
            red_flags=[rf.model_dump() for rf in safety.red_flags],
            matched_protocol_rules=[r.model_dump() for r in protocol_assessment.matched_rules],
            reasoning_summary=consensus.reasoning,
            agent_assessments=[
                findings.model_dump(),
                protocol_assessment.model_dump(),
                safety.model_dump()
            ],
            requires_human_review=safety_eval.requires_human_review,
            consensus_level=consensus.consensus_level,
            consensus_method=consensus.consensus_method,
            disagreement_detected=consensus.disagreement_detected,
            protocol_name=protocol.name if protocol else "Default",
            protocol_version=protocol.version if protocol else "1.0"
        )
        
        db.add(triage_record)
        await db.commit()
        await db.refresh(triage_record)
        
        # 6. Escalation Service
        ehr_result = await self.escalation_service.escalate(db, triage_record, tenant)
        triage_record.ehr_action_status = ehr_result["status"]
        await db.commit()
        
        logger.info(f"Triage Orchestrator completed for Call {result.call_id} -> {safety_eval.final_level}")
        
        return {
            "call_id": str(result.call_id),
            "patient_id": str(result.patient_id),
            "campaign_id": str(result.campaign_id),
            "conversation_result": result.model_dump(mode='json'),
            "triage": {
                "triage_level": safety_eval.final_level,
                "recommended_action": safety_eval.recommended_action,
                "requires_human_review": safety_eval.requires_human_review,
                "consensus_level": consensus.consensus_level,
                "disagreement_detected": consensus.disagreement_detected
            },
            "agent_assessments": [
                findings.model_dump(),
                protocol_assessment.model_dump(),
                safety.model_dump()
            ],
            "matched_protocol_rules": [r.model_dump() for r in protocol_assessment.matched_rules],
            "escalation": {
                "required": safety_eval.requires_human_review,
                "type": safety_eval.recommended_action,
                "status": "CREATED" if ehr_result["status"] == "SUCCESS" else "FAILED"
            },
            "ehr": ehr_result
        }
