"""FastAPI dependencies."""

from functools import lru_cache

<<<<<<< HEAD
from fastapi import Depends
=======
>>>>>>> origin/main
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import BatteryManager
from app.database import get_db


<<<<<<< HEAD
@lru_cache()
=======
@lru_cache
>>>>>>> origin/main
def get_battery_manager() -> BatteryManager:
    """Get singleton BatteryManager instance.

    Returns:
        BatteryManager instance (singleton)
    """
    return BatteryManager()


<<<<<<< HEAD
async def get_db_session() -> AsyncSession:
=======
async def get_db_session() -> AsyncSession:  # type: ignore[misc]
>>>>>>> origin/main
    """Dependency for database session.

    Yields:
        Async database session
    """
    async for session in get_db():
        yield session
