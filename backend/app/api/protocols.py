import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import assert_hospital_access, get_db, get_tenant_context
from app.core.tenant_context import TenantContext
from app.schemas.protocol import (
    ProtocolCreate,
    ProtocolResponse,
    ProtocolUpdate,
    ProtocolVersionCreate,
)
from app.services.protocol_service import protocol_service

router = APIRouter(prefix="/hospitals", tags=["Protocols"])


@router.post(
    "/{hospital_id}/protocols",
    response_model=ProtocolResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a protocol for a hospital",
)
async def create_protocol(
    hospital_id: uuid.UUID,
    body: ProtocolCreate,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> ProtocolResponse:
    assert_hospital_access(tenant, hospital_id)
    protocol = await protocol_service.create_protocol(db, hospital_id, body, tenant)
    return ProtocolResponse.model_validate(protocol)


@router.get(
    "/{hospital_id}/protocols",
    response_model=list[ProtocolResponse],
    summary="List protocols — always scoped to tenant's hospital",
)
async def list_protocols(
    hospital_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> list[ProtocolResponse]:
    """
    The DB query inside protocol_service.list_protocols() uses tenant.hospital_id,
    not the URL's hospital_id, as the primary filter.
    """
    assert_hospital_access(tenant, hospital_id)
    protocols = await protocol_service.list_protocols(db, tenant, hospital_id)
    return [ProtocolResponse.model_validate(p) for p in protocols]


@router.get(
    "/{hospital_id}/protocols/{protocol_id}",
    response_model=ProtocolResponse,
    summary="Get a single protocol (validates hospital ownership)",
)
async def get_protocol(
    hospital_id: uuid.UUID,
    protocol_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> ProtocolResponse:
    assert_hospital_access(tenant, hospital_id)
    # get_protocol also verifies protocol.hospital_id == tenant.hospital_id
    protocol = await protocol_service.get_protocol(db, protocol_id, tenant)
    return ProtocolResponse.model_validate(protocol)


@router.patch(
    "/{hospital_id}/protocols/{protocol_id}",
    response_model=ProtocolResponse,
    summary="Update a protocol",
)
async def update_protocol(
    hospital_id: uuid.UUID,
    protocol_id: uuid.UUID,
    body: ProtocolUpdate,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> ProtocolResponse:
    assert_hospital_access(tenant, hospital_id)
    protocol = await protocol_service.update_protocol(db, protocol_id, body, tenant)
    return ProtocolResponse.model_validate(protocol)


@router.post(
    "/{hospital_id}/protocols/{protocol_id}/activate",
    response_model=ProtocolResponse,
    summary="Activate a protocol (archives current active version of same name)",
)
async def activate_protocol(
    hospital_id: uuid.UUID,
    protocol_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> ProtocolResponse:
    assert_hospital_access(tenant, hospital_id)
    protocol = await protocol_service.activate_protocol(db, protocol_id, tenant)
    return ProtocolResponse.model_validate(protocol)


@router.post(
    "/{hospital_id}/protocols/{protocol_id}/archive",
    response_model=ProtocolResponse,
    summary="Archive a protocol",
)
async def archive_protocol(
    hospital_id: uuid.UUID,
    protocol_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> ProtocolResponse:
    assert_hospital_access(tenant, hospital_id)
    protocol = await protocol_service.archive_protocol(db, protocol_id, tenant)
    return ProtocolResponse.model_validate(protocol)


@router.post(
    "/{hospital_id}/protocols/{protocol_id}/new-version",
    response_model=ProtocolResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new version of an existing protocol",
)
async def create_new_version(
    hospital_id: uuid.UUID,
    protocol_id: uuid.UUID,
    body: ProtocolVersionCreate,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> ProtocolResponse:
    assert_hospital_access(tenant, hospital_id)
    protocol = await protocol_service.create_new_version(db, protocol_id, body, tenant)
    return ProtocolResponse.model_validate(protocol)
