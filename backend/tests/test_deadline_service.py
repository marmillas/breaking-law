import uuid
import pytest
from datetime import datetime, timedelta, UTC

from breaking_law.timekeeping.deadline_service import DeadlineService
from breaking_law.infra.models import Deadline, DeadlineStatus, DeadlinePriority, LawFirm, User
from breaking_law.identity.security import PasswordHasher


@pytest.mark.asyncio
async def test_create_deadline(db_session):
    firm = LawFirm(name="Test Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(
        email="user@example.com",
        full_name="Test User",
        law_firm_id=firm.id,
        hashed_password=PasswordHasher.hash_password("pass"),
        role="assistant",
    )
    db_session.add(user)
    await db_session.flush()

    service = DeadlineService(db_session)
    due = datetime.now(UTC) + timedelta(days=3)
    deadline = await service.create_deadline(
        law_firm_id=firm.id,
        created_by=user.id,
        title="File motion",
        description="Motion to dismiss",
        due_date=due,
        priority=DeadlinePriority.high,
    )
    assert deadline.id is not None
    assert deadline.title == "File motion"
    assert deadline.status == DeadlineStatus.pending
    assert deadline.priority == DeadlinePriority.high


@pytest.mark.asyncio
async def test_list_deadlines_with_filters(db_session):
    firm = LawFirm(name="Test Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(
        email="user@example.com",
        full_name="Test User",
        law_firm_id=firm.id,
        hashed_password=PasswordHasher.hash_password("pass"),
        role="assistant",
    )
    db_session.add(user)
    await db_session.flush()

    service = DeadlineService(db_session)
    await service.create_deadline(firm.id, user.id, "Task A", due_date=datetime.now(UTC) + timedelta(days=1))
    await service.create_deadline(firm.id, user.id, "Task B", due_date=datetime.now(UTC) + timedelta(days=5))
    await db_session.commit()

    deadlines = await service.list_deadlines(firm.id)
    assert len(deadlines) == 2

    deadlines = await service.list_deadlines(firm.id, status=DeadlineStatus.pending)
    assert len(deadlines) == 2


@pytest.mark.asyncio
async def test_acknowledge_deadline(db_session):
    firm = LawFirm(name="Test Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(
        email="user@example.com",
        full_name="Test User",
        law_firm_id=firm.id,
        hashed_password=PasswordHasher.hash_password("pass"),
        role="assistant",
    )
    db_session.add(user)
    await db_session.flush()

    service = DeadlineService(db_session)
    deadline = await service.create_deadline(
        firm.id, user.id, "Task", due_date=datetime.now(UTC) + timedelta(days=1)
    )
    await db_session.commit()

    updated = await service.acknowledge(deadline.id, user.id)
    assert updated.status == DeadlineStatus.acknowledged
    assert updated.acknowledged_at is not None


@pytest.mark.asyncio
async def test_complete_deadline(db_session):
    firm = LawFirm(name="Test Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(
        email="user@example.com",
        full_name="Test User",
        law_firm_id=firm.id,
        hashed_password=PasswordHasher.hash_password("pass"),
        role="assistant",
    )
    db_session.add(user)
    await db_session.flush()

    service = DeadlineService(db_session)
    deadline = await service.create_deadline(
        firm.id, user.id, "Task", due_date=datetime.now(UTC) + timedelta(days=1)
    )
    await db_session.commit()

    updated = await service.complete(deadline.id)
    assert updated.status == DeadlineStatus.completed
    assert updated.completed_at is not None


@pytest.mark.asyncio
async def test_get_overdue(db_session):
    firm = LawFirm(name="Test Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(
        email="user@example.com",
        full_name="Test User",
        law_firm_id=firm.id,
        hashed_password=PasswordHasher.hash_password("pass"),
        role="assistant",
    )
    db_session.add(user)
    await db_session.flush()

    service = DeadlineService(db_session)
    overdue = await service.create_deadline(
        firm.id, user.id, "Overdue Task", due_date=datetime.now(UTC) - timedelta(days=1)
    )
    future = await service.create_deadline(
        firm.id, user.id, "Future Task", due_date=datetime.now(UTC) + timedelta(days=5)
    )
    completed = await service.create_deadline(
        firm.id, user.id, "Completed Task", due_date=datetime.now(UTC) - timedelta(days=2)
    )
    await service.complete(completed.id)
    await db_session.commit()

    overdue_list = await service.get_overdue(firm.id)
    assert len(overdue_list) == 1
    assert overdue_list[0].id == overdue.id


@pytest.mark.asyncio
async def test_get_upcoming(db_session):
    firm = LawFirm(name="Test Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(
        email="user@example.com",
        full_name="Test User",
        law_firm_id=firm.id,
        hashed_password=PasswordHasher.hash_password("pass"),
        role="assistant",
    )
    db_session.add(user)
    await db_session.flush()

    service = DeadlineService(db_session)
    upcoming = await service.create_deadline(
        firm.id, user.id, "Upcoming Task", due_date=datetime.now(UTC) + timedelta(days=2)
    )
    far_future = await service.create_deadline(
        firm.id, user.id, "Far Task", due_date=datetime.now(UTC) + timedelta(days=30)
    )
    await db_session.commit()

    upcoming_list = await service.get_upcoming(firm.id, days=7)
    assert len(upcoming_list) == 1
    assert upcoming_list[0].id == upcoming.id


@pytest.mark.asyncio
async def test_acknowledge_completed_raises(db_session):
    firm = LawFirm(name="Test Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(
        email="user@example.com",
        full_name="Test User",
        law_firm_id=firm.id,
        hashed_password=PasswordHasher.hash_password("pass"),
        role="assistant",
    )
    db_session.add(user)
    await db_session.flush()

    service = DeadlineService(db_session)
    deadline = await service.create_deadline(
        firm.id, user.id, "Task", due_date=datetime.now(UTC) + timedelta(days=1)
    )
    await service.complete(deadline.id)
    await db_session.commit()

    with pytest.raises(ValueError, match="Cannot acknowledge a completed deadline"):
        await service.acknowledge(deadline.id, user.id)
