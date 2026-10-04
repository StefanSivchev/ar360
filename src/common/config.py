from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed configuration for AR-360.

    Validated when first loaded. Environment variables take precedence over .env,
    so the same code runs unchanged on a laptop, in CI and in Airflow.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # AWS settings
    aws_region: str = "eu-central-1"
    s3_bucket: str = "ar360-lake-stefansivchev"

    # Snowflake settings
    snowflake_account: str | None = None
    snowflake_user: str | None = None
    snowflake_role: str = "AR360_LOADER"

    # Root folder the generator writes into.
    data_dir: Path = Path("data")
    # Generator output that extraction treats as the source system.
    source_dir: Path = Path("data/run1")


# Cached so the whole process shares one Settings object and .env is read once.
@lru_cache
def get_settings() -> Settings:
    return Settings()
