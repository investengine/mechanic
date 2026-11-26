"""Settings from the environment, prefixed MECHANIC_. Secrets are SecretStr."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Real environment variables only, no env_file: locally, export them or use
    # `uv run --env-file .env`
    model_config = SettingsConfigDict(env_prefix="MECHANIC_", frozen=True, extra="ignore")

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
