from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    model_config = {"json_schema_extra": {"example": {"email": "admin@platform.com", "password": "secret"}}}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
