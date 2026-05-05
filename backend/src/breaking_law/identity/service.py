"""
Authentication service for the legal platform.

Handles JWT token creation/verification, password verification,
and refresh token lifecycle with rotation and replay detection.
"""
import secrets
import uuid
from datetime import datetime, timedelta, UTC
from typing import Optional, Tuple

from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from breaking_law.infra.models import RefreshToken
from breaking_law.identity.security import TokenHasher


class AuthService:
    """Service for JWT access token and refresh token lifecycle management."""

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    def create_access_token(
        self,
        data: dict,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Create a JWT access token.

        Args:
            data: Payload to encode (must include 'sub' for user ID).
            expires_delta: Optional custom expiry duration.

        Returns:
            Encoded JWT string.
        """
        to_encode = data.copy()
        expire = datetime.now(UTC) + (
            expires_delta or timedelta(minutes=self.access_token_expire_minutes)
        )
        to_encode.update({"exp": expire, "iat": datetime.now(UTC)})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> Optional[dict]:
        """
        Decode and validate a JWT access token.

        Args:
            token: JWT string (Bearer token without prefix).

        Returns:
            Decoded payload dict, or None if invalid/expired.
        """
        try:
            payload = jwt.decode(
                token, self.secret_key, algorithms=[self.algorithm]
            )
            return payload
        except JWTError:
            return None

    async def create_refresh_token(
        self,
        user_id: uuid.UUID,
        law_firm_id: uuid.UUID,
        db_session: AsyncSession,
    ) -> str:
        """
        Generate a cryptographically secure refresh token, hash it,
        store the hash in the database, and return the raw token.

        Args:
            user_id: The user to issue the refresh token for.
            law_firm_id: The law firm the user belongs to (for RLS context).
            db_session: Async SQLAlchemy session.

        Returns:
            The raw refresh token string (must be shown to the client once).
        """
        raw_token = secrets.token_urlsafe(64)
        token_hash = TokenHasher.hash_token(raw_token)
        family_id = uuid.uuid4()
        now = datetime.now(UTC)
        expires_at = now + timedelta(days=self.refresh_token_expire_days)

        record = RefreshToken(
            user_id=user_id,
            law_firm_id=law_firm_id,
            token_hash=token_hash,
            issued_at=now,
            expires_at=expires_at,
            family_id=family_id,
        )
        db_session.add(record)
        await db_session.flush()

        return raw_token

    async def rotate_refresh_token(
        self,
        old_token: str,
        db_session: AsyncSession,
    ) -> Optional[Tuple[str, str]]:
        """
        Rotate a refresh token: verify the old one, detect replay attacks,
        revoke the old token, issue a new access token and refresh token.

        If a replay is detected (the old token was already revoked/rotated),
        the entire token family is revoked for security.

        Args:
            old_token: The raw refresh token presented by the client.
            db_session: Async SQLAlchemy session.

        Returns:
            Tuple of (new_access_token, new_refresh_token) or None if invalid.
        """
        old_hash = TokenHasher.hash_token(old_token)

        result = await db_session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == old_hash)
        )
        record: Optional[RefreshToken] = result.scalar_one_or_none()

        if record is None:
            return None

        # Check if already revoked or expired
        if record.revoked_at is not None:
            # Possible replay attack — revoke the entire family
            await self._revoke_family(record.family_id, db_session)
            return None

        expires_at = record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at < datetime.now(UTC):
            return None

        # Revoke the old token and link to the new one
        record.revoked_at = datetime.now(UTC)

        # Issue new refresh token
        new_raw_token = secrets.token_urlsafe(64)
        new_token_hash = TokenHasher.hash_token(new_raw_token)
        now = datetime.now(UTC)
        expires_at = now + timedelta(days=self.refresh_token_expire_days)

        new_record = RefreshToken(
            user_id=record.user_id,
            token_hash=new_token_hash,
            issued_at=now,
            expires_at=expires_at,
            family_id=record.family_id,
        )
        db_session.add(new_record)
        await db_session.flush()

        record.replaced_by_token_hash = new_token_hash
        await db_session.flush()

        # Issue new access token (include firm_id for RLS context)
        access_token = self.create_access_token(
            data={
                "sub": str(record.user_id),
                "firm_id": str(record.law_firm_id) if record.law_firm_id else None,
            }
        )

        return access_token, new_raw_token

    async def revoke_refresh_token(
        self,
        token: str,
        db_session: AsyncSession,
    ) -> bool:
        """
        Revoke a single refresh token.

        Args:
            token: The raw refresh token to revoke.
            db_session: Async SQLAlchemy session.

        Returns:
            True if the token was found and revoked, False otherwise.
        """
        token_hash = TokenHasher.hash_token(token)

        result = await db_session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        record: Optional[RefreshToken] = result.scalar_one_or_none()

        if record is None:
            return False

        record.revoked_at = datetime.now(UTC)
        await db_session.flush()
        return True

    async def revoke_all_refresh_tokens_for_user(
        self,
        user_id: uuid.UUID,
        db_session: AsyncSession,
    ) -> int:
        """
        Revoke all refresh tokens for a user (global logout).

        Args:
            user_id: The user whose tokens should be revoked.
            db_session: Async SQLAlchemy session.

        Returns:
            Number of tokens revoked.
        """
        result = await db_session.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
        )
        tokens = result.scalars().all()
        now = datetime.now(UTC)
        for token in tokens:
            token.revoked_at = now
        await db_session.flush()
        return len(tokens)

    async def _revoke_family(
        self,
        family_id: uuid.UUID,
        db_session: AsyncSession,
    ) -> int:
        """Revoke every token in a rotation family (used on replay detection)."""
        result = await db_session.execute(
            select(RefreshToken).where(
                RefreshToken.family_id == family_id,
                RefreshToken.revoked_at.is_(None),
            )
        )
        tokens = result.scalars().all()
        now = datetime.now(UTC)
        for token in tokens:
            token.revoked_at = now
        await db_session.flush()
        return len(tokens)
