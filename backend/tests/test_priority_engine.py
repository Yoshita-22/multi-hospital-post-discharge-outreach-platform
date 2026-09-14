import uuid
from datetime import datetime, timedelta
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.campaign import Campaign, CampaignValidationStatus
from app.models.campaign_patient import CampaignPatient
from app.models.ehr import Patient, Discharge, Encounter

pytestmark = pytest.mark.asyncio

async def _setup_campaign(db: AsyncSession, hospital_id: uuid.UUID):
    camp = Campaign(
        id=uuid.uuid4(),
        hospital_id=hospital_id,
        name="Priority Test",
        validation_status=CampaignValidationStatus.VALID,
        priority_config={"weights": {"clinical_risk": 1.0}}
    )
    db.add(camp)
    await db.commit()
    await db.refresh(camp)
    return camp

async def test_priority_engine_only_evaluates_eligible(client: AsyncClient, db: AsyncSession, hospital_a, hospital_a_token):
    camp = await _setup_campaign(db, hospital_a.id)
    
    p = Patient(id=uuid.uuid4(), hospital_id=hospital_a.id, first_name="A", last_name="B", date_of_birth=datetime(1980, 1, 1).date(), gender="Male", contact_phone="+1234567890")
    db.add(p)
    db.add(CampaignPatient(campaign_id=camp.id, patient_id=p.id, eligibility_status="NOT_ELIGIBLE", evaluated_at=datetime.utcnow()))
    await db.commit()
    
    res = await client.post(
        f"/api/v1/campaigns/{camp.id}/prioritize",
        headers={"Authorization": f"Bearer {hospital_a_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["prioritized_count"] == 0


async def test_priority_engine_basic_scoring(client: AsyncClient, db: AsyncSession, hospital_a, hospital_a_token):
    camp = await _setup_campaign(db, hospital_a.id)
    
    p1 = Patient(id=uuid.uuid4(), hospital_id=hospital_a.id, first_name="High", last_name="Risk", date_of_birth=datetime(1980, 1, 1).date(), gender="Male", contact_phone="+1234567890")
    p2 = Patient(id=uuid.uuid4(), hospital_id=hospital_a.id, first_name="Low", last_name="Risk", date_of_birth=datetime(1980, 1, 1).date(), gender="Male", contact_phone="+1234567890")
    db.add_all([p1, p2])
    
    now = datetime.utcnow()
    e1 = Encounter(id=uuid.uuid4(), hospital_id=hospital_a.id, patient_id=p1.id)
    e2 = Encounter(id=uuid.uuid4(), hospital_id=hospital_a.id, patient_id=p2.id)
    db.add_all([e1, e2])

    d1 = Discharge(id=uuid.uuid4(), hospital_id=hospital_a.id, patient_id=p1.id, encounter_id=e1.id, risk_level="High", discharge_timestamp=now)
    d2 = Discharge(id=uuid.uuid4(), hospital_id=hospital_a.id, patient_id=p2.id, encounter_id=e2.id, risk_level="Low", discharge_timestamp=now)
    db.add_all([d1, d2])
    
    db.add(CampaignPatient(campaign_id=camp.id, patient_id=p1.id, eligibility_status="ELIGIBLE", evaluated_at=now))
    db.add(CampaignPatient(campaign_id=camp.id, patient_id=p2.id, eligibility_status="ELIGIBLE", evaluated_at=now))
    await db.commit()
    
    res = await client.post(f"/api/v1/campaigns/{camp.id}/prioritize", headers={"Authorization": f"Bearer {hospital_a_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["prioritized_count"] == 2
    assert data["high_priority_count"] == 1
    assert data["low_priority_count"] == 1
    
    cp1 = (await db.execute(select(CampaignPatient).where(CampaignPatient.patient_id == p1.id))).scalar_one()
    cp2 = (await db.execute(select(CampaignPatient).where(CampaignPatient.patient_id == p2.id))).scalar_one()
    
    assert cp1.priority_rank == 1
    assert cp2.priority_rank == 2


async def test_priority_engine_unvalidated_rejected(client: AsyncClient, db: AsyncSession, hospital_a, hospital_a_token):
    camp = Campaign(
        id=uuid.uuid4(),
        hospital_id=hospital_a.id,
        name="Unval",
        validation_status=CampaignValidationStatus.NOT_VALIDATED
    )
    db.add(camp)
    await db.commit()
    
    res = await client.post(f"/api/v1/campaigns/{camp.id}/prioritize", headers={"Authorization": f"Bearer {hospital_a_token}"})
    assert res.status_code == 409


async def test_tenant_isolation_prioritization(client: AsyncClient, db: AsyncSession, hospital_a, hospital_b_token):
    camp = await _setup_campaign(db, hospital_a.id)
    res = await client.post(f"/api/v1/campaigns/{camp.id}/prioritize", headers={"Authorization": f"Bearer {hospital_b_token}"})
    assert res.status_code == 403


async def test_invalid_weights(client: AsyncClient, db: AsyncSession, hospital_a, hospital_a_token):
    camp = Campaign(
        id=uuid.uuid4(),
        hospital_id=hospital_a.id,
        name="Inv Weights",
        validation_status=CampaignValidationStatus.VALID,
        priority_config={"weights": {"clinical_risk": 0.5, "follow_up_urgency": 0.1}} # Sum = 0.6
    )
    db.add(camp)
    await db.commit()
    
    res = await client.post(f"/api/v1/campaigns/{camp.id}/prioritize", headers={"Authorization": f"Bearer {hospital_a_token}"})
    assert res.status_code == 400
