"""
OAuth 2.0 provider integration with PKCE for Google and Microsoft.

This module implements the authorization code flow with PKCE extension
as required by the spec (REQ-SEC-005). Tokens are exchanged and refreshed
via the provider token endpoints, and the resulting access/refresh tokens
are returned as structured dataclasses for encrypted storage.
"""

import base64
import hashlib
import secrets
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlencode

import httpx


@dataclass
class OAuthTokens:
    """Container for token response from an OAuth provider."""

    access_token: str
    refresh_token: str
    expires_at: int
    scope: str
    email: str


class OAuthProvider:
    """Abstract base for OAuth 2.0 + PKCE providers."""

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    @staticmethod
    def generate_code_verifier() -> str:
        """Generate a random PKCE code verifier (43-128 chars)."""
        return base64.urlsafe_b64encode(
            secrets.token_bytes(64)
        ).decode("ascii").rstrip("=")[:128]

    @staticmethod
    def generate_code_challenge(verifier: str) -> str:
        """Compute the S256 code challenge for a verifier."""
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

    def get_authorization_url(self, state: str, code_verifier: str) -> str:
        raise NotImplementedError

    async def exchange_code(self, code: str, code_verifier: str) -> OAuthTokens:
        raise NotImplementedError

    async def refresh_access_token(self, refresh_token: str) -> OAuthTokens:
        raise NotImplementedError

    async def revoke_token(self, token: str) -> None:
        raise NotImplementedError


class GoogleOAuthProvider(OAuthProvider):
    """Google OAuth 2.0 + PKCE implementation for Gmail integration."""

    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    REVOKE_URL = "https://oauth2.googleapis.com/revoke"
    USERINFO_URL = "https://www.googleapis.com/oauth2/v1/userinfo"
    SCOPES = "https://www.googleapis.com/auth/gmail.readonly email"

    def get_authorization_url(self, state: str, code_verifier: str) -> str:
        """Build the Google OAuth consent screen URL with PKCE challenge."""
        challenge = self.generate_code_challenge(code_verifier)
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": self.SCOPES,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str, code_verifier: str) -> OAuthTokens:
        """Exchange authorization code for tokens."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": code_verifier,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self.TOKEN_URL, data=data)
        response.raise_for_status()
        payload = response.json()
        return await self._build_tokens(payload)

    async def refresh_access_token(self, refresh_token: str) -> OAuthTokens:
        """Refresh an expired access token."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self.TOKEN_URL, data=data)
        response.raise_for_status()
        payload = response.json()
        # Google may not return a new refresh token on refresh
        if "refresh_token" not in payload:
            payload["refresh_token"] = refresh_token
        return await self._build_tokens(payload)

    async def revoke_token(self, token: str) -> None:
        """Revoke a Google token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.REVOKE_URL,
                data={"token": token},
            )
            if response.status_code not in (200, 400):
                response.raise_for_status()

    async def _build_tokens(self, payload: dict) -> OAuthTokens:
        """Normalize token payload and fetch user email."""
        access_token = payload["access_token"]
        refresh_token = payload["refresh_token"]
        expires_in = payload.get("expires_in", 3600)
        scope = payload.get("scope", "")
        email = await self._fetch_email(access_token)
        return OAuthTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_in,
            scope=scope,
            email=email,
        )

    async def _fetch_email(self, access_token: str) -> str:
        """Fetch the user's email from Google userinfo endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.USERINFO_URL,
                params={"alt": "json"},
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if response.status_code == 200:
            return response.json().get("email", "")
        return ""


class MicrosoftOAuthProvider(OAuthProvider):
    """Microsoft OAuth 2.0 + PKCE implementation for Microsoft 365 / Outlook."""

    AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    REVOKE_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/logout"
    USERINFO_URL = "https://graph.microsoft.com/v1.0/me"
    SCOPES = "https://graph.microsoft.com/Mail.Read openid email"

    def get_authorization_url(self, state: str, code_verifier: str) -> str:
        """Build the Microsoft OAuth consent screen URL with PKCE challenge."""
        challenge = self.generate_code_challenge(code_verifier)
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": self.SCOPES,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "prompt": "consent",
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str, code_verifier: str) -> OAuthTokens:
        """Exchange authorization code for tokens."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": code_verifier,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self.TOKEN_URL, data=data)
        response.raise_for_status()
        payload = response.json()
        return await self._build_tokens(payload)

    async def refresh_access_token(self, refresh_token: str) -> OAuthTokens:
        """Refresh an expired access token."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self.TOKEN_URL, data=data)
        response.raise_for_status()
        payload = response.json()
        if "refresh_token" not in payload:
            payload["refresh_token"] = refresh_token
        return await self._build_tokens(payload)

    async def revoke_token(self, token: str) -> None:
        """Revoke a Microsoft token (best-effort logout)."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.REVOKE_URL,
                params={"post_logout_redirect_uri": self.redirect_uri},
            )
            if response.status_code not in (200, 302):
                response.raise_for_status()

    async def _build_tokens(self, payload: dict) -> OAuthTokens:
        """Normalize token payload and fetch user email."""
        access_token = payload["access_token"]
        refresh_token = payload["refresh_token"]
        expires_in = payload.get("expires_in", 3600)
        scope = payload.get("scope", "")
        email = await self._fetch_email(access_token)
        return OAuthTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_in,
            scope=scope,
            email=email,
        )

    async def _fetch_email(self, access_token: str) -> str:
        """Fetch the user's email from Microsoft Graph me endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if response.status_code == 200:
            data = response.json()
            return data.get("mail") or data.get("userPrincipalName", "")
        return ""
