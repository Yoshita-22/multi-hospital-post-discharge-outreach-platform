import uuid
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.tenant_context import TenantContext, UserRole
from app.models.campaign import Campaign, CampaignStatus
from app.schemas.campaign import CampaignCreate
from app.services.audit_service import audit_service


class CampaignService:
    async def create_campaign(
        self, db: AsyncSession, data: CampaignCreate, tenant: TenantContext
    ) -> Campaign:
        """
        Creates a new Campaign.
        Only PLATFORM_ADMIN, HOSPITAL_ADMIN, or CAMPAIGN_MANAGER can create campaigns.
        The provided hospital_id must be accessible by the tenant.
        """
        # 1. Enforce Role Permissions
        allowed_roles = {UserRole.PLATFORM_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.CAMPAIGN_MANAGER}
        if tenant.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your role does not have permission to manage campaigns."
            )

        # 2. Enforce Tenant Isolation
        if not tenant.can_access_hospital(data.hospital_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to the specified hospital."
            )
            
        # Verify hospital exists
        # To avoid a cyclic import with HospitalService or circular dependencies, we can query it directly here or just let FK violation handle it. 
        # But for better UX, let's query it.
        from app.models.hospital import Hospital
        res = await db.execute(select(Hospital.id).where(Hospital.id == data.hospital_id))
        hospital_id = res.scalar_one_or_none()
        if not hospital_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hospital not found."
            )

        # 3. Create Campaign
        try:
            campaign = Campaign(
                hospital_id=data.hospital_id,
                name=data.name,
                description=data.description,
                eligibility_rules=data.eligibility_rules,
                follow_up_window=data.follow_up_window,
                calling_hours=data.calling_hours,
                priority_config=data.priority_config,
                max_retries=data.max_retries,
                calling_capacity=data.calling_capacity,
                status=CampaignStatus.DRAFT,
                created_by=tenant.user_id,
            )
            db.add(campaign)
            
            # We flush so we get the campaign id for the audit log
            await db.flush()

            # 4. Audit Log
            await audit_service.log_event(
                db=db,
                action="CAMPAIGN_CREATED",
                actor_user_id=tenant.user_id,
                hospital_id=data.hospital_id,
                resource_type="CAMPAIGN",
                resource_id=campaign.id,
                metadata={"campaign_name": campaign.name, "status": campaign.status.value}
            )

            await db.commit()
            await db.refresh(campaign)
            return campaign
            
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create campaign: {str(e)}"
            )

    async def mark_ready(self, db: AsyncSession, campaign_id: uuid.UUID, tenant: TenantContext) -> Campaign:
        res = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
        campaign = res.scalar_one_or_none()
        
        if not campaign:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")
            
        if not tenant.can_access_hospital(campaign.hospital_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
            
        if campaign.status != CampaignStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Only DRAFT campaigns can be marked READY."
            )
            
        from app.models.campaign import CampaignValidationStatus
        if campaign.validation_status != CampaignValidationStatus.VALID:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Campaign must be VALID before it can be marked READY."
            )
            
        from app.models.audit_log import AuditLog
        audit_res = await db.execute(
            select(AuditLog).where(
                AuditLog.resource_id == campaign.id,
                AuditLog.action == "CAMPAIGN_QUEUE_CREATED"
            ).limit(1)
        )
        if not audit_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Campaign preparation steps (eligibility, prioritization, queue creation) must be completed before marking READY."
            )
            
        campaign.status = CampaignStatus.READY
        
        await audit_service.log_event(
            db=db,
            action="CAMPAIGN_READY",
            actor_user_id=tenant.user_id,
            hospital_id=campaign.hospital_id,
            resource_type="CAMPAIGN",
            resource_id=campaign.id,
            metadata={"status": campaign.status.value}
        )
        
        await db.commit()
        await db.refresh(campaign)
        return campaign


    async def start_campaign(self, db: AsyncSession, campaign_id: uuid.UUID, tenant: TenantContext) -> Campaign:
        res = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
        campaign = res.scalar_one_or_none()
        
        if not campaign:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")
            
        if not tenant.can_access_hospital(campaign.hospital_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
            
        # VALID TRANSITIONS ONLY
        if campaign.status not in {CampaignStatus.READY, CampaignStatus.PAUSED, CampaignStatus.SCHEDULED}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition campaign from {campaign.status} to RUNNING."
            )
            
        campaign.status = CampaignStatus.RUNNING
        
        await audit_service.log_event(
            db=db,
            action="CAMPAIGN_STARTED",
            actor_user_id=tenant.user_id,
            hospital_id=campaign.hospital_id,
            resource_type="CAMPAIGN",
            resource_id=campaign.id,
            metadata={"status": campaign.status.value}
        )
        
        await db.commit()
        await db.refresh(campaign)
        return campaign


    async def pause_campaign(self, db: AsyncSession, campaign_id: uuid.UUID, tenant: TenantContext) -> Campaign:
        res = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
        campaign = res.scalar_one_or_none()
        
        if not campaign:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")
            
        if not tenant.can_access_hospital(campaign.hospital_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
            
        if campaign.status != CampaignStatus.RUNNING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot pause a campaign that is {campaign.status}. Must be RUNNING."
            )
            
        campaign.status = CampaignStatus.PAUSED
        
        await audit_service.log_event(
            db=db,
            action="CAMPAIGN_PAUSED",
            actor_user_id=tenant.user_id,
            hospital_id=campaign.hospital_id,
            resource_type="CAMPAIGN",
            resource_id=campaign.id,
            metadata={"status": campaign.status.value}
        )
        
        await db.commit()
        await db.refresh(campaign)
        return campaign


    async def schedule_campaign(self, db: AsyncSession, campaign_id: uuid.UUID, start_at: datetime, tenant: TenantContext) -> Campaign:
        res = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
        campaign = res.scalar_one_or_none()
        
        if not campaign:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")
            
        if not tenant.can_access_hospital(campaign.hospital_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
            
        if campaign.status != CampaignStatus.READY:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot schedule a campaign that is {campaign.status}. Must be READY."
            )
            
        campaign.status = CampaignStatus.SCHEDULED
        campaign.start_at = start_at
        
        await audit_service.log_event(
            db=db,
            action="CAMPAIGN_SCHEDULED",
            actor_user_id=tenant.user_id,
            hospital_id=campaign.hospital_id,
            resource_type="CAMPAIGN",
            resource_id=campaign.id,
            metadata={"status": campaign.status.value, "start_at": start_at.isoformat()}
        )
        
        await db.commit()
        await db.refresh(campaign)
        return campaign

campaign_service = CampaignService()
