"""Tests for notification system."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.core.tempo_service import TempoColor
from app.models import Battery
from app.notifications.notifier import Notifier


@pytest.fixture
def mock_apprise() -> MagicMock:
    """Create mock Apprise instance."""
    apprise_mock = MagicMock()
    apprise_mock.notify = MagicMock(return_value=True)
    apprise_mock.__bool__ = MagicMock(return_value=True)
    return apprise_mock


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create mock settings."""
    settings = MagicMock()
    settings.notification.enabled = True
    settings.notification.telegram_enabled = True
    settings.notification.telegram_bot_token = "test_token"
    settings.notification.telegram_chat_id = "test_chat_id"
    settings.notification.urls = ""
    return settings


@pytest.fixture
def sample_battery() -> Battery:
    """Create sample battery for testing."""
    return Battery(
        id=1,
        name="Batt1",
        ip_address="192.168.1.100",
        udp_port=30001,
        ble_mac="AA:BB:CC:DD:EE:FF",
        wifi_mac="11:22:33:44:55:66",
        is_active=True,
        last_seen_at=datetime.utcnow(),
    )


@patch("app.notifications.notifier.get_settings")
@patch("app.notifications.notifier.Apprise")
def test_notifier_init(
    mock_apprise_class: MagicMock,
    mock_get_settings: MagicMock,
    mock_settings: MagicMock,
) -> None:
    """Test Notifier initialization."""
    mock_get_settings.return_value = mock_settings
    mock_apprise_instance = MagicMock()
    mock_apprise_class.return_value = mock_apprise_instance

    notifier = Notifier()

    assert notifier.enabled is True
    assert notifier.apprise == mock_apprise_instance


@patch("app.notifications.notifier.settings")
@patch("app.notifications.notifier.Apprise")
def test_notifier_init_disabled(
    mock_apprise_class: MagicMock, mock_settings: MagicMock
) -> None:
    """Test Notifier initialization when disabled."""
    mock_settings.notification.enabled = False

    notifier = Notifier()

    assert notifier.enabled is False
    mock_apprise_class.assert_not_called()


@patch("app.notifications.notifier.get_settings")
@patch("app.notifications.notifier.Apprise")
@pytest.mark.asyncio
async def test_send_info(
    mock_apprise_class: MagicMock,
    mock_get_settings: MagicMock,
    mock_settings: MagicMock,
    mock_apprise: MagicMock,
) -> None:
    """Test send_info method."""
    mock_get_settings.return_value = mock_settings
    mock_apprise_class.return_value = mock_apprise

    notifier = Notifier()

    result = await notifier.send_info("Test Title", "Test Message")

    assert result is True
    mock_apprise.notify.assert_called_once()


@patch("app.notifications.notifier.get_settings")
@patch("app.notifications.notifier.Apprise")
@pytest.mark.asyncio
async def test_send_warning(
    mock_apprise_class: MagicMock,
    mock_get_settings: MagicMock,
    mock_settings: MagicMock,
    mock_apprise: MagicMock,
) -> None:
    """Test send_warning method."""
    mock_get_settings.return_value = mock_settings
    mock_apprise_class.return_value = mock_apprise

    notifier = Notifier()

    result = await notifier.send_warning("Test Warning", "Warning message")

    assert result is True
    mock_apprise.notify.assert_called_once()


@patch("app.notifications.notifier.get_settings")
@patch("app.notifications.notifier.Apprise")
@pytest.mark.asyncio
async def test_send_error(
    mock_apprise_class: MagicMock,
    mock_get_settings: MagicMock,
    mock_settings: MagicMock,
    mock_apprise: MagicMock,
) -> None:
    """Test send_error method."""
    mock_get_settings.return_value = mock_settings
    mock_apprise_class.return_value = mock_apprise

    notifier = Notifier()

    result = await notifier.send_error("Test Error", "Error message")

    assert result is True
    mock_apprise.notify.assert_called_once()


@patch("app.notifications.notifier.get_settings")
@patch("app.notifications.notifier.Apprise")
@pytest.mark.asyncio
async def test_notify_mode_changed(
    mock_apprise_class: MagicMock,
    mock_get_settings: MagicMock,
    mock_settings: MagicMock,
    mock_apprise: MagicMock,
) -> None:
    """Test notify_mode_changed method."""
    mock_get_settings.return_value = mock_settings
    mock_apprise_class.return_value = mock_apprise

    notifier = Notifier()

    result = await notifier.notify_mode_changed("Manual", "Auto", battery_count=3)

    assert result is True
    mock_apprise.notify.assert_called_once()
    call_args = mock_apprise.notify.call_args
    assert "Changement de Mode" in call_args[1]["body"]
    assert "Manual" in call_args[1]["body"]
    assert "Auto" in call_args[1]["body"]


@patch("app.notifications.notifier.get_settings")
@patch("app.notifications.notifier.Apprise")
@pytest.mark.asyncio
async def test_notify_tempo_alert_red(
    mock_apprise_class: MagicMock,
    mock_get_settings: MagicMock,
    mock_settings: MagicMock,
    mock_apprise: MagicMock,
) -> None:
    """Test notify_tempo_alert for RED color."""
    mock_get_settings.return_value = mock_settings
    mock_apprise_class.return_value = mock_apprise

    notifier = Notifier()

    result = await notifier.notify_tempo_alert(
        TempoColor.RED,
        target_soc=100,
        remaining_days={"RED": 5, "BLUE": 10, "WHITE": 200},
    )

    assert result is True
    mock_apprise.notify.assert_called_once()
    call_args = mock_apprise.notify.call_args
    assert "TEMPO ROUGE" in call_args[1]["body"]


@patch("app.notifications.notifier.get_settings")
@patch("app.notifications.notifier.Apprise")
@pytest.mark.asyncio
async def test_notify_tempo_alert_blue(
    mock_apprise_class: MagicMock,
    mock_get_settings: MagicMock,
    mock_settings: MagicMock,
    mock_apprise: MagicMock,
) -> None:
    """Test notify_tempo_alert for BLUE color."""
    mock_get_settings.return_value = mock_settings
    mock_apprise_class.return_value = mock_apprise

    notifier = Notifier()

    result = await notifier.notify_tempo_alert(
        TempoColor.BLUE, remaining_days={"RED": 5, "BLUE": 10, "WHITE": 200}
    )

    assert result is True
    mock_apprise.notify.assert_called_once()
    call_args = mock_apprise.notify.call_args
    assert "TEMPO BLEU" in call_args[1]["body"]


@patch("app.notifications.notifier.get_settings")
@patch("app.notifications.notifier.Apprise")
@pytest.mark.asyncio
async def test_notify_battery_issue(
    mock_apprise_class: MagicMock,
    mock_get_settings: MagicMock,
    mock_settings: MagicMock,
    mock_apprise: MagicMock,
    sample_battery: Battery,
) -> None:
    """Test notify_battery_issue method."""
    mock_get_settings.return_value = mock_settings
    mock_apprise_class.return_value = mock_apprise

    notifier = Notifier()

    result = await notifier.notify_battery_issue(sample_battery, "Connection timeout")

    assert result is True
    mock_apprise.notify.assert_called_once()
    call_args = mock_apprise.notify.call_args
    assert "Problème Batterie" in call_args[1]["body"]
    assert sample_battery.name in call_args[1]["body"]


@patch("app.notifications.notifier.get_settings")
@patch("app.notifications.notifier.Apprise")
@pytest.mark.asyncio
async def test_notify_battery_low_soc(
    mock_apprise_class: MagicMock,
    mock_get_settings: MagicMock,
    mock_settings: MagicMock,
    mock_apprise: MagicMock,
    sample_battery: Battery,
) -> None:
    """Test notify_battery_low_soc method."""
    mock_get_settings.return_value = mock_settings
    mock_apprise_class.return_value = mock_apprise

    notifier = Notifier()

    result = await notifier.notify_battery_low_soc(sample_battery, soc=15, threshold=20)

    assert result is True
    mock_apprise.notify.assert_called_once()
    call_args = mock_apprise.notify.call_args
    assert "Batterie Faible" in call_args[1]["body"]
    assert "15" in call_args[1]["body"]


@patch("app.notifications.notifier.get_settings")
@patch("app.notifications.notifier.Apprise")
@pytest.mark.asyncio
async def test_notify_battery_offline(
    mock_apprise_class: MagicMock,
    mock_get_settings: MagicMock,
    mock_settings: MagicMock,
    mock_apprise: MagicMock,
    sample_battery: Battery,
) -> None:
    """Test notify_battery_offline method."""
    mock_get_settings.return_value = mock_settings
    mock_apprise_class.return_value = mock_apprise

    notifier = Notifier()

    last_seen = datetime.utcnow()
    result = await notifier.notify_battery_offline(sample_battery, last_seen=last_seen)

    assert result is True
    mock_apprise.notify.assert_called_once()

    call_args = mock_apprise.notify.call_args
    assert "Batterie Hors Ligne" in call_args[1]["body"]
