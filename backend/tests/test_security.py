import pytest
from cryptography.fernet import Fernet
from breaking_law.identity.security import PasswordHasher, Encryption


def test_password_hashing():
    hashed = PasswordHasher.hash_password("secret")
    assert PasswordHasher.verify_password("secret", hashed) is True
    assert PasswordHasher.verify_password("wrong", hashed) is False


def test_encryption_roundtrip():
    key = Fernet.generate_key().decode()
    enc = Encryption(key=key)
    encrypted = enc.encrypt_data("sensitive data")
    assert encrypted != b"sensitive data"
    decrypted = enc.decrypt_data(encrypted)
    assert decrypted == "sensitive data"


def test_encryption_generates_key_when_none(monkeypatch):
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
    enc = Encryption()
    assert enc.cipher is not None
    encrypted = enc.encrypt_data("data")
    decrypted = enc.decrypt_data(encrypted)
    assert decrypted == "data"
