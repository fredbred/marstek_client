"""FastAPI dependencies."""

from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import BatteryManager
from app.database import get_db


@lru_cache()
def get_battery_manager() -> BatteryManager:
    """Get singleton BatteryManager instance.

    Returns:
        BatteryManager instance (singleton)
    """
    return BatteryManager()


async def get_db_session() -> AsyncSession:
    """Dependency for database session.

    Yields:
        Async database session
    """
    async for session in get_db():
        yield session
