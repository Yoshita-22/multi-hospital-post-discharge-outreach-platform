# Import all models so SQLAlchemy registers them with Base.metadata
# Alembic and tests can import this module to ensure all tables are known.

from app.models.hospital import Hospital, HospitalStatus  # noqa: F401
from app.models.user import User, UserRole, UserStatus  # noqa: F401
from app.models.configuration import HospitalConfiguration  # noqa: F401
from app.models.protocol import Protocol, ProtocolStatus  # noqa: F401
from app.models.knowledge_document import KnowledgeDocument, KnowledgeDocumentStatus  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.ehr import (  # noqa: F401
    Patient, Encounter, Discharge, Condition,
    Medication, Observation, CarePlan, Communication, Task
)
from app.models.campaign import Campaign, CampaignStatus, CampaignValidationStatus  # noqa: F401
from app.models.campaign_patient import CampaignPatient  # noqa: F401
from app.models.outbound_queue import OutboundQueue, QueueItemStatus  # noqa: F401
from app.models.outbound_call import OutboundCall  # noqa: F401
from app.models.triage import TriageResult  # noqa: F401

__all__ = [
    "Hospital",
    "HospitalStatus",
    "User",
    "UserRole",
    "UserStatus",
    "HospitalConfiguration",
    "Protocol",
    "ProtocolStatus",
    "KnowledgeDocument",
    "KnowledgeDocumentStatus",
    "AuditLog",
    "Patient",
    "Encounter",
    "Discharge",
    "Condition",
    "Medication",
    "Observation",
    "CarePlan",
    "Communication",
    "Task",
    "Campaign",
    "CampaignStatus",
    "CampaignValidationStatus",
    "CampaignPatient",
    "OutboundQueue",
    "QueueItemStatus",
    "OutboundCall",
    "TriageResult",
]
