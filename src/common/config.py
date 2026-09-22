# The purpose of lru_cache is to cache the settings object so that it is only created once.
# This is important because creating the settings object can be expensive,
# and we want to avoid doing it multiple times.
# By using lru_cache, we ensure that the settings object is only created once and reused on subsequent calls to get_settings().
from functools import lru_cache

# The purpose of Path is to provide a convenient way to work with file system paths.
from pathlib import Path

# The purpose of pydantic_settings is to provide a way to define and validate settings for an application.
from pydantic_settings import BaseSettings, SettingsConfigDict


class settings(BaseSettings):
    """Typed configuration for AR-360, read from environment or .env."""

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

    # Pydantic takes the string data and hands a real Path object
    data_dir: Path = Path("data")


# Settings are constructed once on a frist call and every later call returns the same object.
# Therefore there is no re-reading on every import.
@lru_cache
def get_settings() -> settings:
    return settings()


# Configuration is declared once as a typed model that validates on startup and resolves from the environment before the file,
# so the same code runs unchanged on any laptop, in CI and in Airflow.
