"""Script to initialize database with tables and TimescaleDB hypertables."""

import asyncio

from app.database import init_db


async def main() -> None:
    """Initialize database."""
    print("Initializing database...")
    await init_db()
    print("Database initialized successfully!")


if __name__ == "__main__":
    asyncio.run(main())

