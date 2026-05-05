"""
Timekeeping schemas for time entries, deadlines, and calendar.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from breaking_law.infra.models import DeadlinePriority, DeadlineStatus, TimeEntryStatus


class StartTimerRequest(BaseModel):
    matter_id: Optional[uuid.UUID] = None
    client_id: Optional[uuid.UUID] = None
    description: Optional[str] = None


class TimeEntryOut(BaseModel):
    id: uuid.UUID
    law_firm_id: uuid.UUID
    user_id: uuid.UUID
    matter_id: Optional[uuid.UUID] = None
    client_id: Optional[uuid.UUID] = None
    description: Optional[str] = None
    started_at: str
    ended_at: Optional[str] = None
    duration_minutes: Optional[int] = None
    billable: bool
    billing_rate: Optional[float] = None
    status: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ReportOut(BaseModel):
    total_hours: float
    billable_hours: float
    total_entries: int
    matter_breakdown: dict


class DeadlineCreate(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: datetime
    priority: DeadlinePriority = DeadlinePriority.medium
    matter_id: Optional[uuid.UUID] = None


class DeadlineOut(BaseModel):
    id: uuid.UUID
    law_firm_id: uuid.UUID
    matter_id: Optional[uuid.UUID] = None
    created_by: uuid.UUID
    title: str
    description: Optional[str] = None
    due_date: str
    priority: str
    status: str
    notification_sent_at: Optional[str] = None
    acknowledged_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True
