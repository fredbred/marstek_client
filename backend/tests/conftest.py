"""Pytest configuration and fixtures."""

import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.marstek_client import MarstekUDPClient
from app.database import Base
from app.models import Battery


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session with rollback.

    Yields:
        Async database session that rolls back after each test
    """
    # Use in-memory SQLite for tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        # Start a transaction
        await session.begin()

        yield session

        # Rollback after test
        await session.rollback()
        await session.close()

    await engine.dispose()


@pytest.fixture
def mock_udp_client() -> MagicMock:
    """Create a mock MarstekUDPClient.

    Returns:
        Mock MarstekUDPClient instance
    """
    mock_client = MagicMock(spec=MarstekUDPClient)
    mock_client.broadcast_discover = AsyncMock(return_value=[])
    mock_client.send_command = AsyncMock(return_value={})
    mock_client.get_device_info = AsyncMock(return_value=None)
    mock_client.get_battery_status = AsyncMock(return_value=None)
    mock_client.get_es_status = AsyncMock(return_value=None)
    mock_client.set_mode_auto = AsyncMock(return_value=True)
    mock_client.set_mode_manual = AsyncMock(return_value=True)
    mock_client.get_current_mode = AsyncMock(return_value=None)
    return mock_client


@pytest.fixture
def sample_battery() -> Battery:
    """Create a sample battery for testing.

    Returns:
        Battery instance
    """
    return Battery(
        id=1,
        name="Batt1",
        ip_address="192.168.1.100",
        udp_port=30001,
        ble_mac="AA:BB:CC:DD:EE:FF",
        wifi_mac="11:22:33:44:55:66",
        is_active=True,
        last_seen_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_batteries() -> list[Battery]:
    """Create sample batteries for testing.

    Returns:
        List of Battery instances
    """
    return [
        Battery(
            id=1,
            name="Batt1",
            ip_address="192.168.1.100",
            udp_port=30001,
            ble_mac="AA:BB:CC:DD:EE:FF",
            wifi_mac="11:22:33:44:55:66",
            is_active=True,
            last_seen_at=datetime.utcnow(),
        ),
        Battery(
            id=2,
            name="Batt2",
            ip_address="192.168.1.101",
            udp_port=30002,
            ble_mac="BB:CC:DD:EE:FF:AA",
            wifi_mac="22:33:44:55:66:77",
            is_active=True,
            last_seen_at=datetime.utcnow(),
        ),
        Battery(
            id=3,
            name="Batt3",
            ip_address="192.168.1.102",
            udp_port=30003,
            ble_mac="CC:DD:EE:FF:AA:BB",
            wifi_mac="33:44:55:66:77:88",
            is_active=True,
            last_seen_at=datetime.utcnow(),
        ),
    ]


@pytest.fixture
def mock_redis() -> MagicMock:
    """Create a mock Redis client.

    Returns:
        Mock Redis client
    """
    redis_mock = MagicMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.setex = AsyncMock()
    redis_mock.delete = AsyncMock()
    return redis_mock


@pytest.fixture
def mock_httpx_client() -> MagicMock:
    """Create a mock httpx client.

    Returns:
        Mock httpx client
    """
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json = MagicMock(return_value={})
    mock_response.raise_for_status = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.post = AsyncMock(return_value=mock_response)
    return mock_client


@pytest.fixture
def override_get_db(db_session: AsyncSession):
    """Override get_db dependency for FastAPI tests.

    Args:
        db_session: Test database session

    Yields:
        Database session generator
    """

    async def _get_db():
        yield db_session

    return _get_db
