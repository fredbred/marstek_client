"""Gestionnaire automatique des modes de batteries."""

import asyncio
from datetime import datetime, time
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from marstek.api.marstek_client import BatteryStatus, MarstekClient
from marstek.core.config import AppConfig, BatteryConfig, ModeConfig
from marstek.core.logger import get_logger
from marstek.services.telegram import TelegramService
from marstek.services.tempo import TempoService

logger = get_logger(__name__)


class BatteryManager:
    """Gestionnaire pour automatiser les modes des batteries.

    Gère les transitions automatiques entre modes AUTO et MANUAL
    selon les horaires configurés et les jours Tempo.
    """

    def __init__(self, config: AppConfig) -> None:
        """Initialize battery manager.

        Args:
            config: Configuration de l'application
        """
        self.config = config
        self.scheduler = AsyncIOScheduler(
            timezone=config.scheduler.timezone,
            max_workers=config.scheduler.max_workers,
        )
        self.clients: dict[str, MarstekClient] = {}
        self.telegram = TelegramService(config.telegram)
        self.tempo = TempoService(config.tempo)
        self._current_modes: dict[str, str] = {}

    async def initialize(self) -> None:
        """Initialise les clients et démarre le scheduler."""
        # Créer les clients pour chaque batterie
        for battery_config in self.config.batteries:
            client = MarstekClient(battery_config)
            await client.connect()
            self.clients[battery_config.id] = client

            # Lire le mode actuel
            try:
                status = await client.read_status()
                self._current_modes[battery_config.id] = status.mode or "UNKNOWN"
            except Exception as e:
                logger.warning(
                    "failed_to_read_initial_status",
                    battery_id=battery_config.id,
                    error=str(e),
                )
                self._current_modes[battery_config.id] = "UNKNOWN"

        # Configurer les jobs du scheduler
        self._setup_scheduler_jobs()

        logger.info(
            "battery_manager_initialized",
            batteries=len(self.clients),
            timezone=self.config.scheduler.timezone,
        )

    def _setup_scheduler_jobs(self) -> None:
        """Configure les jobs du scheduler."""
        auto_mode = self.config.modes["auto"]
        manual_mode = self.config.modes["manual"]

        # Job pour passer en mode AUTO (6h)
        self.scheduler.add_job(
            self._switch_to_auto_mode,
            trigger=CronTrigger(hour=auto_mode.start_hour, minute=0),
            id="switch_to_auto",
            name="Switch to AUTO mode",
            replace_existing=True,
        )

        # Job pour passer en mode MANUAL (22h)
        self.scheduler.add_job(
            self._switch_to_manual_mode,
            trigger=CronTrigger(hour=manual_mode.start_hour, minute=0),
            id="switch_to_manual",
            name="Switch to MANUAL mode",
            replace_existing=True,
        )

        # Job pour monitoring périodique (toutes les 5 minutes)
        self.scheduler.add_job(
            self._monitor_batteries,
            trigger=CronTrigger(minute="*/5"),
            id="monitor_batteries",
            name="Monitor battery status",
            replace_existing=True,
        )

        # Job pour vérifier les jours Tempo (tous les jours à minuit)
        if self.config.tempo.enabled:
            self.scheduler.add_job(
                self._check_tempo_days,
                trigger=CronTrigger(hour=0, minute=0),
                id="check_tempo",
                name="Check Tempo days",
                replace_existing=True,
            )

    async def _switch_to_auto_mode(self) -> None:
        """Passe toutes les batteries en mode Auto."""
        logger.info("switching_to_auto_mode")

        for battery_id, client in self.clients.items():
            try:
                old_mode = self._current_modes.get(battery_id, "UNKNOWN")
                success = await client.set_mode("Auto")

                if success:
                    self._current_modes[battery_id] = "Auto"
                    await self.telegram.notify_mode_change(
                        battery_id, old_mode, "Auto"
                    )
                else:
                    logger.error(
                        "failed_to_switch_to_auto",
                        battery_id=battery_id,
                    )
                    await self.telegram.notify_error(
                        battery_id, "Échec passage en mode Auto"
                    )

            except Exception as e:
                logger.error(
                    "error_switching_to_auto",
                    battery_id=battery_id,
                    error=str(e),
                )
                await self.telegram.notify_error(
                    battery_id, f"Erreur passage Auto: {str(e)}"
                )

    async def _switch_to_manual_mode(self) -> None:
        """Passe toutes les batteries en mode Manual."""
        logger.info("switching_to_manual_mode")

        for battery_id, client in self.clients.items():
            try:
                old_mode = self._current_modes.get(battery_id, "UNKNOWN")
                success = await client.set_mode("Manual")

                if success:
                    self._current_modes[battery_id] = "Manual"
                    await self.telegram.notify_mode_change(
                        battery_id, old_mode, "Manual"
                    )
                else:
                    logger.error(
                        "failed_to_switch_to_manual",
                        battery_id=battery_id,
                    )
                    await self.telegram.notify_error(
                        battery_id, "Échec passage en mode Manual"
                    )

            except Exception as e:
                logger.error(
                    "error_switching_to_manual",
                    battery_id=battery_id,
                    error=str(e),
                )
                await self.telegram.notify_error(
                    battery_id, f"Erreur passage Manual: {str(e)}"
                )

    async def _monitor_batteries(self) -> None:
        """Surveille le status de toutes les batteries."""
        logger.debug("monitoring_batteries")

        for battery_id, client in self.clients.items():
            try:
                status = await client.read_status()

                # Enregistrer dans la DB (à implémenter)
                # await self._save_status_to_db(battery_id, status)

                # Vérifier les alertes (SOC bas, température élevée, etc.)
                if status.soc is not None and status.soc < 20:
                    await self.telegram.send_notification(
                        f"Batterie {battery_id}",
                        f"SOC faible: {status.soc}%",
                        level="WARNING",
                    )

                if status.temperature is not None and status.temperature > 45:
                    await self.telegram.send_notification(
                        f"Batterie {battery_id}",
                        f"Température élevée: {status.temperature}°C",
                        level="WARNING",
                    )

            except Exception as e:
                logger.error(
                    "monitoring_error",
                    battery_id=battery_id,
                    error=str(e),
                )

    async def _check_tempo_days(self) -> None:
        """Vérifie les jours Tempo et ajuste si nécessaire."""
        if not self.config.tempo.enabled:
            return

        try:
            is_red = await self.tempo.is_red_day()
            upcoming_red_days = await self.tempo.get_upcoming_red_days(days_ahead=7)

            if is_red:
                logger.info("tempo_red_day_detected")
                # Optionnel: ajuster le comportement en jour rouge
                # Par exemple, charger plus agressivement la veille

            if upcoming_red_days:
                message = f"Jours rouges à venir: {len(upcoming_red_days)}"
                await self.telegram.send_notification(
                    "Alerte Tempo", message, level="INFO"
                )

        except Exception as e:
            logger.error("tempo_check_error", error=str(e))

    def start(self) -> None:
        """Démarre le scheduler."""
        self.scheduler.start()
        logger.info("battery_manager_started")

    def stop(self) -> None:
        """Arrête le scheduler."""
        self.scheduler.shutdown()
        logger.info("battery_manager_stopped")

    async def shutdown(self) -> None:
        """Arrête proprement tous les clients."""
        self.stop()

        for battery_id, client in self.clients.items():
            try:
                await client.disconnect()
            except Exception as e:
                logger.error(
                    "error_disconnecting_client",
                    battery_id=battery_id,
                    error=str(e),
                )

        await self.tempo.close()

        logger.info("battery_manager_shutdown_complete")

