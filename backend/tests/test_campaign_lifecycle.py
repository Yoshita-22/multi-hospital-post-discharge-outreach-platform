import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.campaign import Campaign, CampaignStatus, CampaignValidationStatus
from app.models.audit_log import AuditLog
from app.core.tenant_context import UserRole
from tests.conftest import _create_user_in_db, _get_token

pytestmark = pytest.mark.asyncio

async def _setup_draft_campaign(db: AsyncSession, hospital_id: uuid.UUID):
    camp = Campaign(
        id=uuid.uuid4(),
        hospital_id=hospital_id,
        name="Lifecycle Test Campaign",
        status=CampaignStatus.DRAFT,
        validation_status=CampaignValidationStatus.VALID,
        max_retries=3,
        calling_capacity=10
    )
    db.add(camp)
    
    # Add audit log mock for queue created
    log = AuditLog(
        id=uuid.uuid4(),
        action="CAMPAIGN_QUEUE_CREATED",
        actor_user_id=uuid.uuid4(),
        hospital_id=hospital_id,
        resource_type="CAMPAIGN",
        resource_id=camp.id,
        metadata={}
    )
    db.add(log)
    
    await db.commit()
    await db.refresh(camp)
    return camp


async def test_valid_lifecycle_transitions(client: AsyncClient, db: AsyncSession, hospital_a, hospital_a_token):
    camp = await _setup_draft_campaign(db, hospital_a.id)
    cid = str(camp.id)
    headers = {"Authorization": f"Bearer {hospital_a_token}"}
    
    # 1. DRAFT -> READY
    res = await client.post(f"/api/v1/campaigns/{cid}/ready", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "READY"
    
    # 2. READY -> PAUSED (Should fail)
    res = await client.post(f"/api/v1/campaigns/{cid}/pause", headers=headers)
    assert res.status_code == 400
    
    # 3. READY -> RUNNING
    res = await client.post(f"/api/v1/campaigns/{cid}/start", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "RUNNING"
    
    # 4. RUNNING -> PAUSED
    res = await client.post(f"/api/v1/campaigns/{cid}/pause", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "PAUSED"
    
    # 5. PAUSED -> RUNNING
    res = await client.post(f"/api/v1/campaigns/{cid}/start", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "RUNNING"


async def test_invalid_start_from_draft(client: AsyncClient, db: AsyncSession, hospital_a, hospital_a_token):
    camp = await _setup_draft_campaign(db, hospital_a.id)
    res = await client.post(f"/api/v1/campaigns/{str(camp.id)}/start", headers={"Authorization": f"Bearer {hospital_a_token}"})
    assert res.status_code == 400 # DRAFT -> RUNNING not allowed anymore


async def test_tenant_isolation(client: AsyncClient, db: AsyncSession, hospital_a, hospital_b_token):
    camp = await _setup_draft_campaign(db, hospital_a.id)
    res = await client.post(f"/api/v1/campaigns/{str(camp.id)}/ready", headers={"Authorization": f"Bearer {hospital_b_token}"})
    assert res.status_code == 403 # Hospital B user trying to modify Hospital A campaign


async def test_schedule_campaign(client: AsyncClient, db: AsyncSession, hospital_a, hospital_a_token):
    camp = await _setup_draft_campaign(db, hospital_a.id)
    cid = str(camp.id)
    headers = {"Authorization": f"Bearer {hospital_a_token}"}
    
    await client.post(f"/api/v1/campaigns/{cid}/ready", headers=headers)
    
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    res = await client.post(f"/api/v1/campaigns/{cid}/schedule", json={"start_at": future}, headers=headers)
    
    assert res.status_code == 200
    assert res.json()["status"] == "SCHEDULED"


async def test_auto_scheduler_trigger(client: AsyncClient, db: AsyncSession, hospital_a, hospital_a_token):
    # Test that QueueScheduler auto-starts scheduled campaigns when start_at is reached
    camp = await _setup_draft_campaign(db, hospital_a.id)
    cid = str(camp.id)
    headers = {"Authorization": f"Bearer {hospital_a_token}"}
    
    await client.post(f"/api/v1/campaigns/{cid}/ready", headers=headers)
    
    # Schedule it in the past so it triggers immediately
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    await client.post(f"/api/v1/campaigns/{cid}/schedule", json={"start_at": past}, headers=headers)
    
    # Run scheduler
    res = await client.post("/api/v1/scheduler/run", headers=headers)
    assert res.status_code == 200
    
    # Verify campaign is now RUNNING
    db_camp = (await db.execute(select(Campaign).where(Campaign.id == camp.id))).scalar_one()
    assert db_camp.status == CampaignStatus.RUNNING
