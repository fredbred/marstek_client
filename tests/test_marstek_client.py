"""Tests pour le client API Marstek."""

import json
import socket
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from marstek.api.marstek_client import BatteryStatus, MarstekClient
from marstek.core.config import BatteryConfig


@pytest.mark.asyncio
async def test_client_initialization(battery_config: BatteryConfig) -> None:
    """Test l'initialisation du client."""
    client = MarstekClient(battery_config, timeout=5.0)

    assert client.config == battery_config
    assert client.timeout == 5.0
    assert client._socket is None


@pytest.mark.asyncio
async def test_client_connect_disconnect(battery_config: BatteryConfig) -> None:
    """Test la connexion/déconnexion."""
    client = MarstekClient(battery_config)

    await client.connect()
    assert client._socket is not None

    await client.disconnect()
    assert client._socket is None


@pytest.mark.asyncio
async def test_client_context_manager(battery_config: BatteryConfig) -> None:
    """Test le context manager."""
    async with MarstekClient(battery_config) as client:
        assert client._socket is not None

    # Socket devrait être fermé après le context
    assert client._socket is None


@pytest.mark.asyncio
async def test_read_status_success(battery_config: BatteryConfig) -> None:
    """Test la lecture de status avec succès."""
    client = MarstekClient(battery_config)

    # Mock des réponses JSON-RPC
    bat_response = json.dumps({
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
    }).encode("utf-8")

    es_response = json.dumps({
        "id": 2,
        "src": "VenusC-test",
        "result": {
            "id": 0,
            "bat_power": 100.0,
            "ongrid_power": 50.0,
            "offgrid_power": 0.0,
        },
    }).encode("utf-8")

    mode_response = json.dumps({
        "id": 3,
        "src": "VenusC-test",
        "result": {
            "id": 0,
            "mode": "Auto",
            "bat_soc": 98,
        },
    }).encode("utf-8")

    mock_socket = MagicMock()
    mock_socket.recvfrom.side_effect = [
        (bat_response, ("192.168.1.100", 30000)),
        (es_response, ("192.168.1.100", 30000)),
        (mode_response, ("192.168.1.100", 30000)),
    ]

    with patch("socket.socket", return_value=mock_socket):
        await client.connect()
        status = await client.read_status()

        assert status.battery_id == "test_battery"
        assert status.soc == 98
        assert status.temperature == 25.0
        assert status.mode == "Auto"
        assert mock_socket.sendto.call_count == 3  # 3 appels (Bat, ES, Mode)


@pytest.mark.asyncio
async def test_read_status_timeout_retry(battery_config: BatteryConfig) -> None:
    """Test les retries en cas de timeout."""
    client = MarstekClient(battery_config, timeout=0.1)

    mock_socket = MagicMock()
    mock_socket.recvfrom.side_effect = socket.timeout("Timeout")

    with patch("socket.socket", return_value=mock_socket):
        await client.connect()

        with pytest.raises(TimeoutError):
            await client.read_status(retries=2)

        # Vérifier que sendto a été appelé plusieurs fois (retries pour chaque méthode)
        # read_status appelle 3 méthodes (Bat, ES, Mode), donc 3 * retries
        assert mock_socket.sendto.call_count >= 2


@pytest.mark.asyncio
async def test_set_mode_success(battery_config: BatteryConfig) -> None:
    """Test le changement de mode avec succès."""
    client = MarstekClient(battery_config)

    response = json.dumps({
        "id": 1,
        "src": "VenusC-test",
        "result": {
            "id": 0,
            "set_result": True,
        },
    }).encode("utf-8")

    mock_socket = MagicMock()
    mock_socket.recvfrom.return_value = (response, ("192.168.1.100", 30000))

    with patch("socket.socket", return_value=mock_socket):
        await client.connect()

        success = await client.set_mode("Auto")

        assert success is True
        mock_socket.sendto.assert_called_once()

        # Vérifier que la requête JSON-RPC est correcte
        call_args = mock_socket.sendto.call_args
        sent_data = call_args[0][0]
        request = json.loads(sent_data.decode("utf-8"))

        assert request["method"] == "ES.SetMode"
        assert request["params"]["config"]["mode"] == "Auto"
        assert request["params"]["config"]["auto_cfg"]["enable"] == 1


@pytest.mark.asyncio
async def test_set_mode_invalid(battery_config: BatteryConfig) -> None:
    """Test le changement de mode avec mode invalide."""
    client = MarstekClient(battery_config)

    with pytest.raises(ValueError, match="Invalid mode"):
        await client.set_mode("INVALID_MODE")

    # Tester avec un mode valide mais mal écrit
    with pytest.raises(ValueError, match="Invalid mode"):
        await client.set_mode("AUTO")  # Doit être "Auto"


@pytest.mark.asyncio
async def test_set_mode_failure(battery_config: BatteryConfig) -> None:
    """Test le changement de mode avec échec."""
    client = MarstekClient(battery_config)

    mock_socket = MagicMock()
    mock_socket.recvfrom.side_effect = socket.timeout("Timeout")

    with patch("socket.socket", return_value=mock_socket):
        await client.connect()

        success = await client.set_mode("Auto", retries=2)

        assert success is False

