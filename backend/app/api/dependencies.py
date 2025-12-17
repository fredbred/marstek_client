"""FastAPI dependencies."""

from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import BatteryManager
from app.database import get_db


@lru_cache()
@lru_cache
def get_battery_manager() -> BatteryManager:
    """Get singleton BatteryManager instance.

    Returns:
        BatteryManager instance (singleton)
    """
    return BatteryManager()


async def get_db_session() -> AsyncSession:  # type: ignore[misc]
    """Dependency for database session.

    Yields:
        Async database session
    """
    async for session in get_db():
        yield session
