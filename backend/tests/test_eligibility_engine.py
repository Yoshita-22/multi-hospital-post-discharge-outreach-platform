import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.campaign import Campaign, CampaignValidationStatus
from app.models.campaign_patient import CampaignPatient
from app.models.ehr import Patient, Discharge

pytestmark = pytest.mark.asyncio


async def _setup_campaign(db: AsyncSession, hospital_id: uuid.UUID, rules: dict, status: CampaignValidationStatus = CampaignValidationStatus.VALID):
    camp = Campaign(
        id=uuid.uuid4(),
        hospital_id=hospital_id,
        name="Eligibility Test",
        eligibility_rules=rules,
        validation_status=status
    )
    db.add(camp)
    await db.commit()
    await db.refresh(camp)
    return camp


async def test_unvalidated_campaign_rejected(client: AsyncClient, db: AsyncSession, hospital_a, hospital_a_token):
    camp = await _setup_campaign(db, hospital_a.id, {}, CampaignValidationStatus.NOT_VALIDATED)
    
    res = await client.post(
        f"/api/v1/campaigns/{camp.id}/evaluate-eligibility",
        headers={"Authorization": f"Bearer {hospital_a_token}"}
    )
    assert res.status_code == 409


async def test_evaluate_basic_rule(client: AsyncClient, db: AsyncSession, hospital_a, hospital_a_token):
    # Ensure there is at least one patient to evaluate
    p = Patient(id=uuid.uuid4(), hospital_id=hospital_a.id, first_name="John", last_name="Doe")
    db.add(p)
    d = Discharge(id=uuid.uuid4(), hospital_id=hospital_a.id, patient_id=p.id, encounter_id=uuid.uuid4(), risk_level="High", discharge_timestamp="2026-09-01T00:00:00Z")
    db.add(d)
    await db.commit()

    rules = {
        "all": [
            {"field": "risk_level", "operator": "equals", "value": "High"}
        ]
    }
    camp = await _setup_campaign(db, hospital_a.id, rules)

    res = await client.post(
        f"/api/v1/campaigns/{camp.id}/evaluate-eligibility",
        headers={"Authorization": f"Bearer {hospital_a_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["evaluated_count"] >= 1
    
    # Verify persistence
    cp = (await db.execute(select(CampaignPatient).where(CampaignPatient.campaign_id == camp.id))).scalars().all()
    assert len(cp) == data["eligible_count"]


async def test_tenant_isolation_evaluation(client: AsyncClient, db: AsyncSession, hospital_a, hospital_b_token):
    camp = await _setup_campaign(db, hospital_a.id, {})
    
    res = await client.post(
        f"/api/v1/campaigns/{camp.id}/evaluate-eligibility",
        headers={"Authorization": f"Bearer {hospital_b_token}"}
    )
    assert res.status_code == 403
