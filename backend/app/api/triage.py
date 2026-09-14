import uuid
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.dependencies import get_db, get_current_user
from app.core.tenant_context import TenantContext, UserRole
from app.models.campaign import Campaign
from app.models.ehr import Patient
from app.models.outbound_call import OutboundCall
from app.schemas.conversation import ConversationResult, ConversationOutcome
from app.schemas.triage import MockTriageRequest
from app.services.triage.orchestrator import TriageOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/triage", tags=["Triage"])
orchestrator = TriageOrchestrator()

@router.post("/mock-run")
async def run_mock_triage(
    request: MockTriageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    tenant = TenantContext(user_id=uuid.UUID(current_user["sub"]), hospital_id=uuid.UUID(current_user["hospital_id"]), role=UserRole(current_user["role"]))
    
    # Get a valid patient and campaign for the tenant
    stmt_camp = select(Campaign).where(Campaign.hospital_id == tenant.hospital_id).limit(1)
    campaign = (await db.execute(stmt_camp)).scalars().first()
    
    stmt_pat = select(Patient).where(Patient.hospital_id == tenant.hospital_id).limit(1)
    patient = (await db.execute(stmt_pat)).scalars().first()
    
    if not campaign or not patient:
        raise HTTPException(status_code=400, detail="No campaign or patient found for this hospital. Generate mock data first.")
        
    call_id = uuid.UUID(request.call_id) if request.call_id else uuid.uuid4()
    
    # Save a mock outbound call if one doesn't exist
    if not request.call_id:
        call = OutboundCall(
            id=call_id,
            campaign_id=campaign.id,
            patient_id=patient.id,
            outcome="COMPLETED",
            patient_reached=True,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc)
        )
        db.add(call)
        await db.commit()
        await db.refresh(call)

    # Build the mock ConversationResult
    if request.scenario == "urgent":
        summary = "Patient reported severe chest pain and difficulty breathing."
        responses = {"recovery": "I am not doing well.", "symptoms": "I have severe chest pain."}
        symptoms = [{"symptom": "chest pain", "severity": "severe"}]
    elif request.scenario == "attention":
        summary = "Patient reported increased ankle swelling over the last two days."
        responses = {"recovery": "Mostly okay.", "symptoms": "My ankles have become more swollen."}
        symptoms = [{"symptom": "ankle swelling", "severity": "mild", "worsening": True}]
    else:
        summary = "Routine follow-up completed. Patient feeling well."
        responses = {"recovery": "I am feeling well and recovering normally."}
        symptoms = []

    convo_result = ConversationResult(
        call_id=call_id,
        patient_id=patient.id,
        campaign_id=campaign.id,
        outcome=ConversationOutcome.COMPLETED,
        patient_reached=True,
        responses=responses,
        symptoms_reported=symptoms,
        transcript=[{"role": "ai", "text": "Hello"}, {"role": "patient", "text": summary}],
        summary=summary,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc)
    )

    # Run Triage Orchestrator
    try:
        triage_output = await orchestrator.process(convo_result, db, tenant)
        return triage_output
    except Exception as e:
        logger.error(f"Mock triage failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
