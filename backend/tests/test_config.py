import pytest
from breaking_law.shared.config import Config


def test_config_loads_from_env_vars(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://db")
    monkeypatch.setenv("DATABASE_POOL_SIZE", "5")
    monkeypatch.setenv("DATABASE_MAX_OVERFLOW", "15")
    monkeypatch.setenv("SECRET_KEY", "super-secret")
    monkeypatch.setenv("OCR_ENABLED", "false")
    cfg = Config()
    assert cfg.DATABASE_URL == "postgresql+asyncpg://db"
    assert cfg.DATABASE_POOL_SIZE == 5
    assert cfg.DATABASE_MAX_OVERFLOW == 15
    assert cfg.SECRET_KEY == "super-secret"
    assert cfg.OCR_ENABLED is False


def test_config_sensible_defaults(monkeypatch):
    for key in [
        "DATABASE_URL",
        "DATABASE_POOL_SIZE",
        "DATABASE_MAX_OVERFLOW",
        "LLM_API_KEY",
        "STORAGE_PROVIDER",
        "MINIO_ENDPOINT",
        "S3_ENDPOINT",
        "S3_REGION",
        "S3_BUCKET",
        "STORAGE_ACCESS_KEY",
        "STORAGE_SECRET_KEY",
        "SECRET_KEY",
        "ALGORITHM",
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "OCR_ENABLED",
        "TESSERACT_PATH",
        "LIBREOFFICE_PATH",
        "AUDIT_ENABLED",
        "REDIS_URL",
    ]:
        monkeypatch.delenv(key, raising=False)
    cfg = Config()
    assert cfg.REDIS_URL == "redis://localhost:6379/0"
    assert cfg.STORAGE_PROVIDER == "minio"
    assert cfg.S3_REGION == "us-east-1"
    assert cfg.S3_BUCKET == "legal-docs"
    assert cfg.SECRET_KEY == "insecure-key-for-development"
    assert cfg.ALGORITHM == "HS256"
    assert cfg.ACCESS_TOKEN_EXPIRE_MINUTES == 30
    assert cfg.OCR_ENABLED is True
    assert cfg.AUDIT_ENABLED is True
    assert cfg.TESSERACT_PATH == "/usr/bin/tesseract"
    assert cfg.LIBREOFFICE_PATH == "/usr/bin/libreoffice"
    assert cfg.DATABASE_POOL_SIZE == 10
    assert cfg.DATABASE_MAX_OVERFLOW == 20


def test_config_missing_vars_optional(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("S3_ENDPOINT", raising=False)
    monkeypatch.delenv("STORAGE_ACCESS_KEY", raising=False)
    monkeypatch.delenv("STORAGE_SECRET_KEY", raising=False)
    cfg = Config()
    assert cfg.DATABASE_URL is None
    assert cfg.LLM_API_KEY is None
    assert cfg.S3_ENDPOINT is None
    assert cfg.STORAGE_ACCESS_KEY is None
    assert cfg.STORAGE_SECRET_KEY is None
