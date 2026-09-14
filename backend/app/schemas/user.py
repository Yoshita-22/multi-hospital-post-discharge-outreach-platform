import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.models.user import UserRole, UserStatus


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.HOSPITAL_ADMIN

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Dr. Smith",
                "email": "smith@hospital.com",
                "password": "SecurePass123!",
                "role": "HOSPITAL_ADMIN",
            }
        }
    }


class UserResponse(BaseModel):
    id: uuid.UUID
    hospital_id: uuid.UUID | None
    name: str
    email: str
    role: UserRole
    status: UserStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserStatusUpdate(BaseModel):
    status: UserStatus
