"""Tests for battery diagnostics API route."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request

from app.api.routes.batteries import get_battery_diagnostics
from app.api.schemas import BatteryDiagnosticsResponse
from app.models import Battery


@pytest.mark.asyncio
async def test_get_battery_diagnostics_route_returns_snapshot() -> None:
    """Test diagnostics endpoint function with mocked database and manager."""
    battery = Battery(
        id=1,
        name="Batt1",
        ip_address="192.168.1.100",
        udp_port=49154,
        ble_mac="123456789012",
        wifi_mac="012345678901",
        is_active=True,
    )

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = battery
    db = MagicMock()
    db.execute = AsyncMock(return_value=result_mock)

    manager = MagicMock()
    manager.get_battery_diagnostics = AsyncMock(
        return_value={
            "battery_id": 1,
            "battery_name": "Batt1",
            "timestamp": datetime.utcnow(),
            "ip_address": "192.168.1.100",
            "udp_port": 49154,
            "soc": 72,
            "charg_flag": True,
            "dischrg_flag": False,
            "mode": "Auto",
            "bat_power": 0.0,
            "pv_power": 120.0,
            "pv_voltage": 36.5,
            "pv_current": 3.6,
            "pv_state": 2,
            "ongrid_power": 0.0,
            "offgrid_power": None,
            "ct_state": 1,
            "a_power": 0.0,
            "b_power": 0.0,
            "c_power": 0.0,
            "total_power": 0.0,
            "input_energy": None,
            "output_energy": None,
            "modbus": {
                "ac_voltage": 253.1,
                "ac_frequency": 50.0,
                "inverter_state": 3,
                "battery_discharge_current_limit": 12,
                "max_discharge_power": 800,
            },
            "errors": {},
        }
    )

    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/batteries/1/diagnostics",
            "headers": [],
            "client": ("testclient", 50000),
        }
    )
    response = await get_battery_diagnostics(
        request=request, battery_id=1, db=db, manager=manager
    )

    assert isinstance(response, BatteryDiagnosticsResponse)
    assert response.battery_id == 1
    assert response.udp_port == 49154
    assert response.modbus is not None
    assert response.modbus.ac_voltage == 253.1
    manager.get_battery_diagnostics.assert_awaited_once_with(battery)
