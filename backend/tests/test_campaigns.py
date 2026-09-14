import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.campaign import Campaign, CampaignStatus
from app.models.audit_log import AuditLog
from app.core.tenant_context import UserRole
from tests.conftest import _create_user_in_db, _get_token

pytestmark = pytest.mark.asyncio

async def test_unauthenticated_creation(client: AsyncClient):
    response = await client.post("/api/v1/campaigns", json={"name": "Test", "hospital_id": str(uuid.uuid4())})
    assert response.status_code == 401

async def test_campaign_manager_creation(client: AsyncClient, db: AsyncSession, hospital_a):
    user = await _create_user_in_db(db, f"cm_{uuid.uuid4().hex[:8]}@test.com", UserRole.CAMPAIGN_MANAGER, hospital_a.id)
    token = await _get_token(client, user.email)

    payload = {
        "name": "High Risk HF",
        "hospital_id": str(hospital_a.id),
        "description": "Test",
        "eligibility_rules": {"all": [{"field": "risk_level", "operator": "equals", "value": "HIGH"}]},
        "follow_up_window": {"type": "post_discharge", "days": 7},
        "calling_hours": {"start": "09:00", "end": "18:00"},
        "priority_config": {"priority": "HIGH"},
        "max_retries": 3,
        "calling_capacity": 10
    }

    response = await client.post(
        "/api/v1/campaigns",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "High Risk HF"
    assert data["status"] == "DRAFT"
    assert data["eligibility_rules"]["all"][0]["value"] == "HIGH"

    # Verify DB
    res = await db.execute(select(Campaign).where(Campaign.id == data["id"]))
    camp = res.scalar_one_or_none()
    assert camp is not None
    assert camp.status == CampaignStatus.DRAFT

    # Verify Audit Log
    res = await db.execute(select(AuditLog).where(AuditLog.resource_id == camp.id, AuditLog.action == "CAMPAIGN_CREATED"))
    log = res.scalar_one_or_none()
    assert log is not None


async def test_hospital_admin_creation(client: AsyncClient, db: AsyncSession, hospital_b, hospital_b_token):
    response = await client.post(
        "/api/v1/campaigns",
        json={"name": "HA Campaign", "hospital_id": str(hospital_b.id)},
        headers={"Authorization": f"Bearer {hospital_b_token}"}
    )
    assert response.status_code == 201


async def test_platform_admin_creation(client: AsyncClient, db: AsyncSession, hospital_a, platform_admin_token):
    response = await client.post(
        "/api/v1/campaigns",
        json={"name": "PA Campaign", "hospital_id": str(hospital_a.id)},
        headers={"Authorization": f"Bearer {platform_admin_token}"}
    )
    assert response.status_code == 201


async def test_clinical_reviewer_blocked(client: AsyncClient, db: AsyncSession, hospital_a):
    user = await _create_user_in_db(db, f"cr_{uuid.uuid4().hex[:8]}@test.com", UserRole.CLINICAL_REVIEWER, hospital_a.id)
    token = await _get_token(client, user.email)

    response = await client.post(
        "/api/v1/campaigns",
        json={"name": "CR Campaign", "hospital_id": str(hospital_a.id)},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


async def test_cross_tenant_isolation(client: AsyncClient, db: AsyncSession, hospital_a, hospital_b):
    user = await _create_user_in_db(db, f"cm2_{uuid.uuid4().hex[:8]}@test.com", UserRole.CAMPAIGN_MANAGER, hospital_a.id)
    token = await _get_token(client, user.email)

    response = await client.post(
        "/api/v1/campaigns",
        json={"name": "Cross Tenant", "hospital_id": str(hospital_b.id)},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


async def test_invalid_hospital_id(client: AsyncClient, db: AsyncSession, platform_admin_token):
    response = await client.post(
        "/api/v1/campaigns",
        json={"name": "Invalid Hosp", "hospital_id": str(uuid.uuid4())},
        headers={"Authorization": f"Bearer {platform_admin_token}"}
    )
    assert response.status_code == 404


async def test_validation_errors(client: AsyncClient, db: AsyncSession, hospital_a):
    user = await _create_user_in_db(db, f"cm3_{uuid.uuid4().hex[:8]}@test.com", UserRole.CAMPAIGN_MANAGER, hospital_a.id)
    token = await _get_token(client, user.email)

    # Empty Name
    res1 = await client.post("/api/v1/campaigns", json={"name": "", "hospital_id": str(hospital_a.id)}, headers={"Authorization": f"Bearer {token}"})
    assert res1.status_code == 422

    # Negative Max Retries
    res2 = await client.post("/api/v1/campaigns", json={"name": "A", "hospital_id": str(hospital_a.id), "max_retries": -1}, headers={"Authorization": f"Bearer {token}"})
    assert res2.status_code == 422

    # Zero Calling Capacity
    res3 = await client.post("/api/v1/campaigns", json={"name": "A", "hospital_id": str(hospital_a.id), "calling_capacity": 0}, headers={"Authorization": f"Bearer {token}"})
    assert res3.status_code == 422
