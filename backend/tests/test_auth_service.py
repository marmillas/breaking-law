import pytest
from datetime import timedelta
from breaking_law.identity.service import AuthService
from breaking_law.identity.security import TokenHasher


def test_create_and_decode_token():
    auth = AuthService(secret_key="secret")
    token = auth.create_access_token(data={"sub": "user-123"})
    payload = auth.decode_token(token)
    assert payload is not None
    assert payload["sub"] == "user-123"


def test_expired_token_rejection():
    auth = AuthService(secret_key="secret", access_token_expire_minutes=-1)
    token = auth.create_access_token(data={"sub": "user-123"})
    payload = auth.decode_token(token)
    assert payload is None


def test_invalid_token_returns_none():
    auth = AuthService(secret_key="secret")
    assert auth.decode_token("not.a.token") is None


# ---------------------------------------------------------------------------
# Refresh token tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_refresh_token(db_session):
    auth = AuthService(secret_key="secret")
    from breaking_law.infra.models import User, LawFirm

    # Create a user
    firm = LawFirm(name="Test Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(email="refresh@example.com", full_name="Refresh User", law_firm_id=firm.id, hashed_password="x")
    db_session.add(user)
    await db_session.flush()

    token = await auth.create_refresh_token(user.id, user.law_firm_id, db_session)
    assert isinstance(token, str)
    assert len(token) > 20

    # Verify hash stored, not raw token
    from breaking_law.infra.models import RefreshToken
    result = await db_session.execute(
        RefreshToken.__table__.select().where(RefreshToken.user_id == user.id)
    )
    record = result.fetchone()
    assert record is not None
    assert record.token_hash == TokenHasher.hash_token(token)
    assert record.revoked_at is None


@pytest.mark.asyncio
async def test_rotate_refresh_token(db_session):
    auth = AuthService(secret_key="secret")
    from breaking_law.infra.models import User, LawFirm, RefreshToken

    firm = LawFirm(name="Test Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(email="rotate@example.com", full_name="Rotate User", law_firm_id=firm.id, hashed_password="x")
    db_session.add(user)
    await db_session.flush()

    old_token = await auth.create_refresh_token(user.id, user.law_firm_id, db_session)
    pair = await auth.rotate_refresh_token(old_token, db_session)
    assert pair is not None
    access_token, new_refresh_token = pair
    assert access_token is not None
    assert new_refresh_token is not None

    # Old token should be revoked
    old_hash = TokenHasher.hash_token(old_token)
    result = await db_session.execute(
        RefreshToken.__table__.select().where(RefreshToken.token_hash == old_hash)
    )
    old_record = result.fetchone()
    assert old_record.revoked_at is not None
    assert old_record.replaced_by_token_hash == TokenHasher.hash_token(new_refresh_token)


@pytest.mark.asyncio
async def test_expired_refresh_token_rejection(db_session):
    auth = AuthService(secret_key="secret", refresh_token_expire_days=-1)
    from breaking_law.infra.models import User, LawFirm

    firm = LawFirm(name="Test Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(email="expired@example.com", full_name="Expired User", law_firm_id=firm.id, hashed_password="x")
    db_session.add(user)
    await db_session.flush()

    token = await auth.create_refresh_token(user.id, user.law_firm_id, db_session)
    pair = await auth.rotate_refresh_token(token, db_session)
    assert pair is None


@pytest.mark.asyncio
async def test_revoked_refresh_token_rejection(db_session):
    auth = AuthService(secret_key="secret")
    from breaking_law.infra.models import User, LawFirm

    firm = LawFirm(name="Test Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(email="revoked@example.com", full_name="Revoked User", law_firm_id=firm.id, hashed_password="x")
    db_session.add(user)
    await db_session.flush()

    token = await auth.create_refresh_token(user.id, user.law_firm_id, db_session)
    await auth.revoke_refresh_token(token, db_session)

    pair = await auth.rotate_refresh_token(token, db_session)
    assert pair is None


@pytest.mark.asyncio
async def test_replay_attack_revokes_family(db_session):
    auth = AuthService(secret_key="secret")
    from breaking_law.infra.models import User, LawFirm, RefreshToken

    firm = LawFirm(name="Test Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(email="replay@example.com", full_name="Replay User", law_firm_id=firm.id, hashed_password="x")
    db_session.add(user)
    await db_session.flush()

    token1 = await auth.create_refresh_token(user.id, user.law_firm_id, db_session)
    pair = await auth.rotate_refresh_token(token1, db_session)
    assert pair is not None
    _, token2 = pair

    # Try to reuse token1 (replay attack)
    pair2 = await auth.rotate_refresh_token(token1, db_session)
    assert pair2 is None

    # token2 should also be revoked because the whole family is revoked
    pair3 = await auth.rotate_refresh_token(token2, db_session)
    assert pair3 is None

    # Verify all tokens in family are revoked
    family_result = await db_session.execute(
        RefreshToken.__table__.select().where(RefreshToken.user_id == user.id)
    )
    records = family_result.fetchall()
    assert len(records) >= 2
    for r in records:
        assert r.revoked_at is not None


@pytest.mark.asyncio
async def test_login_returns_both_tokens(async_client, db_session):
    from breaking_law.infra.models import User, LawFirm
    from breaking_law.identity.security import PasswordHasher

    firm = LawFirm(name="Login Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(
        email="login@example.com",
        full_name="Login User",
        law_firm_id=firm.id,
        hashed_password=PasswordHasher.hash_password("secret123"),
    )
    db_session.add(user)
    await db_session.flush()

    response = await async_client.post(
        "/auth/login",
        data={"username": "login@example.com", "password": "secret123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_refresh_endpoint_returns_new_pair(async_client, db_session):
    from breaking_law.infra.models import User, LawFirm
    from breaking_law.identity.security import PasswordHasher
    from breaking_law.identity.service import AuthService

    firm = LawFirm(name="Refresh Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(
        email="refresh_ep@example.com",
        full_name="Refresh EP User",
        law_firm_id=firm.id,
        hashed_password=PasswordHasher.hash_password("secret123"),
    )
    db_session.add(user)
    await db_session.flush()

    auth = AuthService(secret_key="insecure-key-for-development")
    refresh_token = await auth.create_refresh_token(user.id, user.law_firm_id, db_session)

    response = await async_client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body


@pytest.mark.asyncio
async def test_logout_revokes_token(async_client, db_session):
    from breaking_law.infra.models import User, LawFirm
    from breaking_law.identity.security import PasswordHasher
    from breaking_law.identity.service import AuthService

    firm = LawFirm(name="Logout Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(
        email="logout@example.com",
        full_name="Logout User",
        law_firm_id=firm.id,
        hashed_password=PasswordHasher.hash_password("secret123"),
    )
    db_session.add(user)
    await db_session.flush()

    auth = AuthService(secret_key="insecure-key-for-development")
    refresh_token = await auth.create_refresh_token(user.id, user.law_firm_id, db_session)

    response = await async_client.post(
        "/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 204

    # Token should no longer be valid for rotation
    pair = await auth.rotate_refresh_token(refresh_token, db_session)
    assert pair is None
