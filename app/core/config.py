from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    """Application settings"""
    APP_NAME: str
    APP_VERSION: str
    DEBUG: bool = False

    """Database settings"""
    DATABASE_URL: str

    """CORS settings"""
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://sourcio-commerce.vercel.app",
        "https://sourcio-admin.vercel.app",
        "https://souricio-backend-2.onrender.com"
    ]

    """Security & JWT settings"""
    SECRET_KEY: Optional[str] = None
    JWT_SECRET_KEY: Optional[str] = None
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    """SMTP/Email settings"""
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    SMTP_TLS: bool = True  # Use TLS for SMTP

    """Mailtrap settings"""
    MAILTRAP_API_TOKEN: Optional[str] = None
    # Use Sandbox for testing (True) or Production for sending (False)
    MAILTRAP_USE_SANDBOX: bool = True
    # Required for Sandbox mode, ignored for Production
    MAILTRAP_INBOX_ID: Optional[str] = None
    # Sender email address for Mailtrap
    MAILTRAP_FROM_EMAIL: Optional[str] = None
    # Sender name for Mailtrap (defaults to "Sourcio")
    MAILTRAP_FROM_NAME: Optional[str] = None

    """OTP settings"""
    OTP_EXPIRY_MINUTES: int = 10

    """Company information for PDF quotes"""
    COMPANY_NAME: Optional[str] = None
    COMPANY_ADDRESS: Optional[str] = None
    COMPANY_PHONE: Optional[str] = None
    COMPANY_EMAIL: Optional[str] = None
    COMPANY_LOGO_URL: Optional[str] = None
    COMPANY_TERMS_CONDITIONS: Optional[str] = None

    """Cloudinary settings"""
    CLOUDINARY_CLOUD_NAME: Optional[str] = None
    CLOUDINARY_API_KEY: Optional[str] = None
    CLOUDINARY_API_SECRET: Optional[str] = None
    CLOUDINARY_SECURE: bool = True

    """Redis settings"""
    REDIS_URL: Optional[str] = None


settings = Settings()
