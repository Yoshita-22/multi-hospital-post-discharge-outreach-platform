from pydantic import BaseModel
from typing import List
from uuid import UUID

class QueueCreationResult(BaseModel):
    campaign_id: UUID
    queued_count: int
    skipped_existing_count: int
    scheduled_count: int
