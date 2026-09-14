import re
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator

from app.models.user import UserRole, UserStatus

_TIME_RE = re.compile(r"^\d{2}:\d{2}$")


class ConfigurationUpdate(BaseModel):
    calling_start_time: str | None = None
    calling_end_time: str | None = None
    max_calling_capacity: int | None = None
    max_retries: int | None = None
    notification_preferences: dict | None = None
    ehr_settings: dict | None = None

    @field_validator("calling_start_time", "calling_end_time", mode="before")
    @classmethod
    def validate_time_format(cls, v: str | None) -> str | None:
        if v is not None and not _TIME_RE.match(v):
            raise ValueError("Time must be in HH:MM format, e.g. '09:00'")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "calling_start_time": "09:00",
                "calling_end_time": "18:00",
                "max_calling_capacity": 10,
                "max_retries": 3,
            }
        }
    }


class ConfigurationResponse(BaseModel):
    id: uuid.UUID
    hospital_id: uuid.UUID
    calling_start_time: str
    calling_end_time: str
    max_calling_capacity: int
    max_retries: int
    notification_preferences: dict
    ehr_settings: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
