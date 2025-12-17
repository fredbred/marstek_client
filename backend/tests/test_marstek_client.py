"""Tests for Marstek UDP client."""

import json
import socket
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.marstek_client import MarstekAPIError, MarstekUDPClient
from app.models.marstek_api import (
    BatteryStatus,
    DeviceInfo,
    ESStatus,
    ManualConfig,
    ModeInfo,
)


@pytest.fixture
def client() -> MarstekUDPClient:
    """Create MarstekUDPClient instance for testing."""
    return MarstekUDPClient(timeout=1.0, max_retries=3, retry_backoff=0.1)


@pytest.fixture
def mock_socket() -> MagicMock:
    """Create mock UDP socket."""
    return MagicMock(spec=socket.socket)


@pytest.mark.asyncio
async def test_client_initialization(client: MarstekUDPClient) -> None:
    """Test client initialization."""
    assert client.timeout == 1.0
    assert client.max_retries == 3
    assert client.retry_backoff == 0.1
    assert client.instance_id == 0


@pytest.mark.asyncio
async def test_send_command_success(
    client: MarstekUDPClient, mock_socket: MagicMock
) -> None:
    """Test successful command sending."""
    response_data = json.dumps(
        {
            "id": 1,
            "src": "VenusC-test",
            "result": {"id": 0, "soc": 98},
        }
    ).encode("utf-8")

    mock_socket.recvfrom.return_value = (response_data, ("192.168.1.100", 30000))

    with patch.object(client, "_create_socket", return_value=mock_socket):
        response = await client.send_command(
            "192.168.1.100", 30000, {"method": "Bat.GetStatus", "params": {"id": 0}}
        )

        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["soc"] == 98
        mock_socket.sendto.assert_called_once()


@pytest.mark.asyncio
async def test_send_command_timeout_retry(
    client: MarstekUDPClient, mock_socket: MagicMock
) -> None:
    """Test command retry on timeout."""
    mock_socket.recvfrom.side_effect = socket.timeout("Timeout")

    with patch.object(client, "_create_socket", return_value=mock_socket):
        with pytest.raises(TimeoutError):
            await client.send_command(
                "192.168.1.100", 30000, {"method": "Bat.GetStatus", "params": {"id": 0}}
            )

        # Should have retried max_retries times
        assert mock_socket.sendto.call_count == client.max_retries


@pytest.mark.asyncio
async def test_send_command_jsonrpc_error(
    client: MarstekUDPClient, mock_socket: MagicMock
) -> None:
    """Test handling of JSON-RPC error response."""
    error_response = json.dumps(
        {
            "id": 1,
            "src": "VenusC-test",
            "error": {"code": -32601, "message": "Method not found"},
        }
    ).encode("utf-8")

    mock_socket.recvfrom.return_value = (error_response, ("192.168.1.100", 30000))

    with patch.object(client, "_create_socket", return_value=mock_socket):
        with pytest.raises(MarstekAPIError) as exc_info:
            await client.send_command(
                "192.168.1.100", 30000, {"method": "Invalid.Method", "params": {}}
            )

        assert exc_info.value.code == -32601
        assert "Method not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_broadcast_discover(
    client: MarstekUDPClient, mock_socket: MagicMock
) -> None:
    """Test device discovery via broadcast."""
    # First response
    response1 = json.dumps(
        {
            "id": 0,
            "src": "VenusC-123456789012",
            "result": {
                "device": "VenusC",
                "ver": 111,
                "ble_mac": "123456789012",
                "wifi_mac": "012123456789",
                "wifi_name": "MY_HOME",
                "ip": "192.168.1.100",
            },
        }
    ).encode("utf-8")

    # Second response
    response2 = json.dumps(
        {
            "id": 0,
            "src": "VenusE-987654321098",
            "result": {
                "device": "VenusE",
                "ver": 112,
                "ble_mac": "987654321098",
                "wifi_mac": "098765432109",
                "wifi_name": "MY_HOME",
                "ip": "192.168.1.101",
            },
        }
    ).encode("utf-8")

    mock_socket.recvfrom.side_effect = [
        (response1, ("192.168.1.100", 30000)),
        (response2, ("192.168.1.101", 30000)),
        socket.timeout(),  # End discovery
    ]

    with patch.object(client, "_create_socket", return_value=mock_socket):
        devices = await client.broadcast_discover(timeout=1.0)

        assert len(devices) == 2
        assert devices[0].device == "VenusC"
        assert devices[0].ip == "192.168.1.100"
        assert devices[1].device == "VenusE"
        assert devices[1].ip == "192.168.1.101"


@pytest.mark.asyncio
async def test_get_device_info(
    client: MarstekUDPClient, mock_socket: MagicMock
) -> None:
    """Test get_device_info method."""
    response = json.dumps(
        {
            "id": 1,
            "src": "VenusC-123456789012",
            "result": {
                "device": "VenusC",
                "ver": 111,
                "ble_mac": "123456789012",
                "wifi_mac": "012123456789",
                "wifi_name": "MY_HOME",
                "ip": "192.168.1.100",
            },
        }
    ).encode("utf-8")

    mock_socket.recvfrom.return_value = (response, ("192.168.1.100", 30000))

    with patch.object(client, "_create_socket", return_value=mock_socket):
        device_info = await client.get_device_info("192.168.1.100", 30000)

        assert isinstance(device_info, DeviceInfo)
        assert device_info.device == "VenusC"
        assert device_info.ver == 111
        assert device_info.ip == "192.168.1.100"


@pytest.mark.asyncio
async def test_get_battery_status(
    client: MarstekUDPClient, mock_socket: MagicMock
) -> None:
    """Test get_battery_status method."""
    response = json.dumps(
        {
            "id": 1,
            "src": "VenusC-test",
            "result": {
                "id": 0,
                "soc": 98,
                "charg_flag": True,
                "dischrg_flag": True,
                "bat_temp": 25.0,
                "bat_capacity": 2508.0,
                "rated_capacity": 2560.0,
            },
        }
    ).encode("utf-8")

    mock_socket.recvfrom.return_value = (response, ("192.168.1.100", 30000))

    with patch.object(client, "_create_socket", return_value=mock_socket):
        status = await client.get_battery_status("192.168.1.100", 30000)

        assert isinstance(status, BatteryStatus)
        assert status.soc == 98
        assert status.charg_flag is True
        assert status.bat_temp == 25.0


@pytest.mark.asyncio
async def test_get_battery_status_string_soc(
    client: MarstekUDPClient, mock_socket: MagicMock
) -> None:
    """Test get_battery_status with string SOC (API can return string)."""
    response = json.dumps(
        {
            "id": 1,
            "src": "VenusC-test",
            "result": {
                "id": 0,
                "soc": "98",  # String format
                "charg_flag": True,
                "dischrg_flag": True,
            },
        }
    ).encode("utf-8")

    mock_socket.recvfrom.return_value = (response, ("192.168.1.100", 30000))

    with patch.object(client, "_create_socket", return_value=mock_socket):
        status = await client.get_battery_status("192.168.1.100", 30000)

        assert status.soc == 98  # Should be converted to int


@pytest.mark.asyncio
async def test_get_es_status(client: MarstekUDPClient, mock_socket: MagicMock) -> None:
    """Test get_es_status method."""
    response = json.dumps(
        {
            "id": 1,
            "src": "VenusC-test",
            "result": {
                "id": 0,
                "bat_soc": 98,
                "bat_cap": 2560,
                "pv_power": 580.0,
                "ongrid_power": 100.0,
                "offgrid_power": 0.0,
                "bat_power": 0.0,
                "total_pv_energy": 1000.0,
                "total_grid_output_energy": 844.0,
                "total_grid_input_energy": 1607.0,
                "total_load_energy": 0.0,
            },
        }
    ).encode("utf-8")

    mock_socket.recvfrom.return_value = (response, ("192.168.1.100", 30000))

    with patch.object(client, "_create_socket", return_value=mock_socket):
        status = await client.get_es_status("192.168.1.100", 30000)

        assert isinstance(status, ESStatus)
        assert status.bat_soc == 98
        assert status.pv_power == 580.0
        assert status.ongrid_power == 100.0


@pytest.mark.asyncio
async def test_get_current_mode(
    client: MarstekUDPClient, mock_socket: MagicMock
) -> None:
    """Test get_current_mode method."""
    response = json.dumps(
        {
            "id": 1,
            "src": "VenusC-test",
            "result": {
                "id": 0,
                "mode": "Auto",
                "ongrid_power": 100.0,
                "offgrid_power": 0.0,
                "bat_soc": 98,
            },
        }
    ).encode("utf-8")

    mock_socket.recvfrom.return_value = (response, ("192.168.1.100", 30000))

    with patch.object(client, "_create_socket", return_value=mock_socket):
        mode_info = await client.get_current_mode("192.168.1.100", 30000)

        assert isinstance(mode_info, ModeInfo)
        assert mode_info.mode == "Auto"
        assert mode_info.bat_soc == 98


@pytest.mark.asyncio
async def test_get_current_mode_numeric(
    client: MarstekUDPClient, mock_socket: MagicMock
) -> None:
    """Test get_current_mode with numeric mode (API can return number)."""
    response = json.dumps(
        {
            "id": 1,
            "src": "VenusC-test",
            "result": {
                "id": 0,
                "mode": 0,  # Numeric format: 0=Auto
                "ongrid_power": 100.0,
                "bat_soc": 98,
            },
        }
    ).encode("utf-8")

    mock_socket.recvfrom.return_value = (response, ("192.168.1.100", 30000))

    with patch.object(client, "_create_socket", return_value=mock_socket):
        mode_info = await client.get_current_mode("192.168.1.100", 30000)

        assert mode_info.mode == "Auto"  # Should be converted to string


@pytest.mark.asyncio
async def test_set_mode_auto(client: MarstekUDPClient, mock_socket: MagicMock) -> None:
    """Test set_mode_auto method."""
    response = json.dumps(
        {
            "id": 1,
            "src": "VenusC-test",
            "result": {
                "id": 0,
                "set_result": True,
            },
        }
    ).encode("utf-8")

    mock_socket.recvfrom.return_value = (response, ("192.168.1.100", 30000))

    with patch.object(client, "_create_socket", return_value=mock_socket):
        success = await client.set_mode_auto("192.168.1.100", 30000)

        assert success is True

        # Verify command sent
        call_args = mock_socket.sendto.call_args
        sent_data = json.loads(call_args[0][0].decode("utf-8"))
        assert sent_data["method"] == "ES.SetMode"
        assert sent_data["params"]["config"]["mode"] == "Auto"
        assert sent_data["params"]["config"]["auto_cfg"]["enable"] == 1


@pytest.mark.asyncio
async def test_set_mode_manual(
    client: MarstekUDPClient, mock_socket: MagicMock
) -> None:
    """Test set_mode_manual method."""
    response = json.dumps(
        {
            "id": 1,
            "src": "VenusC-test",
            "result": {
                "id": 0,
                "set_result": True,
            },
        }
    ).encode("utf-8")

    mock_socket.recvfrom.return_value = (response, ("192.168.1.100", 30000))

    manual_config = ManualConfig(
        time_num=1,
        start_time="08:30",
        end_time="20:30",
        week_set=127,
        power=100,
        enable=1,
    )

    with patch.object(client, "_create_socket", return_value=mock_socket):
        success = await client.set_mode_manual("192.168.1.100", 30000, manual_config)

        assert success is True

        # Verify command sent
        call_args = mock_socket.sendto.call_args
        sent_data = json.loads(call_args[0][0].decode("utf-8"))
        assert sent_data["method"] == "ES.SetMode"
        assert sent_data["params"]["config"]["mode"] == "Manual"
        assert sent_data["params"]["config"]["manual_cfg"]["time_num"] == 1
        assert sent_data["params"]["config"]["manual_cfg"]["start_time"] == "08:30"


@pytest.mark.asyncio
async def test_send_command_response_id_mismatch(
    client: MarstekUDPClient, mock_socket: MagicMock
) -> None:
    """Test handling of response ID mismatch."""
    # First response with wrong ID
    wrong_response = json.dumps(
        {
            "id": 999,  # Wrong ID
            "src": "VenusC-test",
            "result": {"id": 0, "soc": 98},
        }
    ).encode("utf-8")

    # Second response with correct ID
    correct_response = json.dumps(
        {
            "id": 1,  # Correct ID
            "src": "VenusC-test",
            "result": {"id": 0, "soc": 98},
        }
    ).encode("utf-8")

    mock_socket.recvfrom.side_effect = [
        (wrong_response, ("192.168.1.100", 30000)),
        (correct_response, ("192.168.1.100", 30000)),
    ]

    with patch.object(client, "_create_socket", return_value=mock_socket):
        response = await client.send_command(
            "192.168.1.100", 30000, {"method": "Bat.GetStatus", "params": {"id": 0}}
        )

        # Should eventually get correct response
        assert response["id"] == 1


@pytest.mark.asyncio
async def test_send_command_json_decode_error(
    client: MarstekUDPClient, mock_socket: MagicMock
) -> None:
    """Test handling of JSON decode error."""
    invalid_json = b"Invalid JSON response"

    mock_socket.recvfrom.side_effect = [
        (invalid_json, ("192.168.1.100", 30000)),
        socket.timeout(),  # Retry fails
        socket.timeout(),  # Final retry fails
    ]

    with patch.object(client, "_create_socket", return_value=mock_socket):
        with pytest.raises(TimeoutError):
            await client.send_command(
                "192.168.1.100", 30000, {"method": "Bat.GetStatus", "params": {"id": 0}}
            )

