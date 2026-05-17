import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=1, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class MobileLoginRequest(LoginRequest):
    device_name: str | None = Field(default=None, max_length=255)


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    user: UserOut


class MobileLoginResponse(AuthResponse):
    token: str
    expires_at: datetime


class MobileCapabilities(BaseModel):
    ai_enabled: bool
    embeddings_enabled: bool
    upload_enabled: bool
    mobile_api_version: int


class MobileBootstrapResponse(AuthResponse):
    capabilities: MobileCapabilities
