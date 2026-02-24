"""Scheduled jobs for battery management."""

import asyncio
from datetime import datetime

import structlog
from sqlalchemy import select, update

from app.core import BatteryManager, ModeController
from app.core.marstek_client import MarstekUDPClient
from app.database import async_session_maker
from app.models import Battery
from app.notifications import Notifier

logger = structlog.get_logger(__name__)

# Rate limiting constants (based on Marstek API recommendations)
# See: https://github.com/jaapp/ha-marstek-local-api
MIN_POLLING_INTERVAL_SECONDS = 60  # Minimum 60s between polls per battery
DELAY_BETWEEN_BATTERIES_SECONDS = 20  # Delay between querying each battery
SOC_LOW_THRESHOLD = 20  # Percentage
TEMPERATURE_HIGH_THRESHOLD = 45  # Celsius

# Global notifier instance
_notifier: Notifier | None = None


def _get_notifier() -> Notifier:
    """Get or create notifier instance."""
    global _notifier
    if _notifier is None:
        _notifier = Notifier()
    return _notifier


async def job_switch_to_auto() -> None:
    """Exécuté à 6h00 - Passage mode AUTO pour la journée.

    Passe toutes les batteries actives en mode AUTO pour la période
    de la journée (6h-22h).
    """
    logger.info("scheduled_job_started", job="switch_to_auto")
    notifier = _get_notifier()

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

            # Notification
            if success_count == total_count:
                await notifier.send_info(
                    "Mode AUTO activé",
                    f"✅ {success_count}/{total_count} batteries en mode AUTO\n"
                    f"Heure: {datetime.now().strftime('%H:%M')}",
                )
            else:
                failed = [bid for bid, ok in results.items() if not ok]
                await notifier.send_warning(
                    "Mode AUTO - Échec partiel",
                    f"⚠️ {success_count}/{total_count} batteries OK\n"
                    f"Échecs: batteries {failed}\n"
                    f"Heure: {datetime.now().strftime('%H:%M')}",
                )

        except Exception as e:
            logger.error(
                "scheduled_job_failed",
                job="switch_to_auto",
                error=str(e),
                exc_info=True,
            )
            await notifier.send_error(
                "Erreur Mode AUTO",
                f"❌ Le job switch_to_auto a échoué\n" f"Erreur: {str(e)[:100]}",
            )


async def job_switch_to_manual_night() -> None:
    """Exécuté à 22h00 - Passage mode MANUAL 0W pour la nuit.

    Passe toutes les batteries actives en mode MANUAL avec 0W de décharge
    pour la période de nuit (22h-6h) afin d'éviter la consommation
    pendant les heures creuses.
    """
    logger.info("scheduled_job_started", job="switch_to_manual_night")
    notifier = _get_notifier()

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

            # Notification
            if success_count == total_count:
                await notifier.send_info(
                    "Mode NUIT activé",
                    f"🌙 {success_count}/{total_count} batteries en mode STANDBY (0W)\n"
                    f"Heure: {datetime.now().strftime('%H:%M')}",
                )
            else:
                failed = [bid for bid, ok in results.items() if not ok]
                await notifier.send_warning(
                    "Mode NUIT - Échec partiel",
                    f"⚠️ {success_count}/{total_count} batteries OK\n"
                    f"Échecs: batteries {failed}\n"
                    f"Heure: {datetime.now().strftime('%H:%M')}",
                )

        except Exception as e:
            logger.error(
                "scheduled_job_failed",
                job="switch_to_manual_night",
                error=str(e),
                exc_info=True,
            )
            await notifier.send_error(
                "Erreur Mode NUIT",
                f"❌ Le job switch_to_manual_night a échoué\n" f"Erreur: {str(e)[:100]}",
            )


async def job_check_tempo_tomorrow() -> None:
    """Exécuté à 12h30 - Check RTE API et active précharge si jour rouge.

    Vérifie si le lendemain est un jour rouge Tempo et active la précharge
    des batteries si nécessaire pour optimiser la consommation.
    """
    logger.info("scheduled_job_started", job="check_tempo_tomorrow")
    notifier = _get_notifier()

    async with async_session_maker() as db:
        try:
            from datetime import timedelta

            from app.config import get_settings
            from app.core.tempo_service import TempoColor, TempoService

            settings = get_settings()

            if not settings.tempo.enabled:
                logger.info("tempo_disabled", job="check_tempo_tomorrow")
                return

            async with TempoService() as tempo_service:
                tomorrow = datetime.now().date() + timedelta(days=1)
                color = await tempo_service.get_tempo_color(tomorrow)

                if color == TempoColor.RED:
                    logger.info(
                        "tempo_red_day_detected",
                        date=tomorrow.isoformat(),
                        action="activating_precharge",
                    )

                    manager = BatteryManager()
                    controller = ModeController(manager)

                    await controller.activate_tempo_precharge(db, target_soc=95)

                    logger.info(
                        "tempo_precharge_activated",
                        date=tomorrow.isoformat(),
                    )

                    # Notification jour rouge
                    await notifier.send_warning(
                        "🔴 JOUR ROUGE DEMAIN",
                        f"Date: {tomorrow.strftime('%d/%m/%Y')}\n\n"
                        f"Programme:\n"
                        f"• 22h00: Charge batteries à 95%\n"
                        f"• 06h00: Mode AUTO\n\n"
                        f"Évitez la consommation en heures pleines!",
                    )
                else:
                    logger.debug(
                        "tempo_precharge_not_needed",
                        color=color.value if color else "unknown",
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
            stmt = select(Battery).where(Battery.is_active)
            result = await db.execute(stmt)
            batteries = list(result.scalars().all())

            if not batteries:
                logger.debug("no_active_batteries_for_monitoring")
                return

            client = MarstekUDPClient(timeout=5.0, max_retries=2)
            online_count = 0
            offline_count = 0

            for i, battery in enumerate(batteries):
                if i > 0:
                    logger.debug(
                        "rate_limit_delay",
                        delay_seconds=DELAY_BETWEEN_BATTERIES_SECONDS,
                        next_battery=battery.name,
                    )
                    await asyncio.sleep(DELAY_BETWEEN_BATTERIES_SECONDS)

                try:
                    bat_status = await client.get_battery_status(
                        battery.ip_address, battery.udp_port
                    )

                    await db.execute(
                        update(Battery)
                        .where(Battery.id == battery.id)
                        .values(last_seen_at=datetime.utcnow())
                    )
                    online_count += 1

                    soc = bat_status.soc if bat_status else 0
                    bat_temp = bat_status.bat_temp if bat_status else None

                    if soc < SOC_LOW_THRESHOLD:
                        logger.warning(
                            "battery_low_soc",
                            battery_id=battery.id,
                            battery_name=battery.name,
                            soc=soc,
                        )

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

            logger.info(
                "scheduled_job_completed",
                job="monitor_batteries",
                online_count=online_count,
                offline_count=offline_count,
                total_count=len(batteries),
            )

            # Alerte si toutes les batteries sont offline
            if offline_count == len(batteries) and len(batteries) > 0:
                notifier = _get_notifier()
                await notifier.send_error(
                    "🚨 TOUTES BATTERIES HORS LIGNE",
                    f"Aucune des {len(batteries)} batteries ne répond!\n"
                    f"Vérifiez le réseau et l'API Marstek.",
                )

        except Exception as e:
            logger.error(
                "scheduled_job_failed",
                job="monitor_batteries",
                error=str(e),
                exc_info=True,
            )
            await db.rollback()
