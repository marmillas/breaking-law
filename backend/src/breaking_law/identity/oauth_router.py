"""
OAuth router for the legal platform.

Provides endpoints for connecting Google and Microsoft email accounts
using OAuth 2.0 with PKCE (REQ-SEC-005). Tokens are stored encrypted
in the database via the Encryption adapter.
"""

import uuid
from datetime import datetime, timedelta, UTC
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from breaking_law.api.deps import get_current_user, get_tenant_session, UserContext, get_config
from breaking_law.infra.models import EmailConnection
from breaking_law.identity.oauth import GoogleOAuthProvider, MicrosoftOAuthProvider, OAuthTokens
from breaking_law.identity.security import Encryption
from breaking_law.domain.schemas.identity import ConnectionOut

router = APIRouter(
    prefix="/oauth",
    tags=["oauth"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_encryption() -> Encryption:
    """Get encryption adapter from environment."""
    import os
    key = os.environ.get("ENCRYPTION_KEY")
    return Encryption(key=key)


def _create_state_jwt(verifier: str, secret: str) -> str:
    """Encode the PKCE verifier into a short-lived signed JWT state parameter."""
    payload = {
        "verifier": verifier,
        "exp": datetime.now(UTC) + timedelta(minutes=10),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def _decode_state_jwt(state: str, secret: str) -> str:
    """Decode the state JWT and return the PKCE verifier."""
    try:
        payload = jwt.decode(state, secret, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired state")
    verifier = payload.get("verifier")
    if not verifier:
        raise HTTPException(status_code=400, detail="Invalid state payload")
    return verifier


async def _store_tokens(
    db: AsyncSession,
    user_id: uuid.UUID,
    law_firm_id: uuid.UUID,
    provider: str,
    tokens: OAuthTokens,
) -> EmailConnection:
    """Encrypt and store OAuth tokens, returning the EmailConnection record."""
    encryption = _get_encryption()
    encrypted_access = encryption.encrypt_data(tokens.access_token)
    encrypted_refresh = encryption.encrypt_data(tokens.refresh_token)

    # Check for existing connection and update, or create new
    result = await db.execute(
        select(EmailConnection).where(
            EmailConnection.user_id == user_id,
            EmailConnection.provider == provider,
            EmailConnection.email_address == tokens.email,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.encrypted_access_token = encrypted_access
        existing.encrypted_refresh_token = encrypted_refresh
        existing.token_expires_at = datetime.now(UTC) + timedelta(seconds=tokens.expires_at)
        existing.scopes = tokens.scope
        existing.last_synced_at = datetime.now(UTC)
        await db.flush()
        return existing

    record = EmailConnection(
        law_firm_id=law_firm_id,
        user_id=user_id,
        provider=provider,
        email_address=tokens.email,
        encrypted_access_token=encrypted_access,
        encrypted_refresh_token=encrypted_refresh,
        token_expires_at=datetime.now(UTC) + timedelta(seconds=tokens.expires_at),
        scopes=tokens.scope,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record


# ---------------------------------------------------------------------------
# Google endpoints
# ---------------------------------------------------------------------------

@router.get("/google/authorize")
async def google_authorize(
    request: Request,
    current_user: UserContext = Depends(get_current_user),
):
    """Redirect the user to Google OAuth consent screen with PKCE."""
    cfg = get_config()
    if not cfg.GOOGLE_CLIENT_ID or not cfg.GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=501, detail="Google OAuth is not configured")

    redirect_uri = f"{cfg.OAUTH_REDIRECT_BASE_URL}/oauth/google/callback"
    provider = GoogleOAuthProvider(
        client_id=cfg.GOOGLE_CLIENT_ID,
        client_secret=cfg.GOOGLE_CLIENT_SECRET,
        redirect_uri=redirect_uri,
    )
    verifier = provider.generate_code_verifier()
    state = _create_state_jwt(verifier, cfg.SECRET_KEY)
    url = provider.get_authorization_url(state=state, code_verifier=verifier)
    return RedirectResponse(url)


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Handle Google OAuth callback, exchange code, and store encrypted tokens."""
    cfg = get_config()
    verifier = _decode_state_jwt(state, cfg.SECRET_KEY)
    redirect_uri = f"{cfg.OAUTH_REDIRECT_BASE_URL}/oauth/google/callback"
    provider = GoogleOAuthProvider(
        client_id=cfg.GOOGLE_CLIENT_ID,
        client_secret=cfg.GOOGLE_CLIENT_SECRET,
        redirect_uri=redirect_uri,
    )
    tokens = await provider.exchange_code(code, verifier)
    await _store_tokens(
        db, current_user.user_id, current_user.law_firm_id, "google", tokens
    )
    return {"message": "Google account connected", "email": tokens.email}


# ---------------------------------------------------------------------------
# Microsoft endpoints
# ---------------------------------------------------------------------------

@router.get("/microsoft/authorize")
async def microsoft_authorize(
    request: Request,
    current_user: UserContext = Depends(get_current_user),
):
    """Redirect the user to Microsoft OAuth consent screen with PKCE."""
    cfg = get_config()
    if not cfg.MICROSOFT_CLIENT_ID or not cfg.MICROSOFT_CLIENT_SECRET:
        raise HTTPException(status_code=501, detail="Microsoft OAuth is not configured")

    redirect_uri = f"{cfg.OAUTH_REDIRECT_BASE_URL}/oauth/microsoft/callback"
    provider = MicrosoftOAuthProvider(
        client_id=cfg.MICROSOFT_CLIENT_ID,
        client_secret=cfg.MICROSOFT_CLIENT_SECRET,
        redirect_uri=redirect_uri,
    )
    verifier = provider.generate_code_verifier()
    state = _create_state_jwt(verifier, cfg.SECRET_KEY)
    url = provider.get_authorization_url(state=state, code_verifier=verifier)
    return RedirectResponse(url)


@router.get("/microsoft/callback")
async def microsoft_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Handle Microsoft OAuth callback, exchange code, and store encrypted tokens."""
    cfg = get_config()
    verifier = _decode_state_jwt(state, cfg.SECRET_KEY)
    redirect_uri = f"{cfg.OAUTH_REDIRECT_BASE_URL}/oauth/microsoft/callback"
    provider = MicrosoftOAuthProvider(
        client_id=cfg.MICROSOFT_CLIENT_ID,
        client_secret=cfg.MICROSOFT_CLIENT_SECRET,
        redirect_uri=redirect_uri,
    )
    tokens = await provider.exchange_code(code, verifier)
    await _store_tokens(
        db, current_user.user_id, current_user.law_firm_id, "microsoft", tokens
    )
    return {"message": "Microsoft account connected", "email": tokens.email}


# ---------------------------------------------------------------------------
# Connection management endpoints
# ---------------------------------------------------------------------------

@router.get("/connections", response_model=List[ConnectionOut])
async def list_connections(
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """List the current user's connected email accounts."""
    result = await db.execute(
        select(EmailConnection).where(
            EmailConnection.user_id == current_user.user_id,
            EmailConnection.law_firm_id == current_user.law_firm_id,
        )
    )
    records = result.scalars().all()
    return [
        ConnectionOut(
            id=r.id,
            provider=r.provider,
            email_address=r.email_address,
            scopes=r.scopes,
            connected_at=r.connected_at.isoformat(),
            last_synced_at=r.last_synced_at.isoformat() if r.last_synced_at else None,
        )
        for r in records
    ]


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_connection(
    connection_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Disconnect an email account and revoke the provider token."""
    result = await db.execute(
        select(EmailConnection).where(
            EmailConnection.id == connection_id,
            EmailConnection.user_id == current_user.user_id,
            EmailConnection.law_firm_id == current_user.law_firm_id,
        )
    )
    record: Optional[EmailConnection] = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Connection not found")

    # Attempt to revoke the refresh token with the provider
    cfg = get_config()
    encryption = _get_encryption()
    refresh_token = encryption.decrypt_data(record.encrypted_refresh_token)

    if record.provider == "google":
        provider = GoogleOAuthProvider(
            client_id=cfg.GOOGLE_CLIENT_ID or "",
            client_secret=cfg.GOOGLE_CLIENT_SECRET or "",
            redirect_uri=f"{cfg.OAUTH_REDIRECT_BASE_URL}/oauth/google/callback",
        )
    else:
        provider = MicrosoftOAuthProvider(
            client_id=cfg.MICROSOFT_CLIENT_ID or "",
            client_secret=cfg.MICROSOFT_CLIENT_SECRET or "",
            redirect_uri=f"{cfg.OAUTH_REDIRECT_BASE_URL}/oauth/microsoft/callback",
        )

    try:
        await provider.revoke_token(refresh_token)
    except Exception:
        # Best-effort revocation; proceed with local deletion regardless
        pass

    await db.delete(record)
    await db.flush()
