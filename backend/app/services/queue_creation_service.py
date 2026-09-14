import uuid
import zoneinfo
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import insert

from app.models.campaign import Campaign, CampaignValidationStatus
from app.models.campaign_patient import CampaignPatient
from app.models.outbound_queue import OutboundQueue, QueueItemStatus
from app.schemas.queue_creation import QueueCreationResult
from app.services.audit_service import audit_service
from app.core.tenant_context import TenantContext


class QueueCreationService:
    async def create_queue_entries(self, db: AsyncSession, campaign_id: uuid.UUID, tenant: TenantContext) -> QueueCreationResult:
        # 1. Fetch and Validate Campaign
        res = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
        campaign = res.scalar_one_or_none()
        if not campaign:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")

        if not tenant.can_access_hospital(campaign.hospital_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to campaign.")

        if campaign.validation_status != CampaignValidationStatus.VALID:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Campaign validation_status must be VALID.")

        # 2. Query Eligible and Prioritized Patients (with tenant isolation)
        stmt = (
            select(CampaignPatient)
            .where(CampaignPatient.campaign_id == campaign_id)
            .where(CampaignPatient.eligibility_status == "ELIGIBLE")
            .where(CampaignPatient.priority_score.isnot(None))
            .where(CampaignPatient.priority_rank.isnot(None))
            # The campaign_patient mapping already inherently enforces hospital isolation when combined with valid campaign_id, 
            # but we can explicitly assert it by traversing the relationship if needed. 
            # In Phase 3, CampaignPatient only contains patients from campaign.hospital_id.
        )
        result = await db.execute(stmt)
        campaign_patients = result.scalars().all()

        if not campaign_patients:
            return await self._empty_result(db, campaign, tenant.user_id)

        # 3. Determine `scheduled_at` based on calling hours
        scheduled_at_time = self._calculate_initial_scheduled_at(campaign.calling_hours)
        max_attempts = campaign.max_retries

        # 4. Prepare Bulk Insert Data
        # Using insert().on_conflict_do_nothing() to handle duplicates natively and cleanly skip them
        insert_values = []
        for cp in campaign_patients:
            insert_values.append({
                "id": uuid.uuid4(),
                "campaign_id": campaign.id,
                "patient_id": cp.patient_id,
                "hospital_id": campaign.hospital_id,
                "priority_score": cp.priority_score,
                "priority_level": cp.priority_level,
                "priority_rank": cp.priority_rank,
                "status": QueueItemStatus.PENDING,
                "attempt_count": 0,
                "max_attempts": max_attempts,
                "scheduled_at": scheduled_at_time,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            })
            
        if not insert_values:
            return await self._empty_result(db, campaign, tenant.user_id)

        insert_stmt = insert(OutboundQueue).values(insert_values).on_conflict_do_nothing(
            index_elements=["campaign_id", "patient_id"]
        )

        res = await db.execute(insert_stmt)
        queued_count = res.rowcount
        skipped_count = len(insert_values) - queued_count
        
        await audit_service.log_event(
            db=db,
            action="CAMPAIGN_QUEUE_CREATED",
            actor_user_id=tenant.user_id,
            hospital_id=campaign.hospital_id,
            resource_type="CAMPAIGN",
            resource_id=campaign.id,
            metadata={
                "queued_count": queued_count,
                "skipped_existing_count": skipped_count,
                "scheduled_count": queued_count
            }
        )

        await db.commit()

        return QueueCreationResult(
            campaign_id=campaign.id,
            queued_count=queued_count,
            skipped_existing_count=skipped_count,
            scheduled_count=queued_count
        )
        
    async def _empty_result(self, db: AsyncSession, campaign: Campaign, user_id: uuid.UUID) -> QueueCreationResult:
        await audit_service.log_event(
            db=db,
            action="CAMPAIGN_QUEUE_CREATED",
            actor_user_id=user_id,
            hospital_id=campaign.hospital_id,
            resource_type="CAMPAIGN",
            resource_id=campaign.id,
            metadata={"queued_count": 0, "skipped_existing_count": 0, "scheduled_count": 0}
        )
        await db.commit()
        return QueueCreationResult(
            campaign_id=campaign.id,
            queued_count=0,
            skipped_existing_count=0,
            scheduled_count=0
        )
        

    def _calculate_initial_scheduled_at(self, calling_hours: dict | None) -> datetime:
        now_utc = datetime.now(timezone.utc)
        
        if not calling_hours:
            return now_utc
            
        start_str = calling_hours.get("start")
        end_str = calling_hours.get("end")
        tz_str = calling_hours.get("timezone", "UTC")
        
        if not start_str or not end_str:
            return now_utc
            
        try:
            tz = zoneinfo.ZoneInfo(tz_str)
        except zoneinfo.ZoneInfoNotFoundError:
            tz = timezone.utc
            
        now_local = now_utc.astimezone(tz)
        
        start_hour, start_minute = map(int, start_str.split(":"))
        end_hour, end_minute = map(int, end_str.split(":"))
        
        start_time_today = now_local.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
        end_time_today = now_local.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
        
        if now_local < start_time_today:
            # Case 1: Before calling window
            return start_time_today.astimezone(timezone.utc)
        elif start_time_today <= now_local <= end_time_today:
            # Case 2: Inside calling window (immediate)
            return now_utc
        else:
            # Case 3: After calling window
            start_time_tomorrow = start_time_today + timedelta(days=1)
            return start_time_tomorrow.astimezone(timezone.utc)

queue_creation_service = QueueCreationService()
