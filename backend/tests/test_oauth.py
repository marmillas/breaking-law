"""
Tests for OAuth 2.0 + PKCE provider integration and router endpoints.

Covers REQ-SEC-005 acceptance criteria:
- PKCE code verifier/challenge generation
- Authorization URL construction
- Token exchange with mocked HTTP
- OAuth router endpoint authentication requirements
"""

import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timedelta

from breaking_law.identity.oauth import (
    GoogleOAuthProvider,
    MicrosoftOAuthProvider,
    OAuthProvider,
)
from breaking_law.identity.security import Encryption
from breaking_law.infra.models import LawFirm, User, EmailConnection


# ---------------------------------------------------------------------------
# PKCE generation tests
# ---------------------------------------------------------------------------

def test_generate_code_verifier_length():
    verifier = OAuthProvider.generate_code_verifier()
    assert 43 <= len(verifier) <= 128


def test_generate_code_challenge_determinism():
    verifier = OAuthProvider.generate_code_verifier()
    challenge1 = OAuthProvider.generate_code_challenge(verifier)
    challenge2 = OAuthProvider.generate_code_challenge(verifier)
    assert challenge1 == challenge2
    assert challenge1 != verifier


def test_code_challenge_is_base64url():
    verifier = OAuthProvider.generate_code_verifier()
    challenge = OAuthProvider.generate_code_challenge(verifier)
    # Should not contain padding or standard base64 chars
    assert "=" not in challenge
    assert "+" not in challenge
    assert "/" not in challenge


# ---------------------------------------------------------------------------
# Authorization URL tests
# ---------------------------------------------------------------------------

def test_google_authorization_url_contains_pkce():
    provider = GoogleOAuthProvider(
        client_id="google-client-id",
        client_secret="google-secret",
        redirect_uri="https://example.com/oauth/google/callback",
    )
    verifier = provider.generate_code_verifier()
    url = provider.get_authorization_url(state="test-state", code_verifier=verifier)
    assert "accounts.google.com" in url
    assert "code_challenge=" in url
    assert "code_challenge_method=S256" in url
    assert "state=test-state" in url


def test_microsoft_authorization_url_contains_pkce():
    provider = MicrosoftOAuthProvider(
        client_id="ms-client-id",
        client_secret="ms-secret",
        redirect_uri="https://example.com/oauth/microsoft/callback",
    )
    verifier = provider.generate_code_verifier()
    url = provider.get_authorization_url(state="test-state", code_verifier=verifier)
    assert "login.microsoftonline.com" in url
    assert "code_challenge=" in url
    assert "code_challenge_method=S256" in url
    assert "state=test-state" in url


# ---------------------------------------------------------------------------
# Token exchange tests (mocked HTTP)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_google_exchange_code(monkeypatch):
    provider = GoogleOAuthProvider(
        client_id="google-client-id",
        client_secret="google-secret",
        redirect_uri="https://example.com/oauth/google/callback",
    )

    async def _mock_post(*args, **kwargs):
        class _Resp:
            status_code = 200
            def json(self):
                return {
                    "access_token": "access-123",
                    "refresh_token": "refresh-123",
                    "expires_in": 3600,
                    "scope": "email",
                }
            def raise_for_status(self):
                pass
        return _Resp()

    async def _mock_get(*args, **kwargs):
        class _Resp:
            status_code = 200
            def json(self):
                return {"email": "user@gmail.com"}
        return _Resp()

    monkeypatch.setattr("httpx.AsyncClient.post", _mock_post)
    monkeypatch.setattr("httpx.AsyncClient.get", _mock_get)

    tokens = await provider.exchange_code("auth-code", provider.generate_code_verifier())
    assert tokens.access_token == "access-123"
    assert tokens.refresh_token == "refresh-123"
    assert tokens.email == "user@gmail.com"


@pytest.mark.asyncio
async def test_microsoft_exchange_code(monkeypatch):
    provider = MicrosoftOAuthProvider(
        client_id="ms-client-id",
        client_secret="ms-secret",
        redirect_uri="https://example.com/oauth/microsoft/callback",
    )

    async def _mock_post(*args, **kwargs):
        class _Resp:
            status_code = 200
            def json(self):
                return {
                    "access_token": "access-456",
                    "refresh_token": "refresh-456",
                    "expires_in": 3600,
                    "scope": "email",
                }
            def raise_for_status(self):
                pass
        return _Resp()

    async def _mock_get(*args, **kwargs):
        class _Resp:
            status_code = 200
            def json(self):
                return {"mail": "user@outlook.com"}
        return _Resp()

    monkeypatch.setattr("httpx.AsyncClient.post", _mock_post)
    monkeypatch.setattr("httpx.AsyncClient.get", _mock_get)

    tokens = await provider.exchange_code("auth-code", provider.generate_code_verifier())
    assert tokens.access_token == "access-456"
    assert tokens.refresh_token == "refresh-456"
    assert tokens.email == "user@outlook.com"


@pytest.mark.asyncio
async def test_google_refresh_access_token(monkeypatch):
    provider = GoogleOAuthProvider(
        client_id="google-client-id",
        client_secret="google-secret",
        redirect_uri="https://example.com/oauth/google/callback",
    )

    async def _mock_post(*args, **kwargs):
        class _Resp:
            status_code = 200
            def json(self):
                return {
                    "access_token": "new-access",
                    "expires_in": 3600,
                    "scope": "email",
                }
            def raise_for_status(self):
                pass
        return _Resp()

    async def _mock_get(*args, **kwargs):
        class _Resp:
            status_code = 200
            def json(self):
                return {"email": "user@gmail.com"}
        return _Resp()

    monkeypatch.setattr("httpx.AsyncClient.post", _mock_post)
    monkeypatch.setattr("httpx.AsyncClient.get", _mock_get)

    tokens = await provider.refresh_access_token("old-refresh")
    assert tokens.access_token == "new-access"
    assert tokens.refresh_token == "old-refresh"


# ---------------------------------------------------------------------------
# Router endpoint auth requirement tests
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def oauth_auth_headers(async_client, db_session):
    """Create a user and law firm, return auth headers."""
    firm = LawFirm(name="OAuth Test Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(
        email="oauthtest@example.com",
        full_name="OAuth Test",
        hashed_password="x",
        law_firm_id=firm.id,
        role="owner",
    )
    db_session.add(user)
    await db_session.commit()

    # Use a simple JWT for tests
    from breaking_law.identity.service import AuthService
    auth = AuthService(secret_key="insecure-key-for-development")
    token = auth.create_access_token(data={
        "sub": str(user.id),
        "firm_id": str(firm.id),
        "email": user.email,
        "role": user.role,
        "name": user.full_name,
    })
    return {"Authorization": f"Bearer {token}"}, firm.id, user.id


@pytest.mark.asyncio
async def test_google_authorize_requires_auth(async_client):
    response = await async_client.get("/oauth/google/authorize")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_microsoft_authorize_requires_auth(async_client):
    response = await async_client.get("/oauth/microsoft/authorize")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_connections_requires_auth(async_client):
    response = await async_client.get("/oauth/connections")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_disconnect_connection_requires_auth(async_client):
    response = await async_client.delete(f"/oauth/connections/{uuid.uuid4()}")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_connections_returns_empty(async_client, oauth_auth_headers):
    headers, _, _ = oauth_auth_headers
    response = await async_client.get("/oauth/connections", headers=headers)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_disconnect_connection_not_found(async_client, oauth_auth_headers):
    headers, _, _ = oauth_auth_headers
    response = await async_client.delete(
        f"/oauth/connections/{uuid.uuid4()}", headers=headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_google_callback_requires_auth(async_client):
    response = await async_client.get("/oauth/google/callback?code=x&state=y")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_microsoft_callback_requires_auth(async_client):
    response = await async_client.get("/oauth/microsoft/callback?code=x&state=y")
    assert response.status_code == 401
