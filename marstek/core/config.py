"""Configuration management using Pydantic Settings."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BatteryConfig(BaseSettings):
    """Configuration for a single battery."""

    id: str
    name: str
    ip: str
    port: int = Field(default=502, ge=1, le=65535)

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        """Validate IP address format."""
        parts = v.split(".")
        if len(parts) != 4:
            raise ValueError(f"Invalid IP address: {v}")
        for part in parts:
            if not part.isdigit() or not (0 <= int(part) <= 255):
                raise ValueError(f"Invalid IP address: {v}")
        return v


class ModeConfig(BaseSettings):
    """Configuration for operation mode."""

    start_hour: int = Field(default=6, ge=0, le=23)
    end_hour: int = Field(default=22, ge=0, le=23)

    @field_validator("end_hour")
    @classmethod
    def validate_hours(cls, v: int, info: Any) -> int:
        """Validate that end_hour is after start_hour."""
        if "start_hour" in info.data and v <= info.data["start_hour"]:
            raise ValueError("end_hour must be after start_hour")
        return v


class TempoConfig(BaseSettings):
    """Configuration for Tempo RTE API."""

    enabled: bool = True
    api_url: str = "https://www.api-rte.com/application/json"
    contract_number: str = ""
    timeout: int = Field(default=10, ge=1, le=60)


class TelegramConfig(BaseSettings):
    """Configuration for Telegram notifications."""

    enabled: bool = True
    bot_token: str = ""
    chat_id: str = ""


class DatabaseConfig(BaseSettings):
    """Configuration for PostgreSQL database."""

    host: str = "postgres"
    port: int = Field(default=5432, ge=1, le=65535)
    user: str = "marstek"
    password: str = ""
    database: str = "marstek_db"

    @property
    def url(self) -> str:
        """Get async database URL."""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class RedisConfig(BaseSettings):
    """Configuration for Redis cache."""

    host: str = "redis"
    port: int = Field(default=6379, ge=1, le=65535)
    db: int = Field(default=0, ge=0, le=15)

    @property
    def url(self) -> str:
        """Get Redis URL."""
        return f"redis://{self.host}:{self.port}/{self.db}"


class LoggingConfig(BaseSettings):
    """Configuration for logging."""

    level: str = Field(default="INFO")
    format: str = Field(default="json")  # json or text
    file: str = "logs/marstek.log"

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()


class SchedulerConfig(BaseSettings):
    """Configuration for APScheduler."""

    timezone: str = "Europe/Paris"
    max_workers: int = Field(default=4, ge=1, le=20)


class AppConfig(BaseSettings):
    """Main application configuration."""

    model_config = SettingsConfigDict(env_prefix="MARSTEK_", case_sensitive=False)

    batteries: list[BatteryConfig]
    modes: dict[str, ModeConfig]
    tempo: TempoConfig
    telegram: TelegramConfig
    database: DatabaseConfig
    redis: RedisConfig
    logging: LoggingConfig
    scheduler: SchedulerConfig

    @classmethod
    def from_yaml(cls, path: Path | str) -> "AppConfig":
        """Load configuration from YAML file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        with path.open() as f:
            data = yaml.safe_load(f)

        # Convert nested dicts to config objects
        if "batteries" in data:
            data["batteries"] = [BatteryConfig(**b) for b in data["batteries"]]

        if "modes" in data:
            data["modes"] = {k: ModeConfig(**v) for k, v in data["modes"].items()}

        if "tempo" in data:
            data["tempo"] = TempoConfig(**data["tempo"])

        if "telegram" in data:
            data["telegram"] = TelegramConfig(**data["telegram"])

        if "database" in data:
            data["database"] = DatabaseConfig(**data["database"])

        if "redis" in data:
            data["redis"] = RedisConfig(**data["redis"])

        if "logging" in data:
            data["logging"] = LoggingConfig(**data["logging"])

        if "scheduler" in data:
            data["scheduler"] = SchedulerConfig(**data["scheduler"])

        return cls(**data)

