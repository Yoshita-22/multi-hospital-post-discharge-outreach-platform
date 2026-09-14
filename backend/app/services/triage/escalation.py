import logging
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.triage import TriageResult
from app.ehr.service import healthcare_data_service
from app.ehr.schemas import TaskCreate, CommunicationCreate
from app.core.tenant_context import TenantContext

logger = logging.getLogger(__name__)

class EscalationService:
    async def escalate(self, db: AsyncSession, triage_result: TriageResult, tenant: TenantContext) -> dict:
        ehr_status = "SUCCESS"
        resource_id = None
        action_taken = None
        
        if triage_result.triage_level == "URGENT":
            # Create Urgent EHR Task and Communication
            task_data = TaskCreate(
                task_type="Escalation",
                description=f"URGENT clinician review required. Reason: {triage_result.reasoning_summary}"
            )
            task = await healthcare_data_service.create_task(db, triage_result.patient_id, task_data, tenant)
            
            comm_data = CommunicationCreate(
                communication_type="Alert",
                content="Automated triage identified an urgent concern."
            )
            await healthcare_data_service.create_communication(db, triage_result.patient_id, comm_data, tenant)
            
            action_taken = "CREATE_URGENT_TASK"
            resource_id = task.id
            
        elif triage_result.triage_level == "ATTENTION":
            # Create Routine Review Task
            task_data = TaskCreate(
                task_type="Review",
                description=f"Clinician review required. Reason: {triage_result.reasoning_summary}"
            )
            task = await healthcare_data_service.create_task(db, triage_result.patient_id, task_data, tenant)
            
            action_taken = "CREATE_REVIEW_TASK"
            resource_id = task.id
            
        else:
            # Routine - Log Communication
            comm_data = CommunicationCreate(
                communication_type="Outreach Log",
                content="Post-discharge outreach completed. No concerning symptoms reported."
            )
            comm = await healthcare_data_service.create_communication(db, triage_result.patient_id, comm_data, tenant)
            
            action_taken = "LOG_COMMUNICATION"
            resource_id = comm.id
            
        return {
            "action": action_taken,
            "status": ehr_status,
            "resource_id": resource_id
        }
