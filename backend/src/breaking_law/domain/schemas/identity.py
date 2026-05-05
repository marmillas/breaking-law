"""
Identity schemas for authentication and OAuth.
"""

import uuid
from typing import Optional

from pydantic import BaseModel, EmailStr


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    law_firm_id: uuid.UUID
    role: str = "assistant"


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    law_firm_id: uuid.UUID
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class LawFirmCreate(BaseModel):
    name: str
    timezone: str = "Europe/Madrid"


class LawFirmOut(BaseModel):
    id: uuid.UUID
    name: str
    timezone: str

    class Config:
        from_attributes = True


class LogoutRequest(BaseModel):
    refresh_token: str


class ConnectionOut(BaseModel):
    id: uuid.UUID
    provider: str
    email_address: str
    scopes: str
    connected_at: str
    last_synced_at: Optional[str] = None

    class Config:
        from_attributes = True
