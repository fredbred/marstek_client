"""Tests for BatteryManager."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.battery_manager import BatteryManager
from app.core.marstek_client import MarstekUDPClient
from app.models import Battery
from app.models.marstek_api import BatteryStatus, ESStatus, ModeInfo


@pytest.fixture
def mock_client() -> MagicMock:
    """Create mock MarstekUDPClient."""
    client = MagicMock(spec=MarstekUDPClient)
    client.broadcast_discover = AsyncMock()
    client.get_battery_status = AsyncMock()
    client.get_es_status = AsyncMock()
    client.get_current_mode = AsyncMock()
    client.set_mode_auto = AsyncMock()
    client.set_mode_manual = AsyncMock()
    return client


@pytest.fixture
def battery_manager(mock_client: MagicMock) -> BatteryManager:
    """Create BatteryManager with mock client."""
    return BatteryManager(client=mock_client)


@pytest.fixture
def mock_db() -> MagicMock:
    """Create mock database session."""
    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.flush = AsyncMock()
    return db


@pytest.fixture
def sample_batteries() -> list[Battery]:
    """Create sample battery instances."""
    return [
        Battery(
            id=1,
            name="Batt1",
            ip_address="192.168.1.100",
            udp_port=30001,
            ble_mac="123456789012",
            wifi_mac="012345678901",
            is_active=True,
        ),
        Battery(
            id=2,
            name="Batt2",
            ip_address="192.168.1.101",
            udp_port=30002,
            ble_mac="234567890123",
            wifi_mac="123456789012",
            is_active=True,
        ),
    ]


@pytest.mark.asyncio
async def test_discover_and_register_new_batteries(
    battery_manager: BatteryManager, mock_db: MagicMock, mock_client: MagicMock
) -> None:
    """Test discovering and registering new batteries."""
    from app.models.marstek_api import DeviceInfo

    # Mock discovery
    devices = [
        DeviceInfo(
            device="VenusC",
            ver=111,
            ble_mac="123456789012",
            wifi_mac="012345678901",
            wifi_name="MY_HOME",
            ip="192.168.1.100",
        )
    ]
    mock_client.broadcast_discover.return_value = devices

    # Mock database query (no existing battery)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = result_mock

    batteries = await battery_manager.discover_and_register(mock_db)

    assert len(batteries) == 1
    assert batteries[0].ip_address == "192.168.1.100"
    assert batteries[0].ble_mac == "123456789012"
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_discover_and_register_existing_battery(
    battery_manager: BatteryManager, mock_db: MagicMock, mock_client: MagicMock
) -> None:
    """Test discovering and updating existing battery."""
    from app.models.marstek_api import DeviceInfo

    # Mock discovery
    devices = [
        DeviceInfo(
            device="VenusC",
            ver=111,
            ble_mac="123456789012",
            wifi_mac="012345678901",
            wifi_name="MY_HOME",
            ip="192.168.1.101",  # IP changed
        )
    ]
    mock_client.broadcast_discover.return_value = devices

    # Mock existing battery
    existing_battery = Battery(
        id=1,
        name="Batt1",
        ip_address="192.168.1.100",
        udp_port=30001,
        ble_mac="123456789012",
        wifi_mac="012345678901",
        is_active=True,
    )

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = existing_battery
    mock_db.execute.return_value = result_mock

    batteries = await battery_manager.discover_and_register(mock_db)

    assert len(batteries) == 1
    assert batteries[0].ip_address == "192.168.1.101"  # Updated
    mock_db.add.assert_not_called()  # Should not add, only update
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_all_status_success(
    battery_manager: BatteryManager,
    mock_db: MagicMock,
    sample_batteries: list[Battery],
    mock_client: MagicMock,
) -> None:
    """Test getting status of all batteries successfully."""
    # Mock database query
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = sample_batteries
    mock_db.execute.return_value = result_mock

    # Mock client responses
    bat_status = BatteryStatus(
        id=0, soc=98, charg_flag=True, dischrg_flag=True, bat_temp=25.0
    )
    es_status = ESStatus(
        id=0, bat_soc=98, bat_power=100.0, pv_power=580.0, ongrid_power=50.0
    )
    mode_info = ModeInfo(id=0, mode="Auto", bat_soc=98)

    mock_client.get_battery_status.return_value = bat_status
    mock_client.get_es_status.return_value = es_status
    mock_client.get_current_mode.return_value = mode_info

    status_dict = await battery_manager.get_all_status(mock_db)

    assert len(status_dict) == 2
    assert 1 in status_dict
    assert 2 in status_dict
    assert "bat_status" in status_dict[1]
    assert "es_status" in status_dict[1]
    assert "mode_info" in status_dict[1]


@pytest.mark.asyncio
async def test_get_all_status_partial_failure(
    battery_manager: BatteryManager,
    mock_db: MagicMock,
    sample_batteries: list[Battery],
    mock_client: MagicMock,
) -> None:
    """Test getting status with partial failures."""
    # Mock database query
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = sample_batteries
    mock_db.execute.return_value = result_mock

    # First battery succeeds, second fails
    bat_status = BatteryStatus(id=0, soc=98, charg_flag=True, dischrg_flag=True)
    es_status = ESStatus(id=0, bat_soc=98)
    mode_info = ModeInfo(id=0, mode="Auto")

    mock_client.get_battery_status.side_effect = [
        bat_status,
        Exception("Network error"),
    ]
    mock_client.get_es_status.side_effect = [es_status, Exception("Network error")]
    mock_client.get_current_mode.side_effect = [mode_info, Exception("Network error")]

    status_dict = await battery_manager.get_all_status(mock_db)

    assert len(status_dict) == 2
    assert "error" in status_dict[2]  # Second battery has error


@pytest.mark.asyncio
async def test_set_mode_all_auto(
    battery_manager: BatteryManager,
    mock_db: MagicMock,
    sample_batteries: list[Battery],
    mock_client: MagicMock,
) -> None:
    """Test setting auto mode on all batteries."""
    # Mock database query
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = sample_batteries
    mock_db.execute.return_value = result_mock

    # Mock successful mode changes
    mock_client.set_mode_auto.return_value = True

    mode_config = {"mode": "auto"}
    results = await battery_manager.set_mode_all(mock_db, mode_config)

    assert len(results) == 2
    assert results[1] is True
    assert results[2] is True
    assert mock_client.set_mode_auto.call_count == 2


@pytest.mark.asyncio
async def test_set_mode_all_manual(
    battery_manager: BatteryManager,
    mock_db: MagicMock,
    sample_batteries: list[Battery],
    mock_client: MagicMock,
) -> None:
    """Test setting manual mode on all batteries."""
    from app.models.marstek_api import ManualConfig

    # Mock database query
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = sample_batteries
    mock_db.execute.return_value = result_mock

    # Mock successful mode changes
    mock_client.set_mode_manual.return_value = True

    manual_config = ManualConfig(
        time_num=0,
        start_time="22:00",
        end_time="06:00",
        week_set=127,
        power=0,
        enable=1,
    )

    mode_config = {"mode": "manual", "config": manual_config.model_dump()}
    results = await battery_manager.set_mode_all(mock_db, mode_config)

    assert len(results) == 2
    assert results[1] is True
    assert results[2] is True
    assert mock_client.set_mode_manual.call_count == 2


@pytest.mark.asyncio
async def test_log_status_to_db(
    battery_manager: BatteryManager,
    mock_db: MagicMock,
    sample_batteries: list[Battery],
    mock_client: MagicMock,
) -> None:
    """Test logging battery status to database."""
    # Mock get_all_status
    bat_status = BatteryStatus(
        id=0, soc=98, charg_flag=True, dischrg_flag=True, bat_temp=25.0
    )
    es_status = ESStatus(
        id=0, bat_soc=98, bat_power=100.0, pv_power=580.0, ongrid_power=50.0
    )
    mode_info = ModeInfo(id=0, mode="Auto", bat_soc=98)

    mock_client.get_battery_status.return_value = bat_status
    mock_client.get_es_status.return_value = es_status
    mock_client.get_current_mode.return_value = mode_info

    # Mock database queries
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = sample_batteries
    mock_db.execute.return_value = result_mock

    await battery_manager.log_status_to_db(mock_db)

    # Verify logs were created
    assert mock_db.add.call_count == 2  # One log per battery
    mock_db.commit.assert_called_once()
