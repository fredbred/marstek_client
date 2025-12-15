"""Point d'entrée principal de l'application."""

import asyncio
import signal
from pathlib import Path

from marstek.core.config import AppConfig
from marstek.core.logger import configure_logging, get_logger
from marstek.database.models import Database
from marstek.scheduler.battery_manager import BatteryManager

logger = get_logger(__name__)


async def main() -> None:
    """Fonction principale."""
    # Charger la configuration
    config_path = Path("config/config.yaml")
    if not config_path.exists():
        logger.error("config_file_not_found", path=str(config_path))
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    config = AppConfig.from_yaml(config_path)

    # Configurer le logging
    configure_logging(config.logging)

    logger.info("marstek_automation_starting", version="0.1.0")

    # Initialiser la base de données
    db = Database(config.database)
    await db.create_tables()
    logger.info("database_initialized")

    # Initialiser le gestionnaire de batteries
    manager = BatteryManager(config)
    await manager.initialize()
    manager.start()

    logger.info("marstek_automation_started")

    # Gestion des signaux pour arrêt propre
    shutdown_event = asyncio.Event()

    def signal_handler() -> None:
        """Handler pour signaux d'arrêt."""
        logger.info("shutdown_signal_received")
        shutdown_event.set()

    # Enregistrer les handlers
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    try:
        # Attendre l'événement d'arrêt
        await shutdown_event.wait()
    except KeyboardInterrupt:
        logger.info("keyboard_interrupt_received")
    finally:
        # Arrêt propre
        logger.info("shutting_down")
        await manager.shutdown()
        await db.close()
        logger.info("marstek_automation_stopped")


if __name__ == "__main__":
    asyncio.run(main())

