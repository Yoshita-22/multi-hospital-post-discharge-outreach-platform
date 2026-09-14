import uuid
import zoneinfo
from datetime import datetime, timezone
from typing import List

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, and_, or_, func

from app.core.tenant_context import TenantContext
from app.models.campaign import Campaign, CampaignStatus
from app.models.campaign_patient import CampaignPatient
from app.models.outbound_queue import OutboundQueue, QueueItemStatus
from app.schemas.scheduler import SchedulerRunResult
from app.services.audit_service import audit_service
from app.services.call_dispatcher import call_dispatcher


class QueueScheduler:
    
    async def run_once(self, db: AsyncSession, tenant: TenantContext) -> SchedulerRunResult:
        now = datetime.now(timezone.utc)
        
        # 0. Auto-start SCHEDULED campaigns whose start_at has been reached
        auto_start_stmt = (
            update(Campaign)
            .where(
                Campaign.hospital_id == tenant.hospital_id,
                Campaign.status == CampaignStatus.SCHEDULED,
                Campaign.start_at <= now
            )
            .values(status=CampaignStatus.RUNNING)
        )
        await db.execute(auto_start_stmt)
        # Note: We omit the audit log here for brevity and speed, but ideally an async event is emitted.
        
        # 1. Fetch active campaigns for the tenant
        stmt = select(Campaign).where(
            Campaign.hospital_id == tenant.hospital_id,
            Campaign.status == CampaignStatus.RUNNING
        )
        res = await db.execute(stmt)
        campaigns = res.scalars().all()
        
        campaigns_checked = len(campaigns)
        campaigns_with_capacity = 0
        jobs_considered = 0
        jobs_claimed = 0
        
        now = datetime.now(timezone.utc)
        
        for campaign in campaigns:
            print("NOW UTC:", now)
            print("NOW IST:", now.astimezone(zoneinfo.ZoneInfo("Asia/Kolkata")))
            print("CALLING HOURS:", campaign.calling_hours)
            print(
                "WITHIN CALLING HOURS:",
                self._is_within_calling_hours(campaign.calling_hours, now)
            )
            print("CALLING CAPACITY:", campaign.calling_capacity)
            # 2. Check calling hours
            if not self._is_within_calling_hours(campaign.calling_hours, now):
                continue
                
            # 3. Calculate active calls
            active_calls_stmt = select(func.count()).select_from(OutboundQueue).where(
                OutboundQueue.campaign_id == campaign.id,
                OutboundQueue.status.in_([QueueItemStatus.CLAIMED, QueueItemStatus.IN_PROGRESS])
            )
            active_calls = (await db.execute(active_calls_stmt)).scalar() or 0
            
            available_capacity = max(0, campaign.calling_capacity - active_calls)
            
            if available_capacity <= 0:
                continue
                
            campaigns_with_capacity += 1
            
            # 4. Fetch PENDING queue items
            queue_stmt = (
                select(OutboundQueue, CampaignPatient)
                .join(CampaignPatient, and_(
                    CampaignPatient.campaign_id == OutboundQueue.campaign_id,
                    CampaignPatient.patient_id == OutboundQueue.patient_id
                ))
                .where(
                    OutboundQueue.campaign_id == campaign.id,
                    OutboundQueue.status == QueueItemStatus.PENDING,
                    OutboundQueue.scheduled_at <= now,
                    OutboundQueue.attempt_count < OutboundQueue.max_attempts,
                    or_(
                        OutboundQueue.next_attempt_at == None,
                        OutboundQueue.next_attempt_at <= now
                    )
                )
            )
            candidates_res = await db.execute(queue_stmt)
            candidates = candidates_res.all()
            
            if not candidates:
                continue
                
            jobs_considered += len(candidates)
            
            # 5. Calculate scheduling scores
            scored_candidates = []
            for queue_item, campaign_patient in candidates:
                factors = campaign_patient.priority_factors or {}
                
                priority_score = queue_item.priority_score or 0.0
                deadline_urgency = factors.get("follow_up_urgency", 0.0)
                patient_availability = 1.0  # Prototype mock
                retry_urgency = queue_item.attempt_count / queue_item.max_attempts if queue_item.max_attempts > 0 else 0.0
                campaign_priority = factors.get("campaign_priority", 0.5)
                outcome_factor = 0.0  # Prototype mock
                
                scheduling_score = (
                    0.35 * priority_score +
                    0.25 * deadline_urgency +
                    0.15 * patient_availability +
                    0.10 * retry_urgency +
                    0.10 * campaign_priority +
                    0.05 * outcome_factor
                )
                
                scored_candidates.append({
                    "id": queue_item.id,
                    "score": scheduling_score,
                    "urgency": deadline_urgency,
                    "priority": priority_score,
                    "scheduled_at": queue_item.scheduled_at,
                    "created_at": queue_item.created_at
                })
                
            # 6. Sort
            scored_candidates.sort(
                key=lambda x: (
                    x["score"],
                    x["urgency"],
                    x["priority"],
                    -x["scheduled_at"].timestamp(),
                    -x["created_at"].timestamp()
                ),
                reverse=True
            )
            
            # 7. Select
            selected_ids = [c["id"] for c in scored_candidates[:available_capacity]]
            
            # 8. Atomic Claiming
            if selected_ids:
                claim_stmt = (
                    update(OutboundQueue)
                    .where(
                        OutboundQueue.id.in_(selected_ids),
                        OutboundQueue.status == QueueItemStatus.PENDING
                    )
                    .values(status=QueueItemStatus.CLAIMED)
                    .returning(OutboundQueue.id)
                )
                
                claimed_res = await db.execute(claim_stmt)
                claimed_ids = claimed_res.scalars().all()
                
                jobs_claimed += len(claimed_ids)
                
                # Handoff interface outside database transaction logical context, but within function
                for cid in claimed_ids:
                    call_dispatcher.dispatch(cid)
                    
        # Audit Log
        if jobs_claimed > 0:
            await audit_service.log_event(
                db=db,
                action="QUEUE_JOBS_CLAIMED",
                actor_user_id=tenant.user_id,
                hospital_id=tenant.hospital_id,
                resource_type="SCHEDULER",
                resource_id=uuid.uuid4(),
                metadata={
                    "campaigns_checked": campaigns_checked,
                    "campaigns_with_capacity": campaigns_with_capacity,
                    "jobs_considered": jobs_considered,
                    "jobs_claimed": jobs_claimed
                }
            )
            
        await db.commit()
            
        return SchedulerRunResult(
            campaigns_checked=campaigns_checked,
            campaigns_with_capacity=campaigns_with_capacity,
            jobs_considered=jobs_considered,
            jobs_claimed=jobs_claimed
        )
        

    def _is_within_calling_hours(self, calling_hours: dict | None, now_utc: datetime) -> bool:
        if not calling_hours:
            return True
            
        start_str = calling_hours.get("start")
        end_str = calling_hours.get("end")
        tz_str = calling_hours.get("timezone", "UTC")
        
        if not start_str or not end_str:
            return True
            
        try:
            tz = zoneinfo.ZoneInfo(tz_str)
        except zoneinfo.ZoneInfoNotFoundError:
            tz = timezone.utc
            
        now_local = now_utc.astimezone(tz)
        
        start_hour, start_minute = map(int, start_str.split(":"))
        end_hour, end_minute = map(int, end_str.split(":"))
        
        start_time_today = now_local.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
        end_time_today = now_local.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
        
        return start_time_today <= now_local <= end_time_today


queue_scheduler = QueueScheduler()
