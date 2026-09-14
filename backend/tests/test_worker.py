import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.outbound_queue import OutboundQueue, QueueItemStatus
from app.models.campaign import Campaign, CampaignStatus, CampaignValidationStatus
from app.models.hospital import Hospital, HospitalStatus
from app.models.ehr import Patient
from app.services.call_worker import call_worker
from app.services.voice_call_provider import MockVoiceCallProvider

pytestmark = pytest.mark.asyncio


from app.schemas.conversation import PatientContext, OutreachContext, ProtocolContext, ConversationResult, ConversationOutcome

class PredictableVoiceCallProvider(MockVoiceCallProvider):
    def __init__(self, outcome: ConversationOutcome):
        self.outcome = outcome
        
    async def start_call(self, patient_ctx: PatientContext, outreach_ctx: OutreachContext, protocol_ctx: ProtocolContext) -> ConversationResult:
        return ConversationResult(
            call_id=outreach_ctx.call_id,
            patient_id=patient_ctx.patient_id,
            campaign_id=outreach_ctx.campaign_id,
            outcome=self.outcome,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc)
        )


async def setup_test_queue_item(db: AsyncSession, status: QueueItemStatus = QueueItemStatus.CLAIMED):
    # Create hospital
    h_id = uuid.uuid4()
    hospital = Hospital(id=h_id, name="Worker Test", status=HospitalStatus.ONBOARDING, contact_email="test@example.com", contact_phone="+1234567890", timezone="UTC")
    db.add(hospital)
    await db.flush()
    
    # Create campaign
    c_id = uuid.uuid4()
    camp = Campaign(
        id=c_id, hospital_id=h_id, name="Test Camp",
        status=CampaignStatus.RUNNING, validation_status=CampaignValidationStatus.VALID,
        max_retries=3
    )
    db.add(camp)
    await db.flush()
    
    # Create patient
    p_id = uuid.uuid4()
    pat = Patient(id=p_id, hospital_id=h_id, external_patient_id=f"MRN-{p_id}", first_name="John", last_name="Doe", date_of_birth=datetime(1990, 1, 1).date())
    db.add(pat)
    
    # Create queue item
    q_id = uuid.uuid4()
    item = OutboundQueue(
        id=q_id, campaign_id=c_id, patient_id=p_id, hospital_id=h_id,
        status=status, priority_score=0.9, priority_level="HIGH", priority_rank=1,
        scheduled_at=datetime.now(timezone.utc),
        max_attempts=3, attempt_count=0
    )
    db.add(item)
    await db.commit()
    
    return q_id


async def test_worker_success(db: AsyncSession):
    q_id = await setup_test_queue_item(db)
    
    # Inject predictable provider
    call_worker.provider = PredictableVoiceCallProvider(ConversationOutcome.COMPLETED)
    
    await call_worker.execute(q_id)
    
    # Assert
    res = await db.execute(select(OutboundQueue).where(OutboundQueue.id == q_id))
    item = res.scalar_one()
    
    assert item.status == QueueItemStatus.COMPLETED
    assert item.attempt_count == 1


async def test_worker_retry(db: AsyncSession):
    q_id = await setup_test_queue_item(db)
    
    # Inject predictable provider
    call_worker.provider = PredictableVoiceCallProvider(ConversationOutcome.NO_ANSWER)
    
    await call_worker.execute(q_id)
    
    # Assert
    res = await db.execute(select(OutboundQueue).where(OutboundQueue.id == q_id))
    item = res.scalar_one()
    
    assert item.status == QueueItemStatus.RETRY_PENDING
    assert item.attempt_count == 1
    assert item.next_attempt_at is not None


async def test_worker_exhausted_retries(db: AsyncSession):
    q_id = await setup_test_queue_item(db)
    
    # Setup exhausted max attempts
    res = await db.execute(select(OutboundQueue).where(OutboundQueue.id == q_id))
    item = res.scalar_one()
    item.attempt_count = 2 # Next attempt is 3, hitting the max
    await db.commit()
    
    # Inject predictable provider
    call_worker.provider = PredictableVoiceCallProvider(ConversationOutcome.NO_ANSWER)
    
    await call_worker.execute(q_id)
    
    # Assert
    res = await db.execute(select(OutboundQueue).where(OutboundQueue.id == q_id))
    item = res.scalar_one()
    
    assert item.status == QueueItemStatus.FAILED
    assert item.attempt_count == 3

