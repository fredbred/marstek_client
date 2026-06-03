"""Scheduled jobs for battery management."""

import asyncio
from datetime import datetime, timedelta

import structlog

from app.core import BatteryManager, ModeController
from app.database import async_session_maker

logger = structlog.get_logger(__name__)

SOC_LOW_THRESHOLD = 20
SOC_FULL_THRESHOLD = 100

# Anti-spam des notifications SOC 100 %, reset chaque jour.
_soc_100_notified: dict[int, str] = {}


async def job_switch_to_auto() -> None:
    """Exécuté à 6h00 - Passage mode AUTO pour la journée.

    Passe toutes les batteries actives en mode AUTO pour la période
    de la journée (6h-22h).
    """
    from datetime import datetime

    from app.notifications import Notifier

    start_time = datetime.now()
    notifier = Notifier()
    logger.info(
        "scheduled_job_started",
        job="switch_to_auto",
        start_time=start_time.isoformat(),
        description="Passage en mode AUTO pour consommation journée",
    )

    async with async_session_maker() as db:
        try:
            manager = BatteryManager()
            controller = ModeController(manager, notification_service=notifier)

            results = await controller.switch_to_auto_mode(db)

            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)
            failed_batteries = [bid for bid, success in results.items() if not success]

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            logger.info(
                "scheduled_job_completed",
                job="switch_to_auto",
                success_count=success_count,
                total_count=total_count,
                failed_batteries=failed_batteries if failed_batteries else None,
                duration_seconds=duration,
                end_time=end_time.isoformat(),
                results=results,
            )

            # Log individuel par batterie pour traçabilité
            for battery_id, success in results.items():
                logger.info(
                    "battery_mode_change_result",
                    job="switch_to_auto",
                    battery_id=battery_id,
                    success=success,
                    target_mode="AUTO",
                )

        except Exception as e:
            logger.error(
                "scheduled_job_failed",
                job="switch_to_auto",
                error=str(e),
                exc_info=True,
            )
            await notifier.send_error(
                "Erreur passage AUTO",
                f"Le passage en mode AUTO de 6h00 a échoué: {str(e)[:200]}",
            )


async def job_switch_to_manual_night() -> None:
    """Exécuté à 22h00 - Check Tempo nuit et précharge si rouge.

    Hors jour rouge demain, aucune commande batterie n'est envoyée :
    les batteries restent en Auto / autoconsommation.
    """
    from datetime import datetime

    from app.notifications import Notifier

    start_time = datetime.now()
    notifier = Notifier()
    logger.info(
        "scheduled_job_started",
        job="switch_to_manual_night",
        start_time=start_time.isoformat(),
        description="Check Tempo nuit, précharge seulement si rouge demain",
    )

    async with async_session_maker() as db:
        try:
            manager = BatteryManager()
            controller = ModeController(manager, notification_service=notifier)

            results = await controller.switch_to_manual_night(db)

            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)
            failed_batteries = [bid for bid, success in results.items() if not success]

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            logger.info(
                "scheduled_job_completed",
                job="switch_to_manual_night",
                success_count=success_count,
                total_count=total_count,
                failed_batteries=failed_batteries if failed_batteries else None,
                duration_seconds=duration,
                end_time=end_time.isoformat(),
                results=results,
            )

            # Log individuel par batterie
            for battery_id, success in results.items():
                logger.info(
                    "battery_mode_change_result",
                    job="switch_to_manual_night",
                    battery_id=battery_id,
                    success=success,
                    target_mode="TEMPO_NIGHT_PRECHARGE",
                )

        except Exception as e:
            logger.error(
                "scheduled_job_failed",
                job="switch_to_manual_night",
                error=str(e),
                exc_info=True,
            )
            await notifier.send_error(
                "Erreur check Tempo nuit",
                f"Le check Tempo de 22h00 a échoué: {str(e)[:200]}",
            )


async def job_check_tempo_tomorrow() -> None:
    """Exécuté à 12h30 - Détecte jour rouge demain (pas de charge en HP).

    La charge réseau est déclenchée à 22h00 (heures creuses), en mode Passive
    (affichage type UPS), via switch_to_manual_night.
    """
    logger.info("scheduled_job_started", job="check_tempo_tomorrow")
    from app.notifications import Notifier

    notifier = Notifier()

    try:
        from app.config import get_settings
        from app.core.tempo_service import (
            TempoColor,
            TempoService,
            scheduler_today_date,
        )

        settings = get_settings()

        if not settings.tempo.enabled:
            logger.info("tempo_disabled", job="check_tempo_tomorrow")
            return

        async with TempoService() as tempo_service:
            tomorrow = scheduler_today_date() + timedelta(days=1)
            color = await tempo_service.get_tempo_color(tomorrow, force_refresh=True)

            if color == TempoColor.RED:
                logger.info(
                    "tempo_red_day_detected",
                    date=tomorrow.isoformat(),
                    action="notify_only_no_midday_charge",
                )

                await notifier.send_warning(
                    "🔴 JOUR ROUGE DEMAIN",
                    f"Date: {tomorrow.strftime('%d/%m/%Y')}\n\n"
                    f"Pas de charge aux heures pleines (12h30).\n"
                    f"Programme:\n"
                    f"• 22h00: charge HC (mode Passive / type UPS, "
                    f"puissance configurée tempo_precharge_power)\n"
                    f"• 06h00: mode AUTO\n\n"
                    f"Évitez la consommation aux heures pleines.",
                )

                logger.info(
                    "tempo_red_notification_sent_awaiting_22h_precharge",
                    date=tomorrow.isoformat(),
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
    """Exécuté toutes les 10 minutes - Rafraîchit le cache des batteries.

    Récupère le status de chaque batterie avec délai entre chaque
    pour éviter le rate limiting des VenusE.
    """
    logger.info("scheduled_job_started", job="monitor_batteries")
    from app.notifications import Notifier

    notifier = Notifier()
    today = datetime.now().strftime("%Y-%m-%d")

    async with async_session_maker() as db:
        try:
            from sqlalchemy import select, update

            from app.models import Battery

            manager = BatteryManager()

            # Récupérer les batteries actives
            stmt = select(Battery).where(Battery.is_active)
            result = await db.execute(stmt)
            batteries = result.scalars().all()
            battery_by_id = {battery.id: battery for battery in batteries}

            # Rafraîchir chaque batterie avec délai de 120s
            for i, battery in enumerate(batteries):
                logger.info(
                    "refreshing_battery",
                    battery_id=battery.id,
                    index=i + 1,
                    total=len(batteries),
                )
                await manager.refresh_single_battery(battery)

                # Attendre 120s avant la prochaine batterie (sauf la dernière)
                if i < len(batteries) - 1:
                    await asyncio.sleep(120.0)

            # Récupérer les status depuis le cache
            status_dict = await manager.get_all_status(db)

            # Mettre à jour last_seen_at pour les batteries qui répondent (health check)
            for battery_id, status_data in status_dict.items():
                if "error" not in status_data:
                    await db.execute(
                        update(Battery)
                        .where(Battery.id == battery_id)
                        .values(last_seen_at=datetime.utcnow())
                    )

            await db.commit()

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
                alert_battery = battery_by_id.get(battery_id)

                # Alerte SOC bas
                if soc < SOC_LOW_THRESHOLD:
                    logger.warning(
                        "battery_low_soc",
                        battery_id=battery_id,
                        soc=soc,
                    )
                    # TODO: Envoyer notification

                # Notification batterie pleine (une fois par jour / batterie)
                if (
                    alert_battery is not None
                    and soc >= SOC_FULL_THRESHOLD
                    and _soc_100_notified.get(battery_id) != today
                ):
                    await notifier.send_info(
                        "Batterie pleine",
                        f"{alert_battery.name} ({alert_battery.ip_address}) est à {soc} %.",
                    )
                    _soc_100_notified[battery_id] = today
                    logger.info(
                        "battery_full_notified",
                        battery_id=battery_id,
                        soc=soc,
                        date=today,
                    )

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
            await db.rollback()


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
            stmt = select(Battery).where(Battery.is_active)
            result = await db.execute(stmt)
            batteries = result.scalars().all()

            if not batteries:
                logger.debug("no_active_batteries_for_health_check")
                return

            manager = BatteryManager()

            # Vérifier chaque batterie avec délai pour éviter rate limiting
            for i, battery in enumerate(batteries):
                if i > 0:
                    await asyncio.sleep(3)  # 3 secondes entre chaque batterie

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
