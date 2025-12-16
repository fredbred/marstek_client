"""Database configuration and session management."""

<<<<<<< HEAD
from typing import AsyncGenerator
=======
from collections.abc import AsyncGenerator
>>>>>>> origin/main

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.models.base import Base

settings = get_settings()

# Create async engine
async_engine = create_async_engine(
    settings.database.url,
    echo=settings.database.echo,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Create async session factory
async_session_maker = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session.

    Yields:
        Async database session

    Example:
        ```python
        async def my_endpoint(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Battery))
            return result.scalars().all()
        ```
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database: create tables and TimescaleDB hypertables."""
<<<<<<< HEAD
    from app.models.base import Base
=======
>>>>>>> origin/main
    from app.models.battery import Battery
    from app.models.schedule import ScheduleConfig
    from app.models.status_log import BatteryStatusLog

    # Import all models to register them
    _ = (Battery, BatteryStatusLog, ScheduleConfig)

    # Create all tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create TimescaleDB hypertable for battery_status_logs
    async with async_engine.begin() as conn:
        from sqlalchemy import text

        # Enable TimescaleDB extension if not already enabled
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb;"))

        # Create hypertable (will fail gracefully if already exists)
        await conn.execute(
            text(
                """
                SELECT create_hypertable(
                    'battery_status_logs',
                    'timestamp',
                    if_not_exists => TRUE,
                    chunk_time_interval => INTERVAL '1 day'
                );
                """
            )
        )


async def close_db() -> None:
    """Close database connections."""
    await async_engine.dispose()
<<<<<<< HEAD

=======
>>>>>>> origin/main
