import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./org_service.db")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "mock").lower()
EMAIL_FROM = os.getenv("EMAIL_FROM", "no-reply@localhost")
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
