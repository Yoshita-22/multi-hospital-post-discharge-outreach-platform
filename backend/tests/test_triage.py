import pytest
import uuid
import os
from datetime import datetime, timezone, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.schemas.conversation import ConversationResult, ConversationOutcome
from app.models.triage import TriageResult
from app.models.outbound_call import OutboundCall
from app.models.campaign import Campaign, CampaignStatus
from app.models.ehr import Patient
from app.models.protocol import Protocol
from app.core.tenant_context import TenantContext, UserRole
from app.models.user import User, UserStatus
from app.services.triage.orchestrator import TriageOrchestrator

os.environ["TRIAGE_MODE"] = "mock"

async def create_test_patient(db: AsyncSession, hospital_id: uuid.UUID) -> Patient:
    p = Patient(
        id=uuid.uuid4(),
        hospital_id=hospital_id,
        external_patient_id=f"TEST-PAT-{uuid.uuid4().hex[:6]}",
        first_name="Test",
        last_name="Patient",
        date_of_birth=date(1990, 1, 1),
        phone="555-555-5555"
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p

async def create_test_campaign(db: AsyncSession, hospital_id: uuid.UUID) -> Campaign:
    prot = Protocol(
        id=uuid.uuid4(),
        hospital_id=hospital_id,
        name="Test Protocol",
        version="1.0",
        content={},
        clinical_rules=[]
    )
    db.add(prot)
    
    c = Campaign(
        id=uuid.uuid4(),
        hospital_id=hospital_id,
        name="Test Campaign",
        status=CampaignStatus.RUNNING,
        protocol_id=prot.id
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c

import pytest_asyncio

@pytest_asyncio.fixture
async def mock_convo_data(db, hospital_a):
    patient = await create_test_patient(db, hospital_a.id)
    campaign = await create_test_campaign(db, hospital_a.id)
    
    call_id = uuid.uuid4()
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
    
    convo = ConversationResult(
        call_id=call_id,
        patient_id=patient.id,
        campaign_id=campaign.id,
        outcome=ConversationOutcome.COMPLETED,
        patient_reached=True,
        responses={},
        transcript=[],
        summary="",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc)
    )
    
    # Create User for TenantContext
    u = User(
        id=uuid.uuid4(),
        hospital_id=hospital_a.id,
        name="Test User",
        email=f"test_{uuid.uuid4().hex[:6]}@example.com",
        password_hash="fake",
        role=UserRole.HOSPITAL_ADMIN,
        status=UserStatus.ACTIVE
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    
    yield convo, patient, campaign, u

@pytest.mark.asyncio
async def test_triage_routine(db: AsyncSession, mock_convo_data):
    convo, patient, campaign, user = mock_convo_data
    convo.summary = "Routine checkup, no issues."
    
    tenant = TenantContext(user_id=user.id, hospital_id=campaign.hospital_id, role=UserRole.HOSPITAL_ADMIN)
    orchestrator = TriageOrchestrator()
    
    res = await orchestrator.process(convo, db, tenant)
    
    assert res["triage"]["triage_level"] == "ROUTINE"
    assert res["triage"]["recommended_action"] == "NO_ACTION_REQUIRED"
    assert res["triage"]["consensus_level"] == "ROUTINE"

@pytest.mark.asyncio
async def test_triage_attention(db: AsyncSession, mock_convo_data):
    convo, patient, campaign, user = mock_convo_data
    convo.summary = "Patient reported worsening ankle swelling."
    
    tenant = TenantContext(user_id=user.id, hospital_id=campaign.hospital_id, role=UserRole.HOSPITAL_ADMIN)
    orchestrator = TriageOrchestrator()
    
    res = await orchestrator.process(convo, db, tenant)
    
    assert res["triage"]["triage_level"] == "ATTENTION"
    assert res["triage"]["recommended_action"] == "CLINICIAN_REVIEW"

@pytest.mark.asyncio
async def test_triage_urgent(db: AsyncSession, mock_convo_data):
    convo, patient, campaign, user = mock_convo_data
    convo.summary = "Patient reported severe chest pain."
    
    tenant = TenantContext(user_id=user.id, hospital_id=campaign.hospital_id, role=UserRole.HOSPITAL_ADMIN)
    orchestrator = TriageOrchestrator()
    
    res = await orchestrator.process(convo, db, tenant)
    
    assert res["triage"]["triage_level"] == "URGENT"
    assert res["triage"]["recommended_action"] == "IMMEDIATE_CLINICIAN_REVIEW"

@pytest.mark.asyncio
async def test_triage_tenant_isolation(db: AsyncSession, mock_convo_data):
    from tests.test_triage import create_test_hospital
    convo, patient, campaign, user = mock_convo_data
    
    # Try with wrong hospital
    wrong_hospital = await create_test_hospital(db)
    tenant = TenantContext(user_id=user.id, hospital_id=wrong_hospital.id, role=UserRole.HOSPITAL_ADMIN)
    
    orchestrator = TriageOrchestrator()
    
    # It should not find the campaign since it belongs to a different hospital
    try:
        await orchestrator.process(convo, db, tenant)
        assert False, "Should have failed due to tenant isolation"
    except Exception as e:
        assert "Campaign not found" in str(e) or "Tenant mismatch" in str(e) or "Triage Orchestrator failed" in str(e) or "not found" in str(e)
