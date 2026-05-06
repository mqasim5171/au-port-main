# core/config.py

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Tell Pydantic where to read env vars from
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = Field(..., description="SQLAlchemy URL")
    SECRET_KEY: str = Field(..., min_length=32, description="JWT secret (>=32 chars)")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(60, description="Access token TTL (minutes)")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(7, description="Refresh token TTL (days)")
    APP_ENV: str = Field("dev", description="Environment name")

    @classmethod
    def load(cls) -> "Settings":
        # Instantiate from env/.env
        return cls()

# Instantiate settings once
settings = Settings.load()

# (Optional) sanity check; remove after verifying
# print("✅ SECRET_KEY length:", len(settings.SECRET_KEY))