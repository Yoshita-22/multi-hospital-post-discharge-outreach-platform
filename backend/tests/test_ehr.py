import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.ehr import Patient, Encounter

@pytest.mark.asyncio
async def test_ehr_import_200_patients(
    client: AsyncClient, db: AsyncSession, hospital_a_token: str, hospital_a
):
    import_resp = await client.post(
        f"/api/v1/ehr/import/discharges?hospital_id={hospital_a.id}&count=200",
        headers={"Authorization": f"Bearer {hospital_a_token}"},
    )
    assert import_resp.status_code == 200
    assert import_resp.json()["imported_count"] == 200

@pytest.mark.asyncio
async def test_ehr_import_250_patients(
    client: AsyncClient, db: AsyncSession, hospital_a_token: str, hospital_a
):
    import_resp = await client.post(
        f"/api/v1/ehr/import/discharges?hospital_id={hospital_a.id}&count=250",
        headers={"Authorization": f"Bearer {hospital_a_token}"},
    )
    assert import_resp.status_code == 200
    assert import_resp.json()["imported_count"] == 250

@pytest.mark.asyncio
async def test_ehr_import_300_patients(
    client: AsyncClient, db: AsyncSession, hospital_a_token: str, hospital_a
):
    import_resp = await client.post(
        f"/api/v1/ehr/import/discharges?hospital_id={hospital_a.id}&count=300",
        headers={"Authorization": f"Bearer {hospital_a_token}"},
    )
    assert import_resp.status_code == 200
    assert import_resp.json()["imported_count"] == 300

@pytest.mark.asyncio
async def test_ehr_import_reject_below_minimum(
    client: AsyncClient, hospital_a_token: str, hospital_a
):
    import_resp = await client.post(
        f"/api/v1/ehr/import/discharges?hospital_id={hospital_a.id}&count=199",
        headers={"Authorization": f"Bearer {hospital_a_token}"},
    )
    assert import_resp.status_code == 422

@pytest.mark.asyncio
async def test_ehr_import_reject_above_maximum(
    client: AsyncClient, hospital_a_token: str, hospital_a
):
    import_resp = await client.post(
        f"/api/v1/ehr/import/discharges?hospital_id={hospital_a.id}&count=301",
        headers={"Authorization": f"Bearer {hospital_a_token}"},
    )
    assert import_resp.status_code == 422

@pytest.mark.asyncio
async def test_ehr_import_and_retrieve_patient(
    client: AsyncClient, db: AsyncSession, hospital_a_token: str, hospital_a
):
    import_resp = await client.post(
        f"/api/v1/ehr/import/discharges?hospital_id={hospital_a.id}&count=200",
        headers={"Authorization": f"Bearer {hospital_a_token}"},
    )
    assert import_resp.status_code == 200

    res = await db.execute(select(Patient).where(Patient.hospital_id == hospital_a.id))
    patient = res.scalars().first()
    assert patient is not None

    get_resp = await client.get(
        f"/api/v1/ehr/patients/{patient.id}",
        headers={"Authorization": f"Bearer {hospital_a_token}"},
    )
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["resourceType"] == "Patient"
    assert data["id"] == str(patient.id)
    assert data["hospital_id"] == str(hospital_a.id)

@pytest.mark.asyncio
async def test_tenant_isolation_ehr_data(
    client: AsyncClient, db: AsyncSession, hospital_a_token: str, hospital_b_token: str, hospital_a
):
    await client.post(
        f"/api/v1/ehr/import/discharges?hospital_id={hospital_a.id}&count=200",
        headers={"Authorization": f"Bearer {hospital_a_token}"},
    )

    res = await db.execute(select(Patient).where(Patient.hospital_id == hospital_a.id))
    patient = res.scalars().first()
    
    get_resp = await client.get(
        f"/api/v1/ehr/patients/{patient.id}",
        headers={"Authorization": f"Bearer {hospital_b_token}"},
    )
    assert get_resp.status_code == 403

@pytest.mark.asyncio
async def test_ehr_create_communication_and_task(
    client: AsyncClient, db: AsyncSession, hospital_a_token: str, hospital_a
):
    await client.post(
        f"/api/v1/ehr/import/discharges?hospital_id={hospital_a.id}&count=200",
        headers={"Authorization": f"Bearer {hospital_a_token}"},
    )

    res = await db.execute(select(Patient).where(Patient.hospital_id == hospital_a.id))
    patient = res.scalars().first()

    comm_resp = await client.post(
        f"/api/v1/ehr/patients/{patient.id}/communications",
        json={"communication_type": "Phone Call", "content": "Spoke to patient."},
        headers={"Authorization": f"Bearer {hospital_a_token}"},
    )
    assert comm_resp.status_code == 200
    assert comm_resp.json()["resourceType"] == "Communication"

    task_resp = await client.post(
        f"/api/v1/ehr/patients/{patient.id}/follow-up-task",
        json={"task_type": "Follow-up", "description": "Check vitals"},
        headers={"Authorization": f"Bearer {hospital_a_token}"},
    )
    assert task_resp.status_code == 200
    assert task_resp.json()["resourceType"] == "Task"

@pytest.mark.asyncio
async def test_ehr_update_encounter(
    client: AsyncClient, db: AsyncSession, hospital_a_token: str, hospital_a
):
    await client.post(
        f"/api/v1/ehr/import/discharges?hospital_id={hospital_a.id}&count=200",
        headers={"Authorization": f"Bearer {hospital_a_token}"},
    )

    res = await db.execute(select(Encounter).where(Encounter.hospital_id == hospital_a.id))
    enc = res.scalars().first()

    update_resp = await client.patch(
        f"/api/v1/ehr/encounters/{enc.id}",
        json={"status": "in-progress", "care_setting": "ICU"},
        headers={"Authorization": f"Bearer {hospital_a_token}"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["status"] == "in-progress"
