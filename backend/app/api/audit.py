import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import assert_hospital_access, get_db, get_tenant_context
from app.core.tenant_context import TenantContext
from app.models.audit_log import AuditLog
from app.schemas.audit import AuditLogResponse

router = APIRouter(prefix="/hospitals", tags=["Audit"])


@router.get(
    "/{hospital_id}/audit-logs",
    response_model=list[AuditLogResponse],
    summary="List audit logs for a hospital",
)
async def list_audit_logs(
    hospital_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
    limit: int = 100,
    offset: int = 0,
) -> list[AuditLogResponse]:
    assert_hospital_access(tenant, hospital_id)
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.hospital_id == hospital_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    logs = list(result.scalars().all())
    return [AuditLogResponse.model_validate(log) for log in logs]
