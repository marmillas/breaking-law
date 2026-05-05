import uuid
import pytest
from datetime import datetime, timedelta, UTC

from breaking_law.retention.service import RetentionService
from breaking_law.shared.audit import AuditService
from breaking_law.infra.models import Document, DocumentVersion, LawFirm, User
from breaking_law.identity.security import PasswordHasher


@pytest.mark.asyncio
async def test_apply_retention_policy_keep_forever(db_session):
    firm = LawFirm(name="Test Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(
        email="user@example.com",
        full_name="Test User",
        law_firm_id=firm.id,
        hashed_password=PasswordHasher.hash_password("pass"),
        role="owner",
    )
    db_session.add(user)
    await db_session.flush()

    doc = Document(
        law_firm_id=firm.id,
        owner_user_id=user.id,
        title="Contract",
    )
    db_session.add(doc)
    await db_session.flush()

    audit = AuditService(db_session)
    service = RetentionService(db_session, audit)
    updated = await service.apply_retention_policy(doc.id, "keep_forever", firm.id, user.id)
    assert updated.retention_policy == "keep_forever"
    assert updated.deletion_date is None


@pytest.mark.asyncio
async def test_apply_retention_policy_delete_after_years(db_session):
    firm = LawFirm(name="Test Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(
        email="user@example.com",
        full_name="Test User",
        law_firm_id=firm.id,
        hashed_password=PasswordHasher.hash_password("pass"),
        role="owner",
    )
    db_session.add(user)
    await db_session.flush()

    doc = Document(
        law_firm_id=firm.id,
        owner_user_id=user.id,
        title="Contract",
    )
    db_session.add(doc)
    await db_session.flush()

    audit = AuditService(db_session)
    service = RetentionService(db_session, audit)
    updated = await service.apply_retention_policy(doc.id, "delete_after_years(7)", firm.id, user.id)
    assert updated.retention_policy == "delete_after_years(7)"
    assert updated.deletion_date is not None


@pytest.mark.asyncio
async def test_apply_invalid_policy_raises(db_session):
    firm = LawFirm(name="Test Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(
        email="user@example.com",
        full_name="Test User",
        law_firm_id=firm.id,
        hashed_password=PasswordHasher.hash_password("pass"),
        role="owner",
    )
    db_session.add(user)
    await db_session.flush()

    doc = Document(
        law_firm_id=firm.id,
        owner_user_id=user.id,
        title="Contract",
    )
    db_session.add(doc)
    await db_session.flush()

    audit = AuditService(db_session)
    service = RetentionService(db_session, audit)
    with pytest.raises(ValueError, match="Unknown retention policy"):
        await service.apply_retention_policy(doc.id, "invalid_policy", firm.id)


@pytest.mark.asyncio
async def test_schedule_deletion(db_session):
    firm = LawFirm(name="Test Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(
        email="user@example.com",
        full_name="Test User",
        law_firm_id=firm.id,
        hashed_password=PasswordHasher.hash_password("pass"),
        role="owner",
    )
    db_session.add(user)
    await db_session.flush()

    doc = Document(
        law_firm_id=firm.id,
        owner_user_id=user.id,
        title="Contract",
    )
    db_session.add(doc)
    await db_session.flush()

    audit = AuditService(db_session)
    service = RetentionService(db_session, audit)
    future = datetime.now(UTC) + timedelta(days=30)
    updated = await service.schedule_deletion(doc.id, future, firm.id, user.id)
    assert updated.deletion_date.replace(tzinfo=None) == future.replace(tzinfo=None)


@pytest.mark.asyncio
async def test_execute_deletion(db_session):
    firm = LawFirm(name="Test Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(
        email="user@example.com",
        full_name="Test User",
        law_firm_id=firm.id,
        hashed_password=PasswordHasher.hash_password("pass"),
        role="owner",
    )
    db_session.add(user)
    await db_session.flush()

    doc = Document(
        law_firm_id=firm.id,
        owner_user_id=user.id,
        title="Contract",
    )
    db_session.add(doc)
    await db_session.flush()

    version = DocumentVersion(
        document_id=doc.id,
        version_number=1,
        storage_key="s3://bucket/key",
        sha256_hash="abc123",
        mime_type="application/pdf",
        size_bytes=1024,
        created_by=user.id,
    )
    db_session.add(version)
    await db_session.flush()

    audit = AuditService(db_session)
    service = RetentionService(db_session, audit)
    result = await service.execute_deletion(doc.id, firm.id, user.id)
    assert result is True

    status = await service.get_document_retention_status(doc.id, firm.id)
    assert status["deleted_at"] is not None


@pytest.mark.asyncio
async def test_purge_expired(db_session):
    firm = LawFirm(name="Test Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(
        email="user@example.com",
        full_name="Test User",
        law_firm_id=firm.id,
        hashed_password=PasswordHasher.hash_password("pass"),
        role="owner",
    )
    db_session.add(user)
    await db_session.flush()

    doc = Document(
        law_firm_id=firm.id,
        owner_user_id=user.id,
        title="Old Contract",
        deletion_date=datetime.now(UTC) - timedelta(days=1),
    )
    db_session.add(doc)
    await db_session.flush()

    audit = AuditService(db_session)
    service = RetentionService(db_session, audit)
    count = await service.purge_expired()
    assert count == 1

    status = await service.get_document_retention_status(doc.id, firm.id)
    assert status["deleted_at"] is not None


@pytest.mark.asyncio
async def test_purge_expired_no_documents(db_session):
    audit = AuditService(db_session)
    service = RetentionService(db_session, audit)
    count = await service.purge_expired()
    assert count == 0


@pytest.mark.asyncio
async def test_get_document_retention_status_not_found(db_session):
    audit = AuditService(db_session)
    service = RetentionService(db_session, audit)
    status = await service.get_document_retention_status(uuid.uuid4(), uuid.uuid4())
    assert status is None
