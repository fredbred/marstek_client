"""Tests for read-only Marstek Modbus diagnostics."""

from typing import Any

import pytest

from app.core.marstek_modbus_client import MarstekModbusClient


class FakeModbusResponse:
    """Minimal pymodbus-like response."""

    def __init__(self, value: int, error: bool = False) -> None:
        """Initialize fake response."""
        self.registers = [value]
        self._error = error

    def isError(self) -> bool:  # noqa: N802
        """Return whether the response is an error."""
        return self._error


class FakeModbusTcpClient:
    """Minimal pymodbus-like client used by tests."""

    def __init__(self, values: dict[int, int]) -> None:
        """Initialize fake client."""
        self.values = values
        self.read_addresses: list[int] = []
        self.closed = False

    def connect(self) -> bool:
        """Simulate a successful connection."""
        return True

    def read_holding_registers(
        self, address: int, count: int, slave: int = 1
    ) -> FakeModbusResponse:
        """Read one fake holding register."""
        self.read_addresses.append(address)
        return FakeModbusResponse(self.values[address])

    def close(self) -> None:
        """Close the fake connection."""
        self.closed = True


@pytest.mark.asyncio
async def test_modbus_read_only_mapping() -> None:
    """Test confirmed registers are read and scaled."""
    fake_client = FakeModbusTcpClient(
        {
            32200: 2531,
            32204: 500,
            35100: 3,
            35112: 12,
            44003: 800,
        }
    )

    def client_factory(ip: str, port: int, timeout: float) -> Any:
        assert ip == "192.168.1.100"
        assert port == 502
        assert timeout == 3.0
        return fake_client

    client = MarstekModbusClient(client_factory=client_factory)
    diagnostics = await client.read_diagnostics("192.168.1.100")

    assert diagnostics.ac_voltage == pytest.approx(253.1)
    assert diagnostics.ac_frequency == 50.0
    assert diagnostics.inverter_state == 3
    assert diagnostics.battery_discharge_current_limit == 12
    assert diagnostics.max_discharge_power == 800
    assert diagnostics.errors == {}
    assert fake_client.read_addresses == [32200, 32204, 35100, 35112, 44003]
    assert fake_client.closed is True
