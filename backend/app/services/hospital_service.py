from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant_context import TenantContext
from app.models.configuration import HospitalConfiguration
from app.models.hospital import Hospital, HospitalStatus
from app.schemas.configuration import ConfigurationUpdate
from app.schemas.hospital import HospitalCreate, HospitalUpdate
from app.services.audit_service import audit_service


class HospitalService:
    # ------------------------------------------------------------------ #
    # Create                                                               #
    # ------------------------------------------------------------------ #

    async def create_hospital(
        self,
        db: AsyncSession,
        data: HospitalCreate,
        actor: TenantContext,
    ) -> Hospital:
        """
        Create a hospital with a default configuration.
        Only PLATFORM_ADMIN may call this (enforced at the API layer).
        """
        hospital = Hospital(
            id=uuid.uuid4(),
            name=data.name,
            contact_email=str(data.contact_email),
            contact_phone=data.contact_phone,
            timezone=data.timezone,
            status=HospitalStatus.ONBOARDING,
        )
        db.add(hospital)
        await db.flush()  # populate hospital.id

        # Auto-create a default configuration
        config = HospitalConfiguration(
            id=uuid.uuid4(),
            hospital_id=hospital.id,
            calling_start_time="09:00",
            calling_end_time="18:00",
            max_calling_capacity=10,
            max_retries=3,
        )
        db.add(config)
        await db.flush()

        await audit_service.log_event(
            db=db,
            action="HOSPITAL_CREATED",
            actor_user_id=actor.user_id,
            hospital_id=hospital.id,
            resource_type="HOSPITAL",
            resource_id=hospital.id,
            metadata={"name": hospital.name, "timezone": hospital.timezone},
        )

        await db.commit()
        await db.refresh(hospital)
        return hospital

    # ------------------------------------------------------------------ #
    # Read                                                                  #
    # ------------------------------------------------------------------ #

    async def get_hospital(
        self,
        db: AsyncSession,
        hospital_id: uuid.UUID,
        actor: TenantContext,
    ) -> Hospital:
        result = await db.execute(select(Hospital).where(Hospital.id == hospital_id))
        hospital = result.scalar_one_or_none()
        if not hospital:
            raise HTTPException(status_code=404, detail="Hospital not found.")
        if not actor.can_access_hospital(hospital_id):
            raise HTTPException(status_code=403, detail="Access denied.")
        return hospital

    async def list_hospitals(self, db: AsyncSession, actor: TenantContext) -> list[Hospital]:
        """PLATFORM_ADMIN sees all; others only see their own."""
        if actor.is_platform_admin:
            result = await db.execute(select(Hospital))
        else:
            result = await db.execute(
                select(Hospital).where(Hospital.id == actor.hospital_id)
            )
        return list(result.scalars().all())

    # ------------------------------------------------------------------ #
    # Update                                                               #
    # ------------------------------------------------------------------ #

    async def update_hospital(
        self,
        db: AsyncSession,
        hospital_id: uuid.UUID,
        data: HospitalUpdate,
        actor: TenantContext,
    ) -> Hospital:
        hospital = await self.get_hospital(db, hospital_id, actor)
        changed: dict = {}

        for field, value in data.model_dump(exclude_none=True).items():
            setattr(hospital, field, value)
            changed[field] = str(value)

        await db.flush()

        await audit_service.log_event(
            db=db,
            action="HOSPITAL_UPDATED",
            actor_user_id=actor.user_id,
            hospital_id=hospital_id,
            resource_type="HOSPITAL",
            resource_id=hospital_id,
            metadata={"changes": changed},
        )
        await db.commit()
        await db.refresh(hospital)
        return hospital

    # ------------------------------------------------------------------ #
    # Configuration                                                        #
    # ------------------------------------------------------------------ #

    async def update_configuration(
        self,
        db: AsyncSession,
        hospital_id: uuid.UUID,
        data: ConfigurationUpdate,
        actor: TenantContext,
    ) -> HospitalConfiguration:
        if not actor.can_access_hospital(hospital_id):
            raise HTTPException(status_code=403, detail="Access denied.")

        result = await db.execute(
            select(HospitalConfiguration).where(
                HospitalConfiguration.hospital_id == hospital_id
            )
        )
        config = result.scalar_one_or_none()
        if not config:
            raise HTTPException(status_code=404, detail="Configuration not found.")

        changed: dict = {}
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(config, field, value)
            changed[field] = str(value)

        await db.flush()

        await audit_service.log_event(
            db=db,
            action="CONFIGURATION_UPDATED",
            actor_user_id=actor.user_id,
            hospital_id=hospital_id,
            resource_type="HOSPITAL_CONFIGURATION",
            resource_id=config.id,
            metadata={"changes": changed},
        )
        await db.commit()
        await db.refresh(config)
        return config

    async def get_configuration(
        self,
        db: AsyncSession,
        hospital_id: uuid.UUID,
        actor: TenantContext,
    ) -> HospitalConfiguration:
        if not actor.can_access_hospital(hospital_id):
            raise HTTPException(status_code=403, detail="Access denied.")
        result = await db.execute(
            select(HospitalConfiguration).where(
                HospitalConfiguration.hospital_id == hospital_id
            )
        )
        config = result.scalar_one_or_none()
        if not config:
            raise HTTPException(status_code=404, detail="Configuration not found.")
        return config


hospital_service = HospitalService()
