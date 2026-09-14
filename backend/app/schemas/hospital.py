import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator

from app.models.hospital import HospitalStatus


class HospitalCreate(BaseModel):
    name: str
    contact_email: EmailStr
    contact_phone: str | None = None
    timezone: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Apollo Hospital",
                "contact_email": "contact@apollo.com",
                "contact_phone": "+91-9999999999",
                "timezone": "Asia/Kolkata",
            }
        }
    }


class HospitalUpdate(BaseModel):
    name: str | None = None
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    timezone: str | None = None
    status: HospitalStatus | None = None


class HospitalResponse(BaseModel):
    id: uuid.UUID
    name: str
    contact_email: str
    contact_phone: str | None
    timezone: str
    status: HospitalStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReadinessCheck(BaseModel):
    name: str
    passed: bool
    message: str


class ReadinessReport(BaseModel):
    hospital_id: uuid.UUID
    ready: bool
    checks: list[ReadinessCheck]
