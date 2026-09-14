from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_tenant_context
from app.core.tenant_context import TenantContext
from app.schemas.campaign import CampaignCreate, CampaignRead
from app.services.campaign_service import campaign_service

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


@router.post(
    "",
    response_model=CampaignRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Campaign"
)
async def create_campaign(
    data: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    """
    Create a new Campaign for outbound outreach.
    
    The initial status will always be DRAFT.
    
    Roles allowed: PLATFORM_ADMIN, HOSPITAL_ADMIN, CAMPAIGN_MANAGER.
    """
    campaign = await campaign_service.create_campaign(db, data, tenant)
    return campaign

from app.schemas.campaign_evaluation import ValidationResult, EligibilityResult
from app.services.campaign_validation_service import campaign_validation_service
from app.services.eligibility_engine import eligibility_engine
import uuid

@router.post(
    "/{campaign_id}/validate",
    response_model=ValidationResult,
    status_code=status.HTTP_200_OK,
)
async def validate_campaign(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context)
):
    from sqlalchemy.future import select
    from app.models.campaign import Campaign
    from fastapi import HTTPException
    
    res = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = res.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")
        
    if not tenant.can_access_hospital(campaign.hospital_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
        
    return await campaign_validation_service.validate_campaign(db, campaign, tenant.user_id)


@router.post(
    "/{campaign_id}/evaluate-eligibility",
    response_model=EligibilityResult,
    status_code=status.HTTP_200_OK,
)
async def evaluate_campaign_eligibility(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context)
):
    return await eligibility_engine.evaluate_campaign(db, campaign_id, tenant)
