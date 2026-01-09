"""Tests for ModeController."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.battery_manager import BatteryManager
from app.core.mode_controller import ModeController


@pytest.fixture
def mock_battery_manager() -> MagicMock:
    """Create mock BatteryManager."""
    manager = MagicMock(spec=BatteryManager)
    manager.set_mode_all = AsyncMock()
    manager.get_all_status = AsyncMock()
    return manager


@pytest.fixture
def mock_notification_service() -> MagicMock:
    """Create mock notification service."""
    service = MagicMock()
    service.send_notification = AsyncMock()
    return service


@pytest.fixture
def mode_controller(
    mock_battery_manager: MagicMock, mock_notification_service: MagicMock
) -> ModeController:
    """Create ModeController with mocks."""
    return ModeController(
        battery_manager=mock_battery_manager,
        notification_service=mock_notification_service,
    )


@pytest.fixture
def mock_db() -> MagicMock:
    """Create mock database session."""
    return MagicMock()


@pytest.mark.asyncio
async def test_switch_to_auto_mode_success(
    mode_controller: ModeController,
    mock_db: MagicMock,
    mock_battery_manager: MagicMock,
    mock_notification_service: MagicMock,
) -> None:
    """Test switching to auto mode successfully."""
    # Mock successful mode change for all batteries
    mock_battery_manager.set_mode_all.return_value = {1: True, 2: True, 3: True}

    results = await mode_controller.switch_to_auto_mode(mock_db)

    assert results == {1: True, 2: True, 3: True}
    mock_battery_manager.set_mode_all.assert_called_once()
    mock_notification_service.send_notification.assert_called_once()


@pytest.mark.asyncio
async def test_switch_to_auto_mode_partial_failure(
    mode_controller: ModeController,
    mock_db: MagicMock,
    mock_battery_manager: MagicMock,
    mock_notification_service: MagicMock,
) -> None:
    """Test switching to auto mode with partial failure."""
    # Mock partial failure
    mock_battery_manager.set_mode_all.return_value = {1: True, 2: False, 3: True}

    results = await mode_controller.switch_to_auto_mode(mock_db)

    assert results == {1: True, 2: False, 3: True}
    mock_notification_service.send_notification.assert_called_once()
    # Should send warning notification
    call_args = mock_notification_service.send_notification.call_args
    assert "Échec partiel" in call_args[0][0] or "partial" in str(call_args).lower()


@pytest.mark.asyncio
async def test_switch_to_manual_night_success(
    mode_controller: ModeController,
    mock_db: MagicMock,
    mock_battery_manager: MagicMock,
    mock_notification_service: MagicMock,
) -> None:
    """Test switching to manual night mode successfully (no red day)."""
    from unittest.mock import patch

    # Mock successful mode change
    mock_battery_manager.set_mode_all.return_value = {1: True, 2: True, 3: True}

    # Mock TempoService to return no red day tomorrow
    with patch("app.core.tempo_service.TempoService") as mock_tempo_cls:
        mock_tempo = MagicMock()
        mock_tempo.__aenter__ = AsyncMock(return_value=mock_tempo)
        mock_tempo.__aexit__ = AsyncMock(return_value=None)
        mock_tempo.should_activate_precharge = AsyncMock(return_value=False)
        mock_tempo_cls.return_value = mock_tempo

        results = await mode_controller.switch_to_manual_night(mock_db)

    assert results == {1: True, 2: True, 3: True}
    mock_battery_manager.set_mode_all.assert_called_once()

    # Verify manual config was passed
    call_args = mock_battery_manager.set_mode_all.call_args
    mode_config = call_args[0][1]
    assert mode_config["mode"] == "manual"
    assert mode_config["config"]["power"] == 0  # 0W décharge
    assert mode_config["config"]["start_time"] == "22:00"
    assert mode_config["config"]["end_time"] == "06:00"


@pytest.mark.asyncio
async def test_activate_tempo_precharge(
    mode_controller: ModeController,
    mock_db: MagicMock,
    mock_battery_manager: MagicMock,
    mock_notification_service: MagicMock,
) -> None:
    """Test activating Tempo precharge (uses set_mode_passive on client)."""
    from app.models import Battery

    # Create mock batteries
    mock_batteries = [
        Battery(
            id=1,
            name="Batt1",
            ip_address="192.168.1.100",
            udp_port=30000,
            is_active=True,
        ),
        Battery(
            id=2,
            name="Batt2",
            ip_address="192.168.1.101",
            udp_port=30000,
            is_active=True,
        ),
        Battery(
            id=3,
            name="Batt3",
            ip_address="192.168.1.102",
            udp_port=30000,
            is_active=True,
        ),
    ]

    # Mock database query to return mock batteries
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = mock_batteries
    mock_db.execute = AsyncMock(return_value=result_mock)

    # Mock set_mode_passive on the client
    mock_battery_manager.client = MagicMock()
    mock_battery_manager.client.set_mode_passive = AsyncMock(return_value=True)

    results = await mode_controller.activate_tempo_precharge(mock_db, target_soc=95)

    assert results == {1: True, 2: True, 3: True}
    # set_mode_passive should be called once per battery
    assert mock_battery_manager.client.set_mode_passive.call_count == 3
    # One notification for precharge activation
    mock_notification_service.send_notification.assert_called_once()


@pytest.mark.asyncio
async def test_get_recommended_mode_daytime(
    mode_controller: ModeController, mock_db: MagicMock
) -> None:
    """Test getting recommended mode during daytime."""
    # 12:00 (noon)
    current_time = datetime(2024, 1, 1, 12, 0, 0)

    recommended = await mode_controller.get_recommended_mode(mock_db, current_time)

    assert recommended == "auto"


@pytest.mark.asyncio
async def test_get_recommended_mode_night(
    mode_controller: ModeController, mock_db: MagicMock
) -> None:
    """Test getting recommended mode during night."""
    # 23:00 (night)
    current_time = datetime(2024, 1, 1, 23, 0, 0)

    recommended = await mode_controller.get_recommended_mode(mock_db, current_time)

    assert recommended == "manual_night"


@pytest.mark.asyncio
async def test_get_recommended_mode_early_morning(
    mode_controller: ModeController, mock_db: MagicMock
) -> None:
    """Test getting recommended mode in early morning."""
    # 5:00 (early morning, still night mode)
    current_time = datetime(2024, 1, 1, 5, 0, 0)

    recommended = await mode_controller.get_recommended_mode(mock_db, current_time)

    assert recommended == "manual_night"


@pytest.mark.asyncio
async def test_get_recommended_mode_default_time(
    mode_controller: ModeController, mock_db: MagicMock
) -> None:
    """Test getting recommended mode with default time (now)."""
    recommended = await mode_controller.get_recommended_mode(mock_db)

    # Should return a valid mode
    assert recommended in ["auto", "manual_night", "tempo_precharge"]


@pytest.mark.asyncio
async def test_mode_controller_no_notification_service(
    mock_battery_manager: MagicMock,
) -> None:
    """Test ModeController without notification service."""
    controller = ModeController(
        battery_manager=mock_battery_manager, notification_service=None
    )

    mock_db = MagicMock()
    mock_battery_manager.set_mode_all.return_value = {1: True, 2: True}

    # Should not raise error even without notification service
    results = await controller.switch_to_auto_mode(mock_db)

    assert results == {1: True, 2: True}
