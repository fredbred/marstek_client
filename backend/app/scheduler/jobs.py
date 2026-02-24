"""Scheduled jobs for battery management."""

import asyncio
from datetime import datetime

import structlog
from sqlalchemy import select, update

from app.core import BatteryManager, ModeController
from app.core.marstek_client import MarstekUDPClient
from app.database import async_session_maker
from app.models import Battery

logger = structlog.get_logger(__name__)

# Rate limiting constants (based on Marstek API recommendations)
# See: https://github.com/jaapp/ha-marstek-local-api
MIN_POLLING_INTERVAL_SECONDS = 60  # Minimum 60s between polls per battery
DELAY_BETWEEN_BATTERIES_SECONDS = 20  # Delay between querying each battery
SOC_LOW_THRESHOLD = 20  # Percentage
TEMPERATURE_HIGH_THRESHOLD = 45  # Celsius


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
            from app.core.tempo_service import TempoService

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
    """Exécuté toutes les 5 minutes - Monitoring complet des batteries.

    Combine health check et monitoring en un seul job pour respecter
    les rate limits de l'API Marstek (min 60s entre requêtes par batterie).

    - Vérifie la connectivité de chaque batterie (1 requête légère)
    - Met à jour last_seen_at en base
    - Récupère SOC et température pour alertes
    - Envoie des alertes si nécessaire (SOC bas, température élevée)

    Rate limiting: Délai de 20s entre chaque batterie.
    """
    logger.debug("scheduled_job_started", job="monitor_batteries")

    async with async_session_maker() as db:
        try:
            # Récupérer toutes les batteries actives
            stmt = select(Battery).where(Battery.is_active)
            result = await db.execute(stmt)
            batteries = list(result.scalars().all())

            if not batteries:
                logger.debug("no_active_batteries_for_monitoring")
                return

            client = MarstekUDPClient(timeout=5.0, max_retries=2)
            online_count = 0
            offline_count = 0

            # Interroger chaque batterie avec un délai pour respecter rate limits
            for i, battery in enumerate(batteries):
                # Délai entre batteries (sauf pour la première)
                if i > 0:
                    logger.debug(
                        "rate_limit_delay",
                        delay_seconds=DELAY_BETWEEN_BATTERIES_SECONDS,
                        next_battery=battery.name,
                    )
                    await asyncio.sleep(DELAY_BETWEEN_BATTERIES_SECONDS)

                try:
                    # Récupérer le status batterie (1 seule requête légère)
                    bat_status = await client.get_battery_status(
                        battery.ip_address, battery.udp_port
                    )

                    # Batterie en ligne - mettre à jour last_seen_at
                    await db.execute(
                        update(Battery)
                        .where(Battery.id == battery.id)
                        .values(last_seen_at=datetime.utcnow())
                    )
                    online_count += 1

                    # Extraire les infos pour alertes
                    soc = bat_status.soc if bat_status else 0
                    bat_temp = bat_status.bat_temp if bat_status else None

                    # Alerte SOC bas
                    if soc < SOC_LOW_THRESHOLD:
                        logger.warning(
                            "battery_low_soc",
                            battery_id=battery.id,
                            battery_name=battery.name,
                            soc=soc,
                        )

                    # Alerte température élevée
                    if bat_temp and bat_temp > TEMPERATURE_HIGH_THRESHOLD:
                        logger.warning(
                            "battery_high_temperature",
                            battery_id=battery.id,
                            battery_name=battery.name,
                            temperature=bat_temp,
                        )

                    logger.debug(
                        "battery_monitoring_ok",
                        battery_id=battery.id,
                        battery_name=battery.name,
                        soc=soc,
                        temperature=bat_temp,
                    )

                except Exception as e:
                    offline_count += 1
                    logger.warning(
                        "battery_monitoring_failed",
                        battery_id=battery.id,
                        battery_name=battery.name,
                        ip=battery.ip_address,
                        error=str(e),
                    )

            await db.commit()

            # Log status global du monitoring
            logger.info(
                "scheduled_job_completed",
                job="monitor_batteries",
                online_count=online_count,
                offline_count=offline_count,
                total_count=len(batteries),
            )

        except Exception as e:
            logger.error(
                "scheduled_job_failed",
                job="monitor_batteries",
                error=str(e),
                exc_info=True,
            )
            await db.rollback()
