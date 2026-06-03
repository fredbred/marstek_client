"""Read-only Modbus TCP client for Marstek diagnostics."""

import asyncio
import socket
import struct
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import structlog
from pydantic import BaseModel, Field

try:
    from pymodbus.client import ModbusTcpClient as _ModbusTcpClient
except ImportError:  # pragma: no cover - exercised through raw fallback tests
    _ModbusTcpClient = None

logger = structlog.get_logger(__name__)


class MarstekModbusStatus(BaseModel):
    """Read-only Marstek Modbus diagnostic values."""

    ac_voltage: float | None = Field(default=None, description="AC voltage [V]")
    ac_frequency: float | None = Field(default=None, description="AC frequency [Hz]")
    inverter_state: int | None = Field(default=None, description="Inverter state")
    battery_discharge_current_limit: int | None = Field(
        default=None, description="Battery discharge current limit raw register value"
    )
    max_discharge_power: int | None = Field(
        default=None, description="Maximum discharge power [W]"
    )
    errors: dict[str, str] = Field(default_factory=dict)


@dataclass(frozen=True)
class ModbusRegisterSpec:
    """Definition for one read-only Modbus register."""

    address: int
    field_name: str
    scale: float = 1.0


ClientFactory = Callable[[str, int, float], Any]


READ_ONLY_REGISTERS: tuple[ModbusRegisterSpec, ...] = (
    ModbusRegisterSpec(32200, "ac_voltage", 0.1),
    ModbusRegisterSpec(32204, "ac_frequency", 0.1),
    ModbusRegisterSpec(35100, "inverter_state"),
    ModbusRegisterSpec(35112, "battery_discharge_current_limit"),
    ModbusRegisterSpec(44003, "max_discharge_power"),
)


class RawModbusResponse:
    """Minimal Modbus response compatible with the subset used here."""

    def __init__(self, registers: list[int], error: bool = False) -> None:
        """Initialize a raw Modbus response."""
        self.registers = registers
        self._error = error

    def isError(self) -> bool:  # noqa: N802
        """Return whether the response is a Modbus error."""
        return self._error


class RawModbusTcpClient:
    """Minimal read-only Modbus TCP client used when pymodbus is absent."""

    def __init__(self, host: str, port: int, timeout: float) -> None:
        """Initialize the raw Modbus TCP client."""
        self.host = host
        self.port = port
        self.timeout = timeout
        self._socket: socket.socket | None = None
        self._transaction_id = 0

    def connect(self) -> bool:
        """Open the TCP socket."""
        self._socket = socket.create_connection(
            (self.host, self.port), timeout=self.timeout
        )
        self._socket.settimeout(self.timeout)
        return True

    def read_holding_registers(
        self, address: int, count: int, slave: int = 1
    ) -> RawModbusResponse:
        """Read holding registers with Modbus function 3."""
        if self._socket is None:
            raise ConnectionError("Modbus TCP socket is not connected")

        self._transaction_id = (self._transaction_id + 1) % 65536
        request = struct.pack(
            ">HHHBBHH",
            self._transaction_id,
            0,
            6,
            slave,
            3,
            address,
            count,
        )
        self._socket.sendall(request)

        header = self._read_exact(7)
        transaction_id, _protocol_id, length, _unit_id = struct.unpack(">HHHB", header)
        if transaction_id != self._transaction_id:
            raise ConnectionError("Modbus transaction ID mismatch")

        payload = self._read_exact(length - 1)
        function_code = payload[0]
        if function_code & 0x80:
            return RawModbusResponse([], error=True)

        byte_count = payload[1]
        register_bytes = payload[2 : 2 + byte_count]
        registers = [
            struct.unpack(">H", register_bytes[index : index + 2])[0]
            for index in range(0, len(register_bytes), 2)
        ]
        return RawModbusResponse(registers)

    def close(self) -> None:
        """Close the TCP socket."""
        if self._socket is not None:
            self._socket.close()
            self._socket = None

    def _read_exact(self, byte_count: int) -> bytes:
        """Read an exact number of bytes from the socket."""
        if self._socket is None:
            raise ConnectionError("Modbus TCP socket is not connected")

        chunks = bytearray()
        while len(chunks) < byte_count:
            chunk = self._socket.recv(byte_count - len(chunks))
            if not chunk:
                raise ConnectionError("Modbus TCP connection closed")
            chunks.extend(chunk)
        return bytes(chunks)


class MarstekModbusClient:
    """Read-only Modbus TCP diagnostics client."""

    def __init__(
        self,
        port: int = 502,
        timeout: float = 3.0,
        unit_id: int = 1,
        client_factory: ClientFactory | None = None,
    ) -> None:
        """Initialize the Modbus client."""
        self.port = port
        self.timeout = timeout
        self.unit_id = unit_id
        self._client_factory = client_factory

    async def read_diagnostics(
        self, ip: str, port: int | None = None
    ) -> MarstekModbusStatus:
        """Read known diagnostic registers from a battery."""
        modbus_port = port or self.port
        return await asyncio.to_thread(self._read_diagnostics_sync, ip, modbus_port)

    def _create_client(self, ip: str, port: int) -> Any:
        """Create a Modbus TCP client instance."""
        if self._client_factory is not None:
            return self._client_factory(ip, port, self.timeout)

        if _ModbusTcpClient is None:
            return RawModbusTcpClient(host=ip, port=port, timeout=self.timeout)

        return _ModbusTcpClient(host=ip, port=port, timeout=self.timeout)

    def _read_diagnostics_sync(self, ip: str, port: int) -> MarstekModbusStatus:
        """Synchronously read Modbus registers for execution in a worker thread."""
        client = self._create_client(ip, port)
        values: dict[str, Any] = {
            "ac_voltage": None,
            "ac_frequency": None,
            "inverter_state": None,
            "battery_discharge_current_limit": None,
            "max_discharge_power": None,
        }
        errors: dict[str, str] = {}

        try:
            connected = client.connect()
            if connected is False:
                raise ConnectionError("Modbus TCP connection failed")

            for spec in READ_ONLY_REGISTERS:
                try:
                    raw_value = self._read_register(client, spec.address)
                    scaled_value = raw_value * spec.scale
                    values[spec.field_name] = (
                        int(scaled_value) if spec.scale == 1.0 else scaled_value
                    )
                except Exception as exc:
                    errors[spec.field_name] = str(exc)
                    logger.warning(
                        "marstek_modbus_register_read_failed",
                        ip=ip,
                        port=port,
                        address=spec.address,
                        field=spec.field_name,
                        error=str(exc),
                    )

            return MarstekModbusStatus(**values, errors=errors)

        finally:
            try:
                client.close()
            except Exception as exc:
                logger.debug(
                    "marstek_modbus_close_failed", ip=ip, port=port, error=str(exc)
                )

    def _read_register(self, client: Any, address: int) -> int:
        """Read one holding register without writing to the device."""
        try:
            response = client.read_holding_registers(
                address=address, count=1, slave=self.unit_id
            )
        except TypeError:
            try:
                response = client.read_holding_registers(
                    address=address, count=1, unit=self.unit_id
                )
            except TypeError:
                response = client.read_holding_registers(address=address, count=1)

        is_error = getattr(response, "isError", None)
        if callable(is_error) and is_error():
            raise ConnectionError(f"Modbus error response for register {address}")

        registers = getattr(response, "registers", None)
        if not registers:
            raise ValueError(f"No register value returned for {address}")

        return int(registers[0])
