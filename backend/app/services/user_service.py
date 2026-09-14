from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.core.tenant_context import TenantContext
from app.models.user import User, UserRole, UserStatus
from app.schemas.user import UserCreate
from app.services.audit_service import audit_service


class UserService:
    async def create_hospital_user(
        self,
        db: AsyncSession,
        hospital_id: uuid.UUID,
        data: UserCreate,
        actor: TenantContext,
    ) -> User:
        """
        Create a user scoped to hospital_id.
        The hospital_id is ALWAYS taken from the URL path (actor context or path param),
        never from the request body — prevents tenant hopping.
        """
        # Check for duplicate email
        existing = await db.execute(select(User).where(User.email == data.email))
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A user with email '{data.email}' already exists.",
            )

        # PLATFORM_ADMIN cannot be created via this endpoint
        if data.role == UserRole.PLATFORM_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="PLATFORM_ADMIN users cannot be created via hospital user endpoints.",
            )

        user = User(
            id=uuid.uuid4(),
            hospital_id=hospital_id,  # Forced — never from body
            name=data.name,
            email=data.email,
            password_hash=hash_password(data.password),
            role=data.role,
            status=UserStatus.ACTIVE,
        )
        db.add(user)
        await db.flush()

        await audit_service.log_event(
            db=db,
            action="USER_CREATED",
            actor_user_id=actor.user_id,
            hospital_id=hospital_id,
            resource_type="USER",
            resource_id=user.id,
            metadata={"role": data.role.value, "email": data.email},
        )

        await db.commit()
        await db.refresh(user)
        return user

    async def get_hospital_users(
        self,
        db: AsyncSession,
        hospital_id: uuid.UUID,
        actor: TenantContext,
    ) -> list[User]:
        """List all users belonging to hospital_id, scoped by TenantContext."""
        result = await db.execute(
            select(User).where(User.hospital_id == hospital_id)
        )
        return list(result.scalars().all())

    async def update_user_status(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        new_status: UserStatus,
        actor: TenantContext,
    ) -> User:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

        # Tenant isolation
        if not actor.can_access_hospital(user.hospital_id):
            raise HTTPException(status_code=403, detail="Access denied.")

        old_status = user.status
        user.status = new_status
        await db.flush()

        await audit_service.log_event(
            db=db,
            action="USER_ROLE_CHANGED",
            actor_user_id=actor.user_id,
            hospital_id=user.hospital_id,
            resource_type="USER",
            resource_id=user.id,
            metadata={"old_status": old_status.value, "new_status": new_status.value},
        )
        await db.commit()
        await db.refresh(user)
        return user


user_service = UserService()
