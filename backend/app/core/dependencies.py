from __future__ import annotations

import uuid
from typing import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.core.tenant_context import TenantContext, UserRole
from app.db.database import AsyncSessionLocal

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ---------------------------------------------------------------------------
# Database session
# ---------------------------------------------------------------------------


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async SQLAlchemy session and close it after the request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """
    Decode the JWT, load the User from DB, verify they are ACTIVE.
    Returns the ORM User object.
    """
    # Import here to avoid circular imports at module load time
    from app.models.user import User, UserStatus

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        user_id_str: str | None = payload.get("user_id")
        if not user_id_str:
            raise credentials_exception
        user_id = uuid.UUID(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active.",
        )

    return user


# ---------------------------------------------------------------------------
# Tenant Context
# ---------------------------------------------------------------------------


def get_tenant_context(
    current_user=Depends(get_current_user),
) -> TenantContext:
    """Build TenantContext from the authenticated user."""
    return TenantContext(
        user_id=current_user.id,
        hospital_id=current_user.hospital_id,
        role=UserRole(current_user.role.value),
    )


# ---------------------------------------------------------------------------
# Role guards
# ---------------------------------------------------------------------------


def require_platform_admin(
    tenant: TenantContext = Depends(get_tenant_context),
) -> TenantContext:
    """Dependency: caller must be PLATFORM_ADMIN."""
    if not tenant.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Platform Admins can perform this action.",
        )
    return tenant


def require_hospital_access(hospital_id: uuid.UUID) -> TenantContext:
    """
    Factory that returns a dependency checking the tenant can access `hospital_id`.
    Usage:
        tenant: TenantContext = Depends(require_hospital_access(hospital_id))
    But since hospital_id comes from the path, use inline check in endpoints instead.
    """

    async def _check(
        tenant: TenantContext = Depends(get_tenant_context),
    ) -> TenantContext:
        if not tenant.can_access_hospital(hospital_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this hospital.",
            )
        return tenant

    return Depends(_check)


def assert_hospital_access(
    tenant: TenantContext, hospital_id: uuid.UUID, resource_label: str = "hospital"
) -> None:
    """
    Inline check used inside endpoint functions.
    Raises 403 if tenant cannot access the given hospital.
    """
    if not tenant.can_access_hospital(hospital_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You do not have access to this {resource_label}.",
        )
