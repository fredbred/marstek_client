"""Fixtures pytest communes."""

from pathlib import Path

import pytest
from marstek.core.config import (
    AppConfig,
    BatteryConfig,
    DatabaseConfig,
    LoggingConfig,
    ModeConfig,
    RedisConfig,
    SchedulerConfig,
    TempoConfig,
    TelegramConfig,
)


@pytest.fixture
def battery_config() -> BatteryConfig:
    """Fixture pour configuration de batterie de test."""
    return BatteryConfig(id="test_battery", name="Test Battery", ip="192.168.1.100")


@pytest.fixture
def app_config() -> AppConfig:
    """Fixture pour configuration complète de test."""
    return AppConfig(
        batteries=[
            BatteryConfig(id="battery_1", name="Test 1", ip="192.168.1.100"),
            BatteryConfig(id="battery_2", name="Test 2", ip="192.168.1.101"),
        ],
        modes={
            "auto": ModeConfig(start_hour=6, end_hour=22),
            "manual": ModeConfig(start_hour=22, end_hour=6),
        },
        tempo=TempoConfig(enabled=False, contract_number=""),
        telegram=TelegramConfig(enabled=False, bot_token="", chat_id=""),
        database=DatabaseConfig(
            host="localhost",
            user="test",
            password="test",
            database="test_db",
        ),
        redis=RedisConfig(host="localhost", port=6379),
        logging=LoggingConfig(level="DEBUG", format="text", file=""),
        scheduler=SchedulerConfig(timezone="UTC", max_workers=2),
    )


@pytest.fixture
def mock_config_path(tmp_path: Path) -> Path:
    """Crée un fichier de config temporaire."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
batteries:
  - id: test_battery
    name: Test Battery
    ip: 192.168.1.100
    port: 502
modes:
  auto:
    start_hour: 6
    end_hour: 22
  manual:
    start_hour: 22
    end_hour: 6
tempo:
  enabled: false
  api_url: https://test.api
  contract_number: ""
telegram:
  enabled: false
  bot_token: ""
  chat_id: ""
database:
  host: localhost
  port: 5432
  user: test
  password: test
  database: test_db
redis:
  host: localhost
  port: 6379
logging:
  level: DEBUG
  format: text
  file: ""
scheduler:
  timezone: UTC
  max_workers: 2
"""
    )
    return config_file

