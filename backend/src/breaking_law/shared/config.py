import os
from typing import Optional

class Config:
    """Configuration class for the application.

    .. warning::
       DEPLOYMENT RISK: OCR dependency (tesseract) and PDF conversion dependency (LibreOffice) must be installed in the runtime environment, and the configured paths must be correct.
       Required: Tesseract binary at TESSERACT_PATH and LibreOffice binary at LIBREOFFICE_PATH.
       Impact if missing: Document parsing will fail for scanned PDFs when OCR is enabled, and export pipeline will produce DOCX-only output without PDF conversion.
    """
    
    def __init__(self):
        # Database configuration
        self.DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
        self.DATABASE_POOL_SIZE: int = int(os.getenv("DATABASE_POOL_SIZE", "10"))
        self.DATABASE_MAX_OVERFLOW: int = int(os.getenv("DATABASE_MAX_OVERFLOW", "20"))
        
        # Redis configuration
        self.REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        # API Keys
        self.LLM_API_KEY: str = os.getenv("LLM_API_KEY")
        
        # Storage configuration
        self.STORAGE_PROVIDER: str = os.getenv("STORAGE_PROVIDER", "minio")  # minio or s3
        self.MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
        self.S3_ENDPOINT: str = os.getenv("S3_ENDPOINT")
        self.S3_REGION: str = os.getenv("S3_REGION", "us-east-1")
        self.S3_BUCKET: str = os.getenv("S3_BUCKET", "legal-docs")
        self.STORAGE_ACCESS_KEY: str = os.getenv("STORAGE_ACCESS_KEY")
        self.STORAGE_SECRET_KEY: str = os.getenv("STORAGE_SECRET_KEY")
        
        # Security settings
        self.SECRET_KEY: str = os.getenv("SECRET_KEY", "insecure-key-for-development")
        self.ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
        self.ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        
        # Document processing settings
        self.OCR_ENABLED: bool = os.getenv("OCR_ENABLED", "True").lower() == "true"
        self.TESSERACT_PATH: str = os.getenv("TESSERACT_PATH", "/usr/bin/tesseract")
        
        # Export settings
        self.LIBREOFFICE_PATH: str = os.getenv("LIBREOFFICE_PATH", "/usr/bin/libreoffice")
        
        # Audit settings
        self.AUDIT_ENABLED: bool = os.getenv("AUDIT_ENABLED", "True").lower() == "true"

        # LLM configuration
        self.LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")
        self.LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.LLM_API_KEY: str = os.getenv("LLM_API_KEY")

        # Embedding configuration
        self.EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "stub")
        self.EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        self.EMBEDDING_API_KEY: str = os.getenv("EMBEDDING_API_KEY") or self.LLM_API_KEY
        self.EMBEDDING_DIMENSIONS: int = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))
        self.EMBEDDING_BATCH_SIZE: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "100"))

        # Frontend CORS origins (comma-separated)
        self.FRONTEND_ORIGINS: str = os.getenv(
            "FRONTEND_ORIGINS", "http://localhost:4200"
        )

        # Upload limits
        self.MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))

        # OAuth configuration
        self.GOOGLE_CLIENT_ID: Optional[str] = os.getenv("GOOGLE_CLIENT_ID")
        self.GOOGLE_CLIENT_SECRET: Optional[str] = os.getenv("GOOGLE_CLIENT_SECRET")
        self.MICROSOFT_CLIENT_ID: Optional[str] = os.getenv("MICROSOFT_CLIENT_ID")
        self.MICROSOFT_CLIENT_SECRET: Optional[str] = os.getenv("MICROSOFT_CLIENT_SECRET")
        self.OAUTH_REDIRECT_BASE_URL: str = os.getenv(
            "OAUTH_REDIRECT_BASE_URL", "https://api.example.com"
        )
