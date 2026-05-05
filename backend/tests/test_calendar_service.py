import uuid
import pytest
from datetime import datetime, timedelta, UTC

from breaking_law.timekeeping.calendar_service import CalendarService
from breaking_law.infra.models import Deadline, DeadlineStatus, TimeEntry, TimeEntryStatus, LawFirm, User
from breaking_law.identity.security import PasswordHasher


@pytest.mark.asyncio
async def test_export_deadlines_to_ical(db_session):
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

    deadline = Deadline(
        law_firm_id=firm.id,
        created_by=user.id,
        title="File Motion",
        description="Motion to dismiss",
        due_date=datetime.now(UTC) + timedelta(days=3),
        status=DeadlineStatus.pending,
    )
    db_session.add(deadline)
    await db_session.commit()

    service = CalendarService(db_session)
    ical = await service.export_deadlines_to_ical(firm.id)
    assert "BEGIN:VCALENDAR" in ical
    assert "VERSION:2.0" in ical
    assert "BEGIN:VEVENT" in ical
    assert "File Motion" in ical
    assert "END:VCALENDAR" in ical


@pytest.mark.asyncio
async def test_export_time_entries_to_ical(db_session):
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

    entry = TimeEntry(
        law_firm_id=firm.id,
        user_id=user.id,
        description="Research on contract law",
        started_at=datetime.now(UTC) - timedelta(hours=2),
        ended_at=datetime.now(UTC) - timedelta(hours=1),
        duration_minutes=60,
        status=TimeEntryStatus.approved,
    )
    db_session.add(entry)
    await db_session.commit()

    service = CalendarService(db_session)
    ical = await service.export_time_entries_to_ical(firm.id)
    assert "BEGIN:VCALENDAR" in ical
    assert "BEGIN:VEVENT" in ical
    assert "Research on contract law" in ical
    assert "END:VCALENDAR" in ical


@pytest.mark.asyncio
async def test_export_matter_to_ical(db_session):
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

    matter_id = uuid.uuid4()

    deadline = Deadline(
        law_firm_id=firm.id,
        created_by=user.id,
        matter_id=matter_id,
        title="Matter Deadline",
        due_date=datetime.now(UTC) + timedelta(days=2),
        status=DeadlineStatus.pending,
    )
    db_session.add(deadline)

    entry = TimeEntry(
        law_firm_id=firm.id,
        user_id=user.id,
        matter_id=matter_id,
        description="Matter work",
        started_at=datetime.now(UTC) - timedelta(hours=1),
        ended_at=datetime.now(UTC),
        duration_minutes=60,
        status=TimeEntryStatus.draft,
    )
    db_session.add(entry)
    await db_session.commit()

    service = CalendarService(db_session)
    ical = await service.export_matter_to_ical(firm.id, matter_id)
    assert "BEGIN:VCALENDAR" in ical
    assert "Matter Deadline" in ical
    assert "Matter work" in ical
    assert "END:VCALENDAR" in ical


@pytest.mark.asyncio
async def test_export_deadlines_date_range(db_session):
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

    deadline = Deadline(
        law_firm_id=firm.id,
        created_by=user.id,
        title="Future Deadline",
        due_date=datetime.now(UTC) + timedelta(days=30),
        status=DeadlineStatus.pending,
    )
    db_session.add(deadline)
    await db_session.commit()

    service = CalendarService(db_session)
    # Filter should exclude the far-future deadline
    ical = await service.export_deadlines_to_ical(
        firm.id,
        date_from=datetime.now(UTC),
        date_to=datetime.now(UTC) + timedelta(days=7),
    )
    assert "Future Deadline" not in ical


def test_format_ical_datetime():
    dt = datetime(2024, 6, 15, 10, 30, 0, tzinfo=UTC)
    formatted = CalendarService._format_ical_datetime(dt)
    assert formatted == "20240615T103000Z"


def test_escape_ical_text():
    assert CalendarService._escape_ical_text("a;b,c") == "a\\;b\\,c"
    assert CalendarService._escape_ical_text("line1\nline2") == "line1\\nline2"


def test_wrap_ical_calendar():
    events = ["BEGIN:VEVENT\r\nUID:1\r\nEND:VEVENT"]
    wrapped = CalendarService._wrap_ical_calendar(events)
    assert "BEGIN:VCALENDAR" in wrapped
    assert "VERSION:2.0" in wrapped
    assert "BEGIN:VEVENT" in wrapped
    assert "END:VCALENDAR" in wrapped
