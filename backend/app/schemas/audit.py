import uuid
from datetime import datetime

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    hospital_id: uuid.UUID | None
    actor_user_id: uuid.UUID | None
    action: str
    resource_type: str | None
    resource_id: uuid.UUID | None
    metadata_: dict
    created_at: datetime

    model_config = {"from_attributes": True}
