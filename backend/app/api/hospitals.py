import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    assert_hospital_access,
    get_db,
    get_tenant_context,
    require_platform_admin,
)
from app.core.tenant_context import TenantContext
from app.schemas.configuration import ConfigurationResponse, ConfigurationUpdate
from app.schemas.hospital import (
    HospitalCreate,
    HospitalResponse,
    HospitalUpdate,
    ReadinessReport,
)
from app.services.hospital_service import hospital_service
from app.services.readiness_service import readiness_service

router = APIRouter(prefix="/hospitals", tags=["Hospitals"])


# --------------------------------------------------------------------------- #
# Hospital CRUD                                                                #
# --------------------------------------------------------------------------- #


@router.post(
    "",
    response_model=HospitalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new hospital (PLATFORM_ADMIN only)",
)
async def create_hospital(
    body: HospitalCreate,
    tenant: TenantContext = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> HospitalResponse:
    hospital = await hospital_service.create_hospital(db, body, tenant)
    return HospitalResponse.model_validate(hospital)


@router.get(
    "",
    response_model=list[HospitalResponse],
    summary="List hospitals (PLATFORM_ADMIN sees all; others see own)",
)
async def list_hospitals(
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> list[HospitalResponse]:
    hospitals = await hospital_service.list_hospitals(db, tenant)
    return [HospitalResponse.model_validate(h) for h in hospitals]


@router.get(
    "/{hospital_id}",
    response_model=HospitalResponse,
    summary="Get a hospital by ID",
)
async def get_hospital(
    hospital_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> HospitalResponse:
    assert_hospital_access(tenant, hospital_id)
    hospital = await hospital_service.get_hospital(db, hospital_id, tenant)
    return HospitalResponse.model_validate(hospital)


@router.patch(
    "/{hospital_id}",
    response_model=HospitalResponse,
    summary="Update hospital details",
)
async def update_hospital(
    hospital_id: uuid.UUID,
    body: HospitalUpdate,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> HospitalResponse:
    assert_hospital_access(tenant, hospital_id)
    hospital = await hospital_service.update_hospital(db, hospital_id, body, tenant)
    return HospitalResponse.model_validate(hospital)


# --------------------------------------------------------------------------- #
# Configuration                                                                #
# --------------------------------------------------------------------------- #


@router.get(
    "/{hospital_id}/configuration",
    response_model=ConfigurationResponse,
    summary="Get hospital configuration",
)
async def get_configuration(
    hospital_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> ConfigurationResponse:
    assert_hospital_access(tenant, hospital_id)
    config = await hospital_service.get_configuration(db, hospital_id, tenant)
    return ConfigurationResponse.model_validate(config)


@router.put(
    "/{hospital_id}/configuration",
    response_model=ConfigurationResponse,
    summary="Update hospital configuration (PLATFORM_ADMIN or own HOSPITAL_ADMIN)",
)
async def update_configuration(
    hospital_id: uuid.UUID,
    body: ConfigurationUpdate,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> ConfigurationResponse:
    # Hospital Admin of Hospital A cannot update Hospital B's config
    assert_hospital_access(tenant, hospital_id)
    config = await hospital_service.update_configuration(db, hospital_id, body, tenant)
    return ConfigurationResponse.model_validate(config)


# --------------------------------------------------------------------------- #
# Readiness                                                                    #
# --------------------------------------------------------------------------- #


@router.post(
    "/{hospital_id}/readiness",
    response_model=ReadinessReport,
    summary="Trigger onboarding readiness check (ONBOARDING → READY)",
)
async def check_readiness(
    hospital_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> ReadinessReport:
    assert_hospital_access(tenant, hospital_id)
    _, report = await readiness_service.transition_to_ready(db, hospital_id)
    return report
