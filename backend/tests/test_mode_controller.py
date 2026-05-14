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
async def test_switch_to_manual_night_keeps_auto_when_not_red(
    mode_controller: ModeController,
    mock_db: MagicMock,
    mock_battery_manager: MagicMock,
    mock_notification_service: MagicMock,
) -> None:
    """Jour non rouge demain : conserve Auto sans appel batterie."""
    from unittest.mock import patch

    with patch("app.core.tempo_service.TempoService") as mock_tempo_cls:
        mock_tempo = MagicMock()
        mock_tempo.__aenter__ = AsyncMock(return_value=mock_tempo)
        mock_tempo.__aexit__ = AsyncMock(return_value=None)
        mock_tempo.should_activate_precharge = AsyncMock(return_value=False)
        mock_tempo_cls.return_value = mock_tempo

        results = await mode_controller.switch_to_manual_night(mock_db)

    assert results == {}
    mock_battery_manager.set_mode_all.assert_not_called()
    mock_notification_service.send_notification.assert_called_once()
    call_args = mock_notification_service.send_notification.call_args
    assert "Auto conservé" in call_args[0][0]
    assert "aucune bascule Manual/UPS" in call_args[0][1]


@pytest.mark.asyncio
async def test_activate_tempo_precharge(
    mode_controller: ModeController,
    mock_db: MagicMock,
    mock_battery_manager: MagicMock,
    mock_notification_service: MagicMock,
) -> None:
    """Test activating Tempo precharge (Passive / UPS-style, negative power)."""
    mock_battery_manager.set_mode_all.return_value = {1: True, 2: True, 3: True}

    results = await mode_controller.activate_tempo_precharge(
        mock_db, target_soc=95, power_limit=-1000
    )

    assert results == {1: True, 2: True, 3: True}
    mock_battery_manager.set_mode_all.assert_called_once()

    call_args = mock_battery_manager.set_mode_all.call_args
    mode_config = call_args[0][1]
    assert mode_config["mode"] == "passive"
    assert mode_config["power"] == -1000
    assert mode_config["cd_time"] == 8 * 3600

    mock_notification_service.send_notification.assert_called_once()


@pytest.mark.asyncio
async def test_switch_to_manual_night_red_day_uses_passive(
    mode_controller: ModeController,
    mock_db: MagicMock,
    mock_battery_manager: MagicMock,
) -> None:
    """Jour rouge demain : charge en mode Passive (UPS), pas Manual."""
    from unittest.mock import AsyncMock, MagicMock, patch

    mock_battery_manager.set_mode_all.return_value = {1: True}

    mock_result = MagicMock()
    mock_row = MagicMock()
    mock_row.value = "1000"
    mock_result.scalar_one_or_none.return_value = mock_row
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("app.core.tempo_service.TempoService") as mock_tempo_cls:
        mock_tempo = MagicMock()
        mock_tempo.__aenter__ = AsyncMock(return_value=mock_tempo)
        mock_tempo.__aexit__ = AsyncMock(return_value=None)
        mock_tempo.should_activate_precharge = AsyncMock(return_value=True)
        mock_tempo_cls.return_value = mock_tempo

        results = await mode_controller.switch_to_manual_night(mock_db)

    assert results == {1: True}
    call_args = mock_battery_manager.set_mode_all.call_args
    mode_config = call_args[0][1]
    assert mode_config["mode"] == "passive"
    assert mode_config["power"] == -1000
    assert mode_config["cd_time"] == 8 * 3600


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

    assert recommended == "auto"


@pytest.mark.asyncio
async def test_get_recommended_mode_early_morning(
    mode_controller: ModeController, mock_db: MagicMock
) -> None:
    """Test getting recommended mode in early morning."""
    # 5:00 (early morning, Auto is still preserved)
    current_time = datetime(2024, 1, 1, 5, 0, 0)

    recommended = await mode_controller.get_recommended_mode(mock_db, current_time)

    assert recommended == "auto"


@pytest.mark.asyncio
async def test_get_recommended_mode_default_time(
    mode_controller: ModeController, mock_db: MagicMock
) -> None:
    """Test getting recommended mode with default time (now)."""
    recommended = await mode_controller.get_recommended_mode(mock_db)

    # Should return a valid mode
    assert recommended in ["auto", "tempo_precharge"]


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
