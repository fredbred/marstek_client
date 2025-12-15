"""Tests pour la configuration."""

from pathlib import Path

import pytest
import yaml

from marstek.core.config import (
    AppConfig,
    BatteryConfig,
    ModeConfig,
    TempoConfig,
)


def test_battery_config_valid() -> None:
    """Test la création d'une config batterie valide."""
    config = BatteryConfig(id="test", name="Test", ip="192.168.1.100", port=502)

    assert config.id == "test"
    assert config.name == "Test"
    assert config.ip == "192.168.1.100"
    assert config.port == 502


def test_battery_config_invalid_ip() -> None:
    """Test la validation d'IP invalide."""
    with pytest.raises(ValueError, match="Invalid IP address"):
        BatteryConfig(id="test", name="Test", ip="invalid")


def test_mode_config_valid() -> None:
    """Test la création d'une config mode valide."""
    config = ModeConfig(start_hour=6, end_hour=22)

    assert config.start_hour == 6
    assert config.end_hour == 22


def test_mode_config_invalid_hours() -> None:
    """Test la validation d'heures invalides."""
    with pytest.raises(ValueError, match="end_hour must be after start_hour"):
        ModeConfig(start_hour=22, end_hour=6)


def test_app_config_from_yaml(mock_config_path: Path) -> None:
    """Test le chargement de config depuis YAML."""
    config = AppConfig.from_yaml(mock_config_path)

    assert len(config.batteries) == 1
    assert config.batteries[0].id == "test_battery"
    assert config.modes["auto"].start_hour == 6
    assert config.modes["manual"].start_hour == 22
    assert config.tempo.enabled is False


def test_app_config_file_not_found() -> None:
    """Test l'erreur si le fichier de config n'existe pas."""
    with pytest.raises(FileNotFoundError):
        AppConfig.from_yaml(Path("nonexistent.yaml"))


def test_tempo_config_database_url() -> None:
    """Test la génération de l'URL de base de données."""
    from marstek.core.config import DatabaseConfig

    config = DatabaseConfig(
        host="localhost",
        port=5432,
        user="test",
        password="pass",
        database="test_db",
    )

    assert "postgresql+asyncpg://test:pass@localhost:5432/test_db" in config.url

