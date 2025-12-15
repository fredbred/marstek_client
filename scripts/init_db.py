"""Script d'initialisation de la base de données."""

import asyncio
from pathlib import Path

from marstek.core.config import AppConfig
from marstek.core.logger import configure_logging, get_logger
from marstek.database.models import Database

logger = get_logger(__name__)


async def init_database() -> None:
    """Initialise la base de données et crée les tables."""
    config_path = Path("config/config.yaml")
    if not config_path.exists():
        logger.error("config_file_not_found", path=str(config_path))
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    config = AppConfig.from_yaml(config_path)
    configure_logging(config.logging)

    logger.info("initializing_database")

    db = Database(config.database)
    await db.create_tables()

    logger.info("database_initialized_successfully")

    await db.close()


if __name__ == "__main__":
    asyncio.run(init_database())

