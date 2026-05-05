import uuid
import pytest
from datetime import datetime, timedelta

from breaking_law.timekeeping.time_service import TimeService
from breaking_law.infra.models import TimeEntry, TimeEntryStatus, LawFirm, User, Matter, Client
from breaking_law.identity.security import PasswordHasher


@pytest.mark.asyncio
async def test_start_timer(db_session):
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

    service = TimeService(db_session)
    entry = await service.start_timer(
        user_id=user.id,
        law_firm_id=firm.id,
        description="Research on contract law",
    )
    assert entry.id is not None
    assert entry.user_id == user.id
    assert entry.law_firm_id == firm.id
    assert entry.status == TimeEntryStatus.draft
    assert entry.started_at is not None
    assert entry.ended_at is None


@pytest.mark.asyncio
async def test_stop_timer(db_session):
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

    service = TimeService(db_session)
    entry = await service.start_timer(
        user_id=user.id,
        law_firm_id=firm.id,
        description="Drafting motion",
    )
    await db_session.commit()

    # Wait a tiny bit so duration is non-zero
    import asyncio
    await asyncio.sleep(0.05)

    stopped = await service.stop_timer(entry.id)
    assert stopped is not None
    assert stopped.ended_at is not None
    assert stopped.duration_minutes is not None
    assert stopped.duration_minutes >= 0


@pytest.mark.asyncio
async def test_stop_timer_already_stopped_raises(db_session):
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

    service = TimeService(db_session)
    entry = await service.start_timer(user_id=user.id, law_firm_id=firm.id)
    await service.stop_timer(entry.id)
    await db_session.commit()

    with pytest.raises(ValueError, match="already stopped"):
        await service.stop_timer(entry.id)


@pytest.mark.asyncio
async def test_list_entries_with_filters(db_session):
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

    service = TimeService(db_session)
    await service.start_timer(user_id=user.id, law_firm_id=firm.id, description="Task A")
    await service.start_timer(user_id=user.id, law_firm_id=firm.id, description="Task B")
    await db_session.commit()

    entries = await service.list_entries(law_firm_id=firm.id)
    assert len(entries) == 2

    entries = await service.list_entries(law_firm_id=firm.id, user_id=user.id)
    assert len(entries) == 2


@pytest.mark.asyncio
async def test_submit_and_approve_entry(db_session):
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

    service = TimeService(db_session)
    entry = await service.start_timer(user_id=user.id, law_firm_id=firm.id)
    await service.stop_timer(entry.id)
    await db_session.commit()

    submitted = await service.submit_for_approval(entry.id)
    assert submitted.status == TimeEntryStatus.submitted

    approved = await service.approve_entry(entry.id)
    assert approved.status == TimeEntryStatus.approved


@pytest.mark.asyncio
async def test_submit_non_draft_raises(db_session):
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

    service = TimeService(db_session)
    entry = await service.start_timer(user_id=user.id, law_firm_id=firm.id)
    await service.stop_timer(entry.id)
    await service.submit_for_approval(entry.id)
    await db_session.commit()

    with pytest.raises(ValueError, match="Only draft entries can be submitted"):
        await service.submit_for_approval(entry.id)


@pytest.mark.asyncio
async def test_approve_non_submitted_raises(db_session):
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

    service = TimeService(db_session)
    entry = await service.start_timer(user_id=user.id, law_firm_id=firm.id)
    await db_session.commit()

    with pytest.raises(ValueError, match="Only submitted entries can be approved"):
        await service.approve_entry(entry.id)


@pytest.mark.asyncio
async def test_generate_report(db_session):
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

    service = TimeService(db_session)
    entry1 = await service.start_timer(user_id=user.id, law_firm_id=firm.id, description="Billable work")
    entry1.duration_minutes = 120
    entry1.billable = True
    entry1.status = TimeEntryStatus.approved

    entry2 = await service.start_timer(user_id=user.id, law_firm_id=firm.id, description="Non-billable")
    entry2.duration_minutes = 60
    entry2.billable = False
    entry2.status = TimeEntryStatus.approved
    await db_session.commit()

    report = await service.generate_report(law_firm_id=firm.id)
    assert report["total_hours"] == 3.0
    assert report["billable_hours"] == 2.0
    assert report["total_entries"] == 2
