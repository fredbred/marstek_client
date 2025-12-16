"""Scheduled jobs for battery management."""

from datetime import datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import BatteryManager, ModeController
from app.database import async_session_maker

logger = structlog.get_logger(__name__)


async def job_switch_to_auto() -> None:
    """Exécuté à 6h00 - Passage mode AUTO pour la journée.

    Passe toutes les batteries actives en mode AUTO pour la période
    de la journée (6h-22h).
    """
    logger.info("scheduled_job_started", job="switch_to_auto")

    async with async_session_maker() as db:
        try:
            manager = BatteryManager()
            controller = ModeController(manager)

            results = await controller.switch_to_auto_mode(db)

            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)

            logger.info(
                "scheduled_job_completed",
                job="switch_to_auto",
                success_count=success_count,
                total_count=total_count,
            )

        except Exception as e:
            logger.error(
                "scheduled_job_failed",
                job="switch_to_auto",
                error=str(e),
                exc_info=True,
            )


async def job_switch_to_manual_night() -> None:
    """Exécuté à 22h00 - Passage mode MANUAL 0W pour la nuit.

    Passe toutes les batteries actives en mode MANUAL avec 0W de décharge
    pour la période de nuit (22h-6h) afin d'éviter la consommation
    pendant les heures creuses.
    """
    logger.info("scheduled_job_started", job="switch_to_manual_night")

    async with async_session_maker() as db:
        try:
            manager = BatteryManager()
            controller = ModeController(manager)

            results = await controller.switch_to_manual_night(db)

            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)

            logger.info(
                "scheduled_job_completed",
                job="switch_to_manual_night",
                success_count=success_count,
                total_count=total_count,
            )

        except Exception as e:
            logger.error(
                "scheduled_job_failed",
                job="switch_to_manual_night",
                error=str(e),
                exc_info=True,
            )


async def job_check_tempo_tomorrow() -> None:
    """Exécuté à 11h30 - Check RTE API et active précharge si jour rouge.

    Vérifie si le lendemain est un jour rouge Tempo et active la précharge
    des batteries si nécessaire pour optimiser la consommation.
    """
    logger.info("scheduled_job_started", job="check_tempo_tomorrow")

    async with async_session_maker() as db:
        try:
            from datetime import timedelta

            from app.config import get_settings
            from app.core.tempo_service import TempoColor, TempoService

            settings = get_settings()

            if not settings.tempo.enabled:
                logger.info("tempo_disabled", job="check_tempo_tomorrow")
                return

            # Vérifier si précharge nécessaire
            async with TempoService() as tempo_service:
                should_activate = await tempo_service.should_activate_precharge()

                if should_activate:
                    tomorrow = datetime.now().date() + timedelta(days=1)
                    logger.info(
                        "tempo_red_day_detected",
                        date=tomorrow.isoformat(),
                        action="activating_precharge",
                    )

                    manager = BatteryManager()
                    controller = ModeController(manager)

                    # Activer la précharge
                    await controller.activate_tempo_precharge(db, target_soc=95)

                    logger.info(
                        "tempo_precharge_activated",
                        date=tomorrow.isoformat(),
                    )
                else:
                    logger.debug(
                        "tempo_precharge_not_needed",
                    )

        except Exception as e:
            logger.error(
                "scheduled_job_failed",
                job="check_tempo_tomorrow",
                error=str(e),
                exc_info=True,
            )


async def job_monitor_batteries() -> None:
    """Exécuté toutes les 5 minutes - Log status + alertes.

    Récupère le status de toutes les batteries, le sauvegarde en TimescaleDB
    et envoie des alertes si nécessaire (SOC bas, température élevée, etc.).
    """
    logger.debug("scheduled_job_started", job="monitor_batteries")

    async with async_session_maker() as db:
        try:
            manager = BatteryManager()

            # Récupérer les status
            status_dict = await manager.get_all_status(db)

            # Logger en base de données
            await manager.log_status_to_db(db)

            # Vérifier les alertes
            for battery_id, status_data in status_dict.items():
                if "error" in status_data:
                    logger.warning(
                        "battery_monitoring_error",
                        battery_id=battery_id,
                        error=status_data["error"],
                    )
                    continue

                bat_status = status_data.get("bat_status")
                if not bat_status:
                    continue

                soc = bat_status.get("soc", 0)
                bat_temp = bat_status.get("bat_temp")

                # Alerte SOC bas
                if soc < 20:
                    logger.warning(
                        "battery_low_soc",
                        battery_id=battery_id,
                        soc=soc,
                    )
                    # TODO: Envoyer notification

                # Alerte température élevée
                if bat_temp and bat_temp > 45:
                    logger.warning(
                        "battery_high_temperature",
                        battery_id=battery_id,
                        temperature=bat_temp,
                    )
                    # TODO: Envoyer notification

            logger.debug("scheduled_job_completed", job="monitor_batteries")

        except Exception as e:
            logger.error(
                "scheduled_job_failed",
                job="monitor_batteries",
                error=str(e),
                exc_info=True,
            )


async def job_health_check() -> None:
    """Exécuté toutes les 1 minute - Vérifie connectivité batteries.

    Vérifie que toutes les batteries sont accessibles et met à jour
    le champ last_seen_at en base de données.
    """
    logger.debug("scheduled_job_started", job="health_check")

    async with async_session_maker() as db:
        try:
            from sqlalchemy import select, update

            from app.models import Battery

            # Récupérer toutes les batteries actives
            stmt = select(Battery).where(Battery.is_active == True)
            result = await db.execute(stmt)
            batteries = result.scalars().all()

            if not batteries:
                logger.debug("no_active_batteries_for_health_check")
                return

            manager = BatteryManager()

            # Vérifier chaque batterie
            for battery in batteries:
                try:
                    # Tentative de récupération du status (test de connectivité)
                    await manager.client.get_device_info(
                        battery.ip_address, battery.udp_port
                    )

                    # Mettre à jour last_seen_at
                    await db.execute(
                        update(Battery)
                        .where(Battery.id == battery.id)
                        .values(last_seen_at=datetime.utcnow())
                    )

                    logger.debug(
                        "battery_health_check_ok",
                        battery_id=battery.id,
                        ip=battery.ip_address,
                    )

                except Exception as e:
                    logger.warning(
                        "battery_health_check_failed",
                        battery_id=battery.id,
                        ip=battery.ip_address,
                        error=str(e),
                    )

            await db.commit()

            logger.debug("scheduled_job_completed", job="health_check")

        except Exception as e:
            logger.error(
                "scheduled_job_failed",
                job="health_check",
                error=str(e),
                exc_info=True,
            )
            await db.rollback()

