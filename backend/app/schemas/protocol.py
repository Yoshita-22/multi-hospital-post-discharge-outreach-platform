import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.protocol import ProtocolStatus


class ProtocolCreate(BaseModel):
    name: str
    version: str = "1.0"
    content: dict

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Cardiac Post Discharge",
                "version": "1.0",
                "content": {
                    "questions": [
                        "How are you feeling today?",
                        "Are you experiencing chest pain?",
                        "Are you experiencing difficulty breathing?",
                    ],
                    "red_flags": [
                        "severe chest pain",
                        "difficulty breathing",
                        "fainting",
                    ],
                },
            }
        }
    }


class ProtocolUpdate(BaseModel):
    name: str | None = None
    content: dict | None = None


class ProtocolResponse(BaseModel):
    id: uuid.UUID
    hospital_id: uuid.UUID
    name: str
    version: str
    status: ProtocolStatus
    content: dict
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProtocolVersionCreate(BaseModel):
    """Create a new version of an existing protocol (archives the old one)."""

    version: str
    content: dict
