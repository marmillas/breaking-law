"""
Security infrastructure for legal platform.

Provides Fernet encryption for tokens/secrets, bcrypt password hashing
for user credentials, and SHA-256 token hashing for refresh tokens.
"""
import hashlib
from typing import Optional
from cryptography.fernet import Fernet
from passlib.context import CryptContext
import os


# Password hashing context using bcrypt
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Encryption:
    """Fernet symmetric encryption for tokens, API keys, and integration secrets."""

    def __init__(self, key: Optional[str] = None):
        """Initialize encryption with optional key"""
        if key is None:
            key = os.environ.get("ENCRYPTION_KEY")
        if key is None:
            # Generate a new key if none provided
            key = Fernet.generate_key()
        self.cipher = Fernet(key)

    def encrypt_data(self, data: str) -> bytes:
        """Encrypt data"""
        return self.cipher.encrypt(data.encode())

    def decrypt_data(self, encrypted_data: bytes) -> str:
        """Decrypt data"""
        return self.cipher.decrypt(encrypted_data).decode()


class PasswordHasher:
    """Bcrypt password hashing for user credentials."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a plain-text password using bcrypt."""
        return _pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plain-text password against a bcrypt hash."""
        return _pwd_context.verify(plain_password, hashed_password)


class TokenHasher:
    """SHA-256 token hashing for secure refresh token storage.

    Stores only the hash so that a database leak does not expose
    usable refresh tokens.
    """

    @staticmethod
    def hash_token(token: str) -> str:
        """Return the SHA-256 hex digest of a token."""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def verify_token(token: str, token_hash: str) -> bool:
        """Verify a raw token against a stored hash."""
        return TokenHasher.hash_token(token) == token_hash