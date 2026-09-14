from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_tenant_context
from app.core.tenant_context import TenantContext
from app.schemas.scheduler import SchedulerRunResult
from app.services.scheduler_service import queue_scheduler

router = APIRouter(prefix="/scheduler", tags=["Scheduler"])

@router.post(
    "/run",
    response_model=SchedulerRunResult,
    status_code=status.HTTP_200_OK,
    summary="Run the Outbound Queue Scheduler (Tenant Scoped)"
)
async def run_scheduler(
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    """
    Given all queued outbound jobs for the current tenant's hospital, 
    determine which patients are callable now, 
    select the best patients for currently available call capacity, 
    atomically claim those queue items, and hand them off to the call-worker layer.
    """
    return await queue_scheduler.run_once(db, tenant)
