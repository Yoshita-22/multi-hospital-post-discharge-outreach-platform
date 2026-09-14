import logging
import uuid
from typing import Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_db
from app.models.outbound_call import OutboundCall
from app.models.campaign import Campaign
from app.models.ehr import Patient, Condition, Medication
from app.models.protocol import Protocol
from app.schemas.conversation import (
    PatientContext,
    OutreachContext,
    ProtocolContext,
    ConversationResult
)
from app.services.triage_service import TriageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["Voice"])

@router.get("/sessions/{call_id}")
async def get_session_context(call_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Called by the TypeScript LiveKit Agent to get the context for a call.
    """
    stmt = select(OutboundCall).where(OutboundCall.id == call_id)
    result = await db.execute(stmt)
    call = result.scalars().first()
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
        
    # Get Patient with conditions and medications
    stmt_patient = select(Patient).where(Patient.id == call.patient_id)
    result_patient = await db.execute(stmt_patient)
    patient = result_patient.scalars().first()
    
    stmt_conditions = select(Condition).where(Condition.patient_id == patient.id)
    result_conditions = await db.execute(stmt_conditions)
    conditions = [c.display for c in result_conditions.scalars().all() if c.display]
    
    stmt_meds = select(Medication).where(Medication.patient_id == patient.id)
    result_meds = await db.execute(stmt_meds)
    medications = [m.name for m in result_meds.scalars().all()]
    
    patient_ctx = PatientContext(
        patient_id=patient.id,
        patient_name=f"{patient.first_name} {patient.last_name}",
        preferred_language=patient.preferred_language if hasattr(patient, 'preferred_language') else "en",
        conditions=conditions,
        medications=medications
    )
    
    # Get Campaign and Protocol
    stmt_camp = select(Campaign).options(selectinload(Campaign.protocol)).where(Campaign.id == call.campaign_id)
    result_camp = await db.execute(stmt_camp)
    campaign = result_camp.scalars().first()
    
    outreach_ctx = OutreachContext(
        call_id=call.id,
        campaign_id=campaign.id,
        campaign_name=campaign.name,
        outreach_purpose=campaign.description or "Hospital Follow-up",
        attempt_number=1,
        days_since_discharge=0
    )
    
    protocol_ctx = ProtocolContext(
        protocol_name=campaign.protocol.name if campaign.protocol else "Default Protocol",
        version="1.0",
        questions=campaign.protocol.questions if campaign.protocol else []
    )
    
    return {
        "patient": patient_ctx.model_dump(),
        "outreach": outreach_ctx.model_dump(),
        "protocol": protocol_ctx.model_dump()
    }

from app.core.tenant_context import TenantContext, UserRole
from app.services.triage.orchestrator import TriageOrchestrator

orchestrator = TriageOrchestrator()

@router.post("/sessions/{call_id}/complete")
async def complete_session(call_id: uuid.UUID, result_payload: ConversationResult, db: AsyncSession = Depends(get_db)):
    """
    Called by the TypeScript agent when the conversation ends.
    """
    stmt = select(OutboundCall).options(selectinload(OutboundCall.campaign)).where(OutboundCall.id == call_id)
    result = await db.execute(stmt)
    call = result.scalars().first()
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
        
    call.outcome = result_payload.outcome.value
    call.patient_reached = result_payload.patient_reached
    call.responses = result_payload.responses
    call.symptoms_reported = result_payload.symptoms_reported
    call.uncertainties = result_payload.uncertainties
    call.callback_requested = result_payload.callback_requested
    call.callback_time = result_payload.callback_time
    call.transcript = result_payload.transcript
    call.summary = result_payload.summary
    call.completed_at = datetime.now(timezone.utc)
    
    await db.commit()
    
    # Override the IDs in case the mocked frontend payload doesn't have them
    result_payload.patient_id = call.patient_id
    result_payload.campaign_id = call.campaign_id

    # Create a system TenantContext since this is coming from the AI agent worker
    tenant = TenantContext(user_id=uuid.uuid4(), hospital_id=call.campaign.hospital_id, role=UserRole.PLATFORM_ADMIN)

    # Invoke Triage Orchestrator asynchronously
    res = await orchestrator.process(result_payload, db, tenant)
    
    return {"status": "success", "triage": res}
