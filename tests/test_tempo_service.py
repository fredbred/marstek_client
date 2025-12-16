"""Tests pour le service Tempo RTE."""

from datetime import date
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from marstek.core.config import TempoConfig
from marstek.services.tempo import TempoService


@pytest.mark.asyncio
async def test_tempo_service_disabled() -> None:
    """Test le service Tempo désactivé."""
    config = TempoConfig(enabled=False, contract_number="")
    service = TempoService(config)

    status = await service.get_tempo_status()

    assert status["color"] == "UNKNOWN"


@pytest.mark.asyncio
async def test_get_tempo_status_success() -> None:
    """Test la récupération du status Tempo avec succès."""
    config = TempoConfig(enabled=True, api_url="https://test.api", contract_number="123")
    service = TempoService(config)

    mock_response = {
        "color": "RED",
        "date": "2024-01-15",
        "next_color": "BLUE",
    }

    with patch.object(service._client, "get", new_callable=AsyncMock) as mock_get:
        mock_response_obj = AsyncMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status = AsyncMock()
        mock_get.return_value = mock_response_obj

        status = await service.get_tempo_status(date(2024, 1, 15))

        assert status["color"] == "RED"
        assert status["date"] == "2024-01-15"
        assert status["next_color"] == "BLUE"


@pytest.mark.asyncio
async def test_get_tempo_status_http_error() -> None:
    """Test la gestion d'erreur HTTP."""
    config = TempoConfig(enabled=True, api_url="https://test.api", contract_number="123")
    service = TempoService(config)

    with patch.object(service._client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.HTTPError("Connection error")

        with pytest.raises(httpx.HTTPError):
            await service.get_tempo_status()


@pytest.mark.asyncio
async def test_is_red_day_true() -> None:
    """Test la détection d'un jour rouge."""
    config = TempoConfig(enabled=True, api_url="https://test.api", contract_number="123")
    service = TempoService(config)

    with patch.object(service, "get_tempo_status", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"color": "RED", "date": "2024-01-15"}

        is_red = await service.is_red_day()

        assert is_red is True


@pytest.mark.asyncio
async def test_is_red_day_false() -> None:
    """Test la détection d'un jour non-rouge."""
    config = TempoConfig(enabled=True, api_url="https://test.api", contract_number="123")
    service = TempoService(config)

    with patch.object(service, "get_tempo_status", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"color": "BLUE", "date": "2024-01-15"}

        is_red = await service.is_red_day()

        assert is_red is False


@pytest.mark.asyncio
async def test_is_red_day_error_fallback() -> None:
    """Test le fallback en cas d'erreur."""
    config = TempoConfig(enabled=True, api_url="https://test.api", contract_number="123")
    service = TempoService(config)

    with patch.object(service, "get_tempo_status", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = Exception("Error")

        is_red = await service.is_red_day()

        assert is_red is False  # Fallback à False


@pytest.mark.asyncio
async def test_get_upcoming_red_days() -> None:
    """Test la récupération des jours rouges à venir."""
    config = TempoConfig(enabled=True, api_url="https://test.api", contract_number="123")
    service = TempoService(config)

    with patch.object(service, "is_red_day", new_callable=AsyncMock) as mock_is_red:
        # Simuler 2 jours rouges sur 7
        mock_is_red.side_effect = [True, False, False, True, False, False, False]

        red_days = await service.get_upcoming_red_days(days_ahead=7)

        assert len(red_days) == 2


@pytest.mark.asyncio
async def test_close_service() -> None:
    """Test la fermeture du service."""
    config = TempoConfig(enabled=True)
    service = TempoService(config)

    with patch.object(service._client, "aclose", new_callable=AsyncMock) as mock_close:
        await service.close()

        mock_close.assert_called_once()

