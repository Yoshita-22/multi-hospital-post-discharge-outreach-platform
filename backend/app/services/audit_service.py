from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


class AuditService:
    """
    Central service for writing audit log entries.

    Every important action should call log_event() to produce a traceable record.
    """

    async def log_event(
        self,
        db: AsyncSession,
        action: str,
        actor_user_id: uuid.UUID | None = None,
        hospital_id: uuid.UUID | None = None,
        resource_type: str | None = None,
        resource_id: uuid.UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        """
        Create an immutable audit log entry.

        Args:
            db:              AsyncSession (caller owns commit)
            action:          e.g. HOSPITAL_CREATED, PROTOCOL_ARCHIVED
            actor_user_id:   User who triggered the event
            hospital_id:     Hospital context (None for platform-level actions)
            resource_type:   e.g. HOSPITAL, PROTOCOL, USER
            resource_id:     UUID of the affected resource
            metadata:        Extra contextual data (e.g. old/new values)
        """
        entry = AuditLog(
            id=uuid.uuid4(),
            actor_user_id=actor_user_id,
            hospital_id=hospital_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata_=metadata or {},
        )
        db.add(entry)
        # Caller is responsible for commit — we just flush to get the ID
        await db.flush()
        return entry


audit_service = AuditService()
