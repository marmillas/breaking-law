"""
CRM schemas for clients, matters, and notifications.
"""

import uuid
from typing import Optional

from pydantic import BaseModel, EmailStr


class ClientCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None


class ClientOut(BaseModel):
    id: uuid.UUID
    law_firm_id: uuid.UUID
    name: str
    email: str
    phone: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class MatterCreate(BaseModel):
    client_id: uuid.UUID
    title: str
    description: Optional[str] = None
    status: str = "open"


class MatterUpdate(BaseModel):
    client_id: Optional[uuid.UUID] = None
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class MatterOut(BaseModel):
    id: uuid.UUID
    law_firm_id: uuid.UUID
    client_id: uuid.UUID
    title: str
    description: Optional[str] = None
    status: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class NotificationOut(BaseModel):
    id: uuid.UUID
    law_firm_id: uuid.UUID
    user_id: uuid.UUID
    deadline_id: Optional[uuid.UUID] = None
    title: str
    message: str
    priority: str
    read: bool
    created_at: str

    class Config:
        from_attributes = True


class MarkReadResponse(BaseModel):
    message: str


class MarkAllReadResponse(BaseModel):
    marked_count: int
