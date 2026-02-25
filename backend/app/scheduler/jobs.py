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
MIN_POLLING_INTERVAL_SECONDS = 60
DELAY_BETWEEN_BATTERIES_SECONDS = 20
SOC_LOW_THRESHOLD = 20
SOC_FULL_THRESHOLD = 100
TEMPERATURE_HIGH_THRESHOLD = 45

# State tracking for notifications (avoid spam)
_consecutive_all_offline = 0  # Count consecutive "all offline" events
_soc_100_notified: dict[int, bool] = {}  # Track SOC 100% notifications per battery
_last_monitoring_date: str = ""  # Reset SOC notifications daily

CONSECUTIVE_FAILURES_BEFORE_ALERT = 3  # Require 3 consecutive failures

# Global notifier instance
_notifier: Notifier | None = None


def _get_notifier() -> Notifier:
    """Get or create notifier instance."""
    global _notifier
    if _notifier is None:
        _notifier = Notifier()
    return _notifier


async def job_switch_to_auto() -> None:
    """Exécuté à 6h00 - Passage mode AUTO pour la journée."""
    logger.info("scheduled_job_started", job="switch_to_auto")
    notifier = _get_notifier()

    # Reset SOC 100% notifications for new day
    global _soc_100_notified
    _soc_100_notified = {}

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
                f"❌ Le job switch_to_auto a échoué\nErreur: {str(e)[:100]}",
            )


async def job_switch_to_manual_night() -> None:
    """Exécuté à 22h00 - Passage mode MANUAL 0W pour la nuit."""
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

            if success_count == total_count:
                await notifier.send_info(
                    "Mode NUIT activé",
                    f"🌙 {success_count}/{total_count} batteries en STANDBY (0W)\n"
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
                f"❌ Le job switch_to_manual_night a échoué\nErreur: {str(e)[:100]}",
            )


async def job_check_tempo_tomorrow() -> None:
    """Exécuté à 12h30 - Check RTE API et active précharge si jour rouge."""
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

                    logger.info("tempo_precharge_activated", date=tomorrow.isoformat())

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
    """Exécuté toutes les 5 minutes - Monitoring complet des batteries."""
    global _consecutive_all_offline, _soc_100_notified, _last_monitoring_date

    logger.debug("scheduled_job_started", job="monitor_batteries")

    # Reset SOC notifications at midnight
    today = datetime.now().strftime("%Y-%m-%d")
    if today != _last_monitoring_date:
        _soc_100_notified = {}
        _last_monitoring_date = today
        logger.debug("soc_notifications_reset", date=today)

    async with async_session_maker() as db:
        try:
            stmt = select(Battery).where(Battery.is_active)
            result = await db.execute(stmt)
            batteries = list(result.scalars().all())

            if not batteries:
                logger.debug("no_active_batteries_for_monitoring")
                return

            client = MarstekUDPClient(timeout=5.0, max_retries=2)
            notifier = _get_notifier()
            online_count = 0
            offline_count = 0

            for i, battery in enumerate(batteries):
                if i > 0:
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

                    # Notification SOC 100% (once per day per battery)
                    if soc >= SOC_FULL_THRESHOLD:
                        if not _soc_100_notified.get(battery.id, False):
                            _soc_100_notified[battery.id] = True
                            await notifier.send_info(
                                "🔋 Batterie 100%",
                                f"{battery.name} est complètement chargée!\n"
                                f"SOC: {soc}%",
                            )
                            logger.info(
                                "soc_100_notification_sent",
                                battery_id=battery.id,
                                battery_name=battery.name,
                            )
                    elif soc < 95:
                        # Reset notification flag when SOC drops
                        _soc_100_notified[battery.id] = False

                    # Alert low SOC
                    if soc < SOC_LOW_THRESHOLD:
                        logger.warning(
                            "battery_low_soc",
                            battery_id=battery.id,
                            battery_name=battery.name,
                            soc=soc,
                        )

                    # Alert high temperature
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

            # Alert only after CONSECUTIVE failures (avoid false positives)
            if offline_count == len(batteries) and len(batteries) > 0:
                _consecutive_all_offline += 1
                logger.warning(
                    "all_batteries_offline",
                    consecutive_count=_consecutive_all_offline,
                    threshold=CONSECUTIVE_FAILURES_BEFORE_ALERT,
                )

                if _consecutive_all_offline >= CONSECUTIVE_FAILURES_BEFORE_ALERT:
                    await notifier.send_error(
                        "🚨 TOUTES BATTERIES HORS LIGNE",
                        f"Aucune des {len(batteries)} batteries ne répond "
                        f"depuis {_consecutive_all_offline * 5} minutes!\n"
                        f"Vérifiez le réseau et l'API Marstek.",
                    )
            else:
                # Reset counter if at least one battery responds
                if _consecutive_all_offline > 0:
                    logger.info(
                        "batteries_back_online",
                        previous_consecutive_failures=_consecutive_all_offline,
                    )
                _consecutive_all_offline = 0

        except Exception as e:
            logger.error(
                "scheduled_job_failed",
                job="monitor_batteries",
                error=str(e),
                exc_info=True,
            )
            await db.rollback()
