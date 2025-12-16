"""Tests for TempoService."""

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import redis.asyncio as aioredis

from app.core.tempo_service import TempoCalendar, TempoColor, TempoService


@pytest.fixture
def mock_redis() -> MagicMock:
    """Create mock Redis client."""
    redis_mock = MagicMock(spec=aioredis.Redis)
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.setex = AsyncMock()
    return redis_mock


@pytest.fixture
def tempo_service(mock_redis: MagicMock) -> TempoService:
    """Create TempoService with mock Redis."""
    service = TempoService(redis_client=mock_redis)
    return service


@pytest.mark.asyncio
async def test_get_tempo_color_cache_hit(
    tempo_service: TempoService, mock_redis: MagicMock
) -> None:
    """Test getting Tempo color from cache."""
    target_date = date.today()

    # Mock cache hit
    mock_redis.get.return_value = "RED"

    color = await tempo_service.get_tempo_color(target_date)

    assert color == TempoColor.RED
    mock_redis.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_tempo_color_api_success(
    tempo_service: TempoService, mock_redis: MagicMock
) -> None:
    """Test getting Tempo color from API."""
    target_date = date.today()

    # Mock cache miss
    mock_redis.get.return_value = None

    # Mock API response - Format attendu par api-couleur-tempo.fr
    api_response = [
        {"dateJour": target_date.isoformat(), "codeJour": 1, "libCouleur": "Bleu"}
    ]

    with patch.object(tempo_service, "_get_http_client") as mock_get_client:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = api_response
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        color = await tempo_service.get_tempo_color(target_date)

        assert color == TempoColor.BLUE
        mock_redis.setex.assert_called_once()  # Should cache the result

    with patch.object(tempo_service, "_get_http_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=httpx.HTTPError("API Error"))
        mock_get_client.return_value = mock_client

        color = await tempo_service.get_tempo_color(target_date)

        assert color == TempoColor.UNKNOWN


@pytest.mark.asyncio
async def test_get_tomorrow_color(
    tempo_service: TempoService, mock_redis: MagicMock
) -> None:
    """Test getting tomorrow's color."""
    tomorrow = date.today() + timedelta(days=1)

    # Mock cache hit
    mock_redis.get.return_value = "RED"

    color = await tempo_service.get_tomorrow_color()

    assert color == TempoColor.RED
    # Should check cache for tomorrow
    call_args = mock_redis.get.call_args[0][0]
    assert tomorrow.isoformat() in call_args


@pytest.mark.asyncio
async def test_should_activate_precharge_true(
    tempo_service: TempoService, mock_redis: MagicMock
) -> None:
    """Test precharge activation when tomorrow is red and today is not."""
    today = date.today()
    tomorrow = today + timedelta(days=1)

    # Mock cache: today BLUE, tomorrow RED
    def mock_get(key: str) -> str | None:
        if today.isoformat() in key:
            return "BLUE"
        elif tomorrow.isoformat() in key:
            return "RED"
        return None

    mock_redis.get.side_effect = mock_get

    should_activate = await tempo_service.should_activate_precharge()

    assert should_activate is True


@pytest.mark.asyncio
async def test_should_activate_precharge_false_today_red(
    tempo_service: TempoService, mock_redis: MagicMock
) -> None:
    """Test precharge not activated when today is already red."""
    today = date.today()
    today + timedelta(days=1)

    # Mock cache: both RED
    def mock_get(key: str) -> str | None:
        return "RED"

    mock_redis.get.side_effect = mock_get

    should_activate = await tempo_service.should_activate_precharge()

    assert should_activate is False


@pytest.mark.asyncio
async def test_get_remaining_days_success(
    tempo_service: TempoService, mock_redis: MagicMock
) -> None:
    """Test getting remaining days."""
    from datetime import timedelta

    today = date.today()
    # Mock API response - Format attendu par api-couleur-tempo.fr
    # Ajouter 22 jours bleus
    api_response = []
    for i in range(22):
        api_response.append(
            {
                "dateJour": (today + timedelta(days=i + 1)).isoformat(),
                "codeJour": 1,
                "libCouleur": "Bleu",
            }
        )
    # Ajouter 43 jours blancs
    for i in range(43):
        api_response.append(
            {
                "dateJour": (today + timedelta(days=i + 23)).isoformat(),
                "codeJour": 2,
                "libCouleur": "Blanc",
            }
        )

    with patch.object(tempo_service, "_get_http_client") as mock_get_client:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = api_response
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        remaining = await tempo_service.get_remaining_days()

        assert remaining["BLUE"] == 22
        assert remaining["WHITE"] == 43
        assert remaining["RED"] == 0

    # Mock API response - Format attendu par api-couleur-tempo.fr
    # Ajouter 22 jours bleus
    api_response = []
    for i in range(22):
        api_response.append(
            {
                "dateJour": (today + timedelta(days=i + 1)).isoformat(),
                "codeJour": 1,
                "libCouleur": "Bleu",
            }
        )
    # Ajouter 43 jours blancs
    for i in range(43):
        api_response.append(
            {
                "dateJour": (today + timedelta(days=i + 23)).isoformat(),
                "codeJour": 2,
                "libCouleur": "Blanc",
            }
        )

    with patch.object(tempo_service, "_get_http_client") as mock_get_client:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = api_response
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        remaining = await tempo_service.get_remaining_days()

        assert remaining["BLUE"] == 22
        assert remaining["WHITE"] == 43
        assert remaining["RED"] == 0


@pytest.mark.asyncio
async def test_cache_ttl_tomorrow(tempo_service: TempoService) -> None:
    """Test cache TTL calculation for tomorrow."""
    tomorrow = date.today() + timedelta(days=1)
    ttl = tempo_service._get_cache_ttl(tomorrow)

    # Should be positive
    assert ttl > 0


@pytest.mark.asyncio
async def test_parse_api_response_valid(tempo_service: TempoService) -> None:
    """Test parsing valid API response."""
    target_date = date.today()
    data = {
        "tempo_like_calendars": [{"date": target_date.isoformat(), "value": "WHITE"}]
    }

    color = tempo_service._parse_api_response(data, target_date)

    assert color == TempoColor.WHITE


@pytest.mark.asyncio
async def test_parse_api_response_empty(tempo_service: TempoService) -> None:
    """Test parsing empty API response."""
    target_date = date.today()
    data = {"tempo_like_calendars": []}

    color = tempo_service._parse_api_response(data, target_date)

    assert color == TempoColor.UNKNOWN


@pytest.mark.asyncio
async def test_tempo_calendar_to_dict() -> None:
    """Test TempoCalendar to_dict."""
    calendar = TempoCalendar(date=date(2024, 1, 15), color=TempoColor.RED)

    result = calendar.to_dict()

    assert result["date"] == "2024-01-15"
    assert result["color"] == "RED"


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_tempo_calendar_from_dict() -> None:
    """Test TempoCalendar from_dict."""
    data = {"date": "2024-01-15", "color": "BLUE"}

    calendar = TempoCalendar.from_dict(data)

    """Test TempoCalendar from_dict."""
    data = {"date": "2024-01-15", "color": "BLUE"}
