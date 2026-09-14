import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.knowledge_document import KnowledgeDocumentStatus


class KnowledgeDocumentCreate(BaseModel):
    title: str
    content: str
    protocol_id: uuid.UUID | None = None
    version: str | None = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "Cardiac Care Guidelines",
                "content": "Post-discharge cardiac care involves...",
                "protocol_id": None,
                "version": "1.0",
            }
        }
    }


class KnowledgeDocumentResponse(BaseModel):
    id: uuid.UUID
    hospital_id: uuid.UUID
    protocol_id: uuid.UUID | None
    title: str
    content: str
    version: str | None
    status: KnowledgeDocumentStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeSearchRequest(BaseModel):
    query: str
    protocol_id: uuid.UUID | None = None
    limit: int = 10
