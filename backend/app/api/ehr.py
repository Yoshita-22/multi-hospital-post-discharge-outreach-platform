import uuid
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_tenant_context, require_platform_admin
from app.core.tenant_context import TenantContext
from app.ehr.schemas import (
    PatientSchema,
    EncounterSchema,
    DischargeSchema,
    ConditionSchema,
    MedicationSchema,
    ObservationSchema,
    CarePlanSchema,
    CommunicationSchema,
    TaskSchema,
    CommunicationCreate,
    TaskCreate,
    ObservationCreate,
    EncounterUpdate,
    OutreachOutcomeCreate,
)
from app.ehr.service import healthcare_data_service

router = APIRouter(prefix="/ehr", tags=["EHR Mock (Phase 2)"])


@router.get("/patients/{patient_id}", response_model=PatientSchema)
async def get_patient(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return await healthcare_data_service.get_patient(db, patient_id, tenant)


@router.get("/patients/{patient_id}/encounters", response_model=List[EncounterSchema])
async def get_encounters(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return await healthcare_data_service.get_encounters(db, patient_id, tenant)


@router.get("/patients/{patient_id}/discharge", response_model=List[DischargeSchema])
async def get_discharges(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return await healthcare_data_service.get_discharges(db, patient_id, tenant)


@router.get("/patients/{patient_id}/observations", response_model=List[ObservationSchema])
async def get_observations(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return await healthcare_data_service.get_observations(db, patient_id, tenant)


@router.get("/patients/{patient_id}/conditions", response_model=List[ConditionSchema])
async def get_conditions(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return await healthcare_data_service.get_conditions(db, patient_id, tenant)


@router.get("/patients/{patient_id}/medications", response_model=List[MedicationSchema])
async def get_medications(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return await healthcare_data_service.get_medications(db, patient_id, tenant)


@router.get("/patients/{patient_id}/care-plan", response_model=List[CarePlanSchema])
async def get_care_plans(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return await healthcare_data_service.get_care_plans(db, patient_id, tenant)


@router.post("/patients/{patient_id}/communications", response_model=CommunicationSchema)
async def create_communication(
    patient_id: uuid.UUID,
    data: CommunicationCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return await healthcare_data_service.create_communication(db, patient_id, data, tenant)


@router.post("/patients/{patient_id}/outreach-outcome")
async def record_outreach_outcome(
    patient_id: uuid.UUID,
    data: OutreachOutcomeCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return await healthcare_data_service.record_outreach_outcome(db, patient_id, data, tenant)


@router.post("/patients/{patient_id}/observations", response_model=ObservationSchema)
async def create_observation(
    patient_id: uuid.UUID,
    data: ObservationCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return await healthcare_data_service.create_observation(db, patient_id, data, tenant)


@router.post("/patients/{patient_id}/follow-up-task", response_model=TaskSchema)
async def create_follow_up_task(
    patient_id: uuid.UUID,
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return await healthcare_data_service.create_task(db, patient_id, data, tenant)


@router.post("/patients/{patient_id}/escalations", response_model=TaskSchema)
async def create_escalation(
    patient_id: uuid.UUID,
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    # Ensure task_type is escalation for consistency
    data.task_type = "escalation"
    return await healthcare_data_service.create_task(db, patient_id, data, tenant)


@router.patch("/encounters/{encounter_id}", response_model=EncounterSchema)
async def update_encounter(
    encounter_id: uuid.UUID,
    data: EncounterUpdate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return await healthcare_data_service.update_encounter(db, encounter_id, data, tenant)


@router.post("/import/discharges")
async def import_discharges(
    hospital_id: uuid.UUID,
    count: int = Query(250, ge=200, le=300),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    """
    Simulates importing a set number of patient discharges into a hospital's EHR instance.
    """
    return await healthcare_data_service.generate_simulated_discharges(db, hospital_id, count, tenant)
