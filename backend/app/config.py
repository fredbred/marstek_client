"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database configuration."""

    url: str = Field(alias="DATABASE_URL")
    echo: bool = False

    model_config = SettingsConfigDict(case_sensitive=False)


class RedisSettings(BaseSettings):
    """Redis configuration."""

    url: str = Field(alias="REDIS_URL")

    model_config = SettingsConfigDict(case_sensitive=False)


class BatterySettings(BaseSettings):
    """Battery configuration."""

    battery_1_ip: str = Field(alias="BATTERY_1_IP")
    battery_1_port: int = Field(default=30001, alias="BATTERY_1_PORT")
    battery_2_ip: str = Field(alias="BATTERY_2_IP")
    battery_2_port: int = Field(default=30002, alias="BATTERY_2_PORT")
    battery_3_ip: str = Field(alias="BATTERY_3_IP")
    battery_3_port: int = Field(default=30003, alias="BATTERY_3_PORT")

    model_config = SettingsConfigDict(case_sensitive=False)

    def get_batteries(self) -> list[dict[str, Any]]:
        """Get list of battery configurations."""
        return [
            {"id": "battery_1", "ip": self.battery_1_ip, "port": self.battery_1_port},
            {"id": "battery_2", "ip": self.battery_2_ip, "port": self.battery_2_port},
            {"id": "battery_3", "ip": self.battery_3_ip, "port": self.battery_3_port},
        ]


class SchedulerSettings(BaseSettings):
    """Scheduler configuration."""

    auto_mode_start_hour: int = Field(
        default=6, alias="AUTO_MODE_START_HOUR", ge=0, le=23
    )
    auto_mode_end_hour: int = Field(default=22, alias="AUTO_MODE_END_HOUR", ge=0, le=23)
    manual_mode_start_hour: int = Field(
        default=22, alias="MANUAL_MODE_START_HOUR", ge=0, le=23
    )
    manual_mode_end_hour: int = Field(
        default=6, alias="MANUAL_MODE_END_HOUR", ge=0, le=23
    )
    timezone: str = Field(default="Europe/Paris", alias="TIMEZONE")
    max_workers: int = Field(default=4, alias="SCHEDULER_MAX_WORKERS", ge=1, le=20)

    model_config = SettingsConfigDict(case_sensitive=False)


class TempoSettings(BaseSettings):
    """Tempo RTE API configuration."""

    enabled: bool = Field(default=True, alias="TEMPO_ENABLED")
    api_url: str = Field(
        default="https://www.api-rte.com/application/json", alias="TEMPO_API_URL"
    )
    contract_number: str = Field(default="", alias="TEMPO_CONTRACT_NUMBER")
    timeout: int = Field(default=10, alias="TEMPO_TIMEOUT", ge=1, le=60)

    model_config = SettingsConfigDict(case_sensitive=False)


class NotificationSettings(BaseSettings):
    """Notification configuration."""

    enabled: bool = Field(default=True, alias="NOTIFICATIONS_ENABLED")
    urls: str = Field(default="", alias="NOTIFICATION_URLS")  # Apprise URLs
    telegram_enabled: bool = Field(default=False, alias="TELEGRAM_ENABLED")
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(default="", alias="TELEGRAM_CHAT_ID")

    model_config = SettingsConfigDict(case_sensitive=False)


class Settings(BaseSettings):
    """Main application settings."""

    app_name: str = Field(default="marstek-automation", alias="APP_NAME")
    app_env: str = Field(default="production", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    timezone: str = Field(default="Europe/Paris", alias="TIMEZONE")

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    battery: BatterySettings = Field(default_factory=BatterySettings)
    scheduler: SchedulerSettings = Field(default_factory=SchedulerSettings)
    tempo: TempoSettings = Field(default_factory=TempoSettings)
    notification: NotificationSettings = Field(default_factory=NotificationSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_nested_delimiter="__",
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
