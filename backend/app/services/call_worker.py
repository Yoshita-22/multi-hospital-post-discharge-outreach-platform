import uuid
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.database import AsyncSessionLocal
from app.models.outbound_queue import OutboundQueue, QueueItemStatus
from app.services.voice_call_provider import MockVoiceCallProvider
from app.ehr.mock_ehr import mock_ehr
from app.models.campaign import Campaign
from app.schemas.conversation import PatientContext, OutreachContext, ProtocolContext, ConversationOutcome
from app.services.outbound_call_service import OutboundCallService
from app.services.triage_service import TriageService

logger = logging.getLogger(__name__)

class CallWorker:
    def __init__(self):
        self.provider = MockVoiceCallProvider()
        
    async def execute(self, queue_id: uuid.UUID):
        """
        Executes a single queue item. Must be called in an async background task.
        """
        logger.info(f"Worker started execution for queue item {queue_id}")
        
        async with AsyncSessionLocal() as db:
            res = await db.execute(select(OutboundQueue).where(OutboundQueue.id == queue_id))
            queue_item = res.scalar_one_or_none()
            
            if not queue_item:
                logger.error(f"Queue item {queue_id} not found.")
                return
                
            if queue_item.status != QueueItemStatus.CLAIMED:
                logger.error(f"Queue item {queue_id} has invalid status {queue_item.status}, expected CLAIMED.")
                return
                
            queue_item.status = QueueItemStatus.IN_PROGRESS
            queue_item.attempt_count += 1
            queue_item.last_attempt_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(queue_item)
            
            logger.info(f"Queue item {queue_id} marked IN_PROGRESS (Attempt {queue_item.attempt_count})")
            
            try:
                # 2. Fetch Contexts
                patient_data = await mock_ehr.get_patient(db=db, patient_id=queue_item.patient_id)
                camp_res = await db.execute(select(Campaign).where(Campaign.id == queue_item.campaign_id))
                campaign = camp_res.scalar_one()
                
                patient_name = patient_data.name[0] if patient_data and patient_data.name else None
                first_name = patient_name.given[0] if patient_name and patient_name.given else ""
                last_name = patient_name.family if patient_name else ""
                full_name = f"{first_name} {last_name}".strip()
                
                patient_ctx = PatientContext(
                    patient_id=queue_item.patient_id,
                    patient_name=full_name,
                    conditions=[], # In real life, fetch from mock_ehr.get_patient_conditions
                    medications=[]
                )
                
                outreach_ctx = OutreachContext(
                    call_id=uuid.uuid4(),
                    campaign_id=campaign.id,
                    campaign_name=campaign.name,
                    outreach_purpose="Post Discharge Follow Up",
                    attempt_number=queue_item.attempt_count
                )
                
                protocol_ctx = ProtocolContext(
                    protocol_name="Default",
                    version="1.0",
                    questions=[{"id": "q1", "text": "Are you experiencing any swelling?"}]
                )
                
                # 3. Invoke Provider
                logger.info(f"Worker dispatching to provider for {full_name} (item {queue_id})...")
                result = await self.provider.start_call(patient_ctx, outreach_ctx, protocol_ctx)
                
                # 4. Save OutboundCall result
                await OutboundCallService.save_conversation_result(db, result)
                
                # 5. Handle Outcome
                if result.outcome in [ConversationOutcome.COMPLETED, ConversationOutcome.PATIENT_DECLINED, ConversationOutcome.TRANSFERRED]:
                    queue_item.status = QueueItemStatus.COMPLETED
                else:
                    if queue_item.attempt_count >= queue_item.max_attempts:
                        queue_item.status = QueueItemStatus.FAILED
                    else:
                        queue_item.status = QueueItemStatus.RETRY_PENDING
                        delay_minutes = 5 * queue_item.attempt_count
                        if result.outcome == ConversationOutcome.CALLBACK_REQUESTED:
                            delay_minutes = 30
                        queue_item.next_attempt_at = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
                
                await db.commit()
                
                # 6. Pass to Triage Hook
                triage_status = await TriageService.process(result)
                logger.info(f"Worker successfully finished item {queue_id} -> Queue Status: {queue_item.status} | Triage: {triage_status}")
                
            except Exception as e:
                logger.error(f"Worker failed for item {queue_id}: {str(e)}")
                await db.rollback()
                queue_item.status = QueueItemStatus.FAILED
                await db.commit()

call_worker = CallWorker()
