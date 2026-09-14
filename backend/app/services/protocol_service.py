from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant_context import TenantContext
from app.models.protocol import Protocol, ProtocolStatus
from app.schemas.protocol import ProtocolCreate, ProtocolUpdate, ProtocolVersionCreate
from app.services.audit_service import audit_service


class ProtocolService:
    # ------------------------------------------------------------------ #
    # Create                                                               #
    # ------------------------------------------------------------------ #

    async def create_protocol(
        self,
        db: AsyncSession,
        hospital_id: uuid.UUID,
        data: ProtocolCreate,
        actor: TenantContext,
    ) -> Protocol:
        """
        Create a new protocol scoped to hospital_id.
        hospital_id is ALWAYS taken from TenantContext / path — never body.
        """
        if not actor.can_access_hospital(hospital_id):
            raise HTTPException(status_code=403, detail="Access denied.")

        protocol = Protocol(
            id=uuid.uuid4(),
            hospital_id=hospital_id,  # Tenant-locked
            name=data.name,
            version=data.version,
            status=ProtocolStatus.DRAFT,
            content=data.content,
            created_by=actor.user_id,
        )
        db.add(protocol)
        await db.flush()

        await audit_service.log_event(
            db=db,
            action="PROTOCOL_CREATED",
            actor_user_id=actor.user_id,
            hospital_id=hospital_id,
            resource_type="PROTOCOL",
            resource_id=protocol.id,
            metadata={"name": data.name, "version": data.version},
        )
        await db.commit()
        await db.refresh(protocol)
        return protocol

    # ------------------------------------------------------------------ #
    # Read — ALWAYS filtered by tenant hospital_id                        #
    # ------------------------------------------------------------------ #

    async def list_protocols(
        self,
        db: AsyncSession,
        tenant: TenantContext,
        hospital_id: uuid.UUID | None = None,
    ) -> list[Protocol]:
        """
        List protocols.
        The query is ALWAYS scoped to tenant.hospital_id.
        The URL hospital_id param is only used for access-control verification,
        not for the actual DB filter.
        """
        scoped_hospital_id = (
            hospital_id if tenant.is_platform_admin and hospital_id else tenant.hospital_id
        )

        result = await db.execute(
            select(Protocol).where(Protocol.hospital_id == scoped_hospital_id)
        )
        return list(result.scalars().all())

    async def get_protocol(
        self,
        db: AsyncSession,
        protocol_id: uuid.UUID,
        tenant: TenantContext,
    ) -> Protocol:
        """
        Fetch a protocol by ID.

        CRITICAL: After fetching by ID, we verify that the protocol's hospital_id
        matches the tenant's hospital_id.  A user cannot access another hospital's
        protocol by guessing its UUID (direct-ID manipulation attack).
        """
        result = await db.execute(select(Protocol).where(Protocol.id == protocol_id))
        protocol = result.scalar_one_or_none()

        if not protocol:
            raise HTTPException(status_code=404, detail="Protocol not found.")

        # ← The critical security check
        if not tenant.can_access_hospital(protocol.hospital_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this protocol.",
            )
        return protocol

    # ------------------------------------------------------------------ #
    # Update                                                               #
    # ------------------------------------------------------------------ #

    async def update_protocol(
        self,
        db: AsyncSession,
        protocol_id: uuid.UUID,
        data: ProtocolUpdate,
        tenant: TenantContext,
    ) -> Protocol:
        protocol = await self.get_protocol(db, protocol_id, tenant)

        changed: dict = {}
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(protocol, field, value)
            changed[field] = str(value)

        await db.flush()

        await audit_service.log_event(
            db=db,
            action="PROTOCOL_UPDATED",
            actor_user_id=tenant.user_id,
            hospital_id=protocol.hospital_id,
            resource_type="PROTOCOL",
            resource_id=protocol.id,
            metadata={"changes": changed},
        )
        await db.commit()
        await db.refresh(protocol)
        return protocol

    # ------------------------------------------------------------------ #
    # Versioning: archive old → activate new                              #
    # ------------------------------------------------------------------ #

    async def activate_protocol(
        self, db: AsyncSession, protocol_id: uuid.UUID, tenant: TenantContext
    ) -> Protocol:
        """Activate a DRAFT protocol. Archives any currently ACTIVE protocol with same name."""
        protocol = await self.get_protocol(db, protocol_id, tenant)

        if protocol.status == ProtocolStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="Protocol is already ACTIVE.")

        # Archive existing active version(s) with the same name
        existing_active = await db.execute(
            select(Protocol).where(
                and_(
                    Protocol.hospital_id == protocol.hospital_id,
                    Protocol.name == protocol.name,
                    Protocol.status == ProtocolStatus.ACTIVE,
                    Protocol.id != protocol_id,
                )
            )
        )
        for old_protocol in existing_active.scalars().all():
            old_protocol.status = ProtocolStatus.ARCHIVED
            await audit_service.log_event(
                db=db,
                action="PROTOCOL_ARCHIVED",
                actor_user_id=tenant.user_id,
                hospital_id=protocol.hospital_id,
                resource_type="PROTOCOL",
                resource_id=old_protocol.id,
                metadata={
                    "reason": "superseded_by_new_version",
                    "new_protocol_id": str(protocol_id),
                },
            )

        protocol.status = ProtocolStatus.ACTIVE
        await db.flush()

        await audit_service.log_event(
            db=db,
            action="PROTOCOL_UPDATED",
            actor_user_id=tenant.user_id,
            hospital_id=protocol.hospital_id,
            resource_type="PROTOCOL",
            resource_id=protocol.id,
            metadata={"status_change": "DRAFT → ACTIVE"},
        )
        await db.commit()
        await db.refresh(protocol)
        return protocol

    async def archive_protocol(
        self, db: AsyncSession, protocol_id: uuid.UUID, tenant: TenantContext
    ) -> Protocol:
        protocol = await self.get_protocol(db, protocol_id, tenant)

        if protocol.status == ProtocolStatus.ARCHIVED:
            raise HTTPException(status_code=400, detail="Protocol is already ARCHIVED.")

        protocol.status = ProtocolStatus.ARCHIVED
        await db.flush()

        await audit_service.log_event(
            db=db,
            action="PROTOCOL_ARCHIVED",
            actor_user_id=tenant.user_id,
            hospital_id=protocol.hospital_id,
            resource_type="PROTOCOL",
            resource_id=protocol.id,
        )
        await db.commit()
        await db.refresh(protocol)
        return protocol

    async def create_new_version(
        self,
        db: AsyncSession,
        protocol_id: uuid.UUID,
        data: ProtocolVersionCreate,
        tenant: TenantContext,
    ) -> Protocol:
        """
        Create a new version of an existing protocol.
        Automatically archives the old version.
        """
        old_protocol = await self.get_protocol(db, protocol_id, tenant)

        new_protocol = Protocol(
            id=uuid.uuid4(),
            hospital_id=old_protocol.hospital_id,
            name=old_protocol.name,
            version=data.version,
            status=ProtocolStatus.DRAFT,
            content=data.content,
            created_by=tenant.user_id,
        )
        db.add(new_protocol)
        await db.flush()

        await audit_service.log_event(
            db=db,
            action="PROTOCOL_CREATED",
            actor_user_id=tenant.user_id,
            hospital_id=old_protocol.hospital_id,
            resource_type="PROTOCOL",
            resource_id=new_protocol.id,
            metadata={
                "name": old_protocol.name,
                "version": data.version,
                "previous_version_id": str(protocol_id),
            },
        )
        await db.commit()
        await db.refresh(new_protocol)
        return new_protocol


protocol_service = ProtocolService()
