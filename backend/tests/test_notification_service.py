import uuid
import pytest
from datetime import datetime

from breaking_law.crm.service import NotificationService
from breaking_law.infra.models import Notification, DeadlinePriority, LawFirm, User
from breaking_law.identity.security import PasswordHasher


@pytest.mark.asyncio
async def test_create_notification(db_session):
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

    service = NotificationService(db_session)
    notification = await service.create_notification(
        law_firm_id=firm.id,
        user_id=user.id,
        title="Test Notification",
        message="This is a test",
        priority=DeadlinePriority.high,
    )
    assert notification.id is not None
    assert notification.read is False
    assert notification.priority == DeadlinePriority.high


@pytest.mark.asyncio
async def test_list_unread(db_session):
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

    service = NotificationService(db_session)
    await service.create_notification(firm.id, user.id, "Unread 1", "Msg 1")
    await service.create_notification(firm.id, user.id, "Unread 2", "Msg 2")
    await db_session.commit()

    unread = await service.list_unread(user_id=user.id, law_firm_id=firm.id)
    assert len(unread) == 2


@pytest.mark.asyncio
async def test_mark_read(db_session):
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

    service = NotificationService(db_session)
    notification = await service.create_notification(firm.id, user.id, "Test", "Msg")
    await db_session.commit()

    updated = await service.mark_read(notification.id, user.id)
    assert updated.read is True


@pytest.mark.asyncio
async def test_mark_all_read(db_session):
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

    service = NotificationService(db_session)
    await service.create_notification(firm.id, user.id, "A", "Msg A")
    await service.create_notification(firm.id, user.id, "B", "Msg B")
    await db_session.commit()

    count = await service.mark_all_read(user.id, firm.id)
    assert count == 2

    unread = await service.list_unread(user_id=user.id, law_firm_id=firm.id)
    assert len(unread) == 0


@pytest.mark.asyncio
async def test_get_urgent_actions(db_session):
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

    service = NotificationService(db_session)
    await service.create_notification(firm.id, user.id, "Critical", "Msg", DeadlinePriority.critical)
    await service.create_notification(firm.id, user.id, "High", "Msg", DeadlinePriority.high)
    await service.create_notification(firm.id, user.id, "Low", "Msg", DeadlinePriority.low)
    await db_session.commit()

    urgent = await service.get_urgent_actions(user_id=user.id, law_firm_id=firm.id)
    assert len(urgent) == 2
    priorities = {n.priority for n in urgent}
    assert priorities == {DeadlinePriority.critical, DeadlinePriority.high}


@pytest.mark.asyncio
async def test_mark_read_not_found(db_session):
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

    service = NotificationService(db_session)
    result = await service.mark_read(uuid.uuid4(), user.id)
    assert result is None
