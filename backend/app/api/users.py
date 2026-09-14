import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import assert_hospital_access, get_db, get_tenant_context
from app.core.tenant_context import TenantContext
from app.schemas.user import UserCreate, UserResponse
from app.services.user_service import user_service

router = APIRouter(prefix="/hospitals", tags=["Users"])


@router.post(
    "/{hospital_id}/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user for a hospital (PLATFORM_ADMIN or own HOSPITAL_ADMIN)",
)
async def create_hospital_user(
    hospital_id: uuid.UUID,
    body: UserCreate,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Creates a user scoped to hospital_id from the URL path.
    The body's hospital_id (if any) is IGNORED — the path param is authoritative.
    """
    assert_hospital_access(tenant, hospital_id)
    user = await user_service.create_hospital_user(db, hospital_id, body, tenant)
    return UserResponse.model_validate(user)


@router.get(
    "/{hospital_id}/users",
    response_model=list[UserResponse],
    summary="List users for a hospital",
)
async def list_hospital_users(
    hospital_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> list[UserResponse]:
    assert_hospital_access(tenant, hospital_id)
    users = await user_service.get_hospital_users(db, hospital_id, tenant)
    return [UserResponse.model_validate(u) for u in users]
