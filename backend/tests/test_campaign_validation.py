import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.campaign import Campaign, CampaignValidationStatus
from app.core.tenant_context import UserRole
from tests.conftest import _create_user_in_db, _get_token

pytestmark = pytest.mark.asyncio

async def test_validate_valid_campaign(client: AsyncClient, db: AsyncSession, hospital_a, hospital_a_token):
    # 1. Create a draft campaign
    payload = {
        "name": "High Risk HF",
        "hospital_id": str(hospital_a.id),
        "eligibility_rules": {
            "all": [
                {"field": "risk_level", "operator": "equals", "value": "High"}
            ]
        },
        "follow_up_window": {"start_days_after_discharge": 0, "end_days_after_discharge": 7},
        "calling_hours": {"start": "09:00", "end": "18:00"},
        "max_retries": 3,
        "calling_capacity": 10
    }

    create_res = await client.post(
        "/api/v1/campaigns",
        json=payload,
        headers={"Authorization": f"Bearer {hospital_a_token}"}
    )
    assert create_res.status_code == 201
    campaign_id = create_res.json()["id"]

    # 2. Validate
    val_res = await client.post(
        f"/api/v1/campaigns/{campaign_id}/validate",
        headers={"Authorization": f"Bearer {hospital_a_token}"}
    )
    assert val_res.status_code == 200
    data = val_res.json()
    assert data["valid"] is True
    assert len(data["errors"]) == 0

    # Verify DB
    db_camp = (await db.execute(select(Campaign).where(Campaign.id == uuid.UUID(campaign_id)))).scalar_one()
    assert db_camp.validation_status == CampaignValidationStatus.VALID


async def test_validate_invalid_field(client: AsyncClient, db: AsyncSession, hospital_a, hospital_a_token):
    payload = {
        "name": "Invalid Field Campaign",
        "hospital_id": str(hospital_a.id),
        "eligibility_rules": {
            "all": [
                {"field": "unknown_column", "operator": "equals", "value": "High"}
            ]
        }
    }
    create_res = await client.post("/api/v1/campaigns", json=payload, headers={"Authorization": f"Bearer {hospital_a_token}"})
    campaign_id = create_res.json()["id"]

    val_res = await client.post(f"/api/v1/campaigns/{campaign_id}/validate", headers={"Authorization": f"Bearer {hospital_a_token}"})
    assert val_res.status_code == 200
    data = val_res.json()
    assert data["valid"] is False
    assert len(data["errors"]) > 0
    assert "Unsupported field" in data["errors"][0]["message"]


async def test_validate_invalid_operator(client: AsyncClient, db: AsyncSession, hospital_a, hospital_a_token):
    payload = {
        "name": "Invalid Operator Campaign",
        "hospital_id": str(hospital_a.id),
        "eligibility_rules": {
            "all": [
                {"field": "risk_level", "operator": "greater_than", "value": 5}
            ]
        }
    }
    create_res = await client.post("/api/v1/campaigns", json=payload, headers={"Authorization": f"Bearer {hospital_a_token}"})
    campaign_id = create_res.json()["id"]

    val_res = await client.post(f"/api/v1/campaigns/{campaign_id}/validate", headers={"Authorization": f"Bearer {hospital_a_token}"})
    assert val_res.status_code == 200
    data = val_res.json()
    assert data["valid"] is False
    assert "Unsupported operator" in data["errors"][0]["message"]


async def test_tenant_isolation_validation(client: AsyncClient, db: AsyncSession, hospital_a, hospital_b_token):
    payload = {
        "name": "HA Campaign",
        "hospital_id": str(hospital_a.id)
    }
    # Create bypassing router if needed, or assume we already have one
    camp = Campaign(
        id=uuid.uuid4(),
        hospital_id=hospital_a.id,
        name="Tenant Iso Test",
    )
    db.add(camp)
    await db.commit()

    val_res = await client.post(
        f"/api/v1/campaigns/{camp.id}/validate",
        headers={"Authorization": f"Bearer {hospital_b_token}"}
    )
    assert val_res.status_code == 403
