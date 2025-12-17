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
    """Test switching to manual night mode successfully."""
    # Mock successful mode change
    mock_battery_manager.set_mode_all.return_value = {1: True, 2: True, 3: True}

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
    """Test activating Tempo precharge."""
    # Mock successful mode change
    mock_battery_manager.set_mode_all.return_value = {1: True, 2: True, 3: True}

    results = await mode_controller.activate_tempo_precharge(mock_db, target_soc=95)

    assert results == {1: True, 2: True, 3: True}
    mock_battery_manager.set_mode_all.assert_called_once()
    # switch_to_auto_mode sends a notification, then activate_tempo_precharge sends another
    assert mock_notification_service.send_notification.call_count == 2


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
