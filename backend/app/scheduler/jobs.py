"""Scheduled jobs for battery management."""

import asyncio
from datetime import datetime

import structlog

from app.core import BatteryManager, ModeController
from app.database import async_session_maker

logger = structlog.get_logger(__name__)


async def job_switch_to_auto() -> None:
    """Exécuté à 6h00 - Passage mode AUTO pour la journée.

    Passe toutes les batteries actives en mode AUTO pour la période
    de la journée (6h-22h).
    """
    from datetime import datetime

    start_time = datetime.now()
    logger.info(
        "scheduled_job_started",
        job="switch_to_auto",
        start_time=start_time.isoformat(),
        description="Passage en mode AUTO pour consommation journée",
    )

    async with async_session_maker() as db:
        try:
            manager = BatteryManager()
            controller = ModeController(manager)

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


async def job_switch_to_manual_night() -> None:
    """Exécuté à 22h00 - Passage mode MANUAL 0W pour la nuit.

    Passe toutes les batteries actives en mode MANUAL avec 0W de décharge
    pour la période de nuit (22h-6h) afin d'éviter la consommation
    pendant les heures creuses.
    """
    from datetime import datetime

    start_time = datetime.now()
    logger.info(
        "scheduled_job_started",
        job="switch_to_manual_night",
        start_time=start_time.isoformat(),
        description="Passage en mode MANUAL 0W pour nuit HC",
    )

    async with async_session_maker() as db:
        try:
            manager = BatteryManager()
            controller = ModeController(manager)

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
                    target_mode="MANUAL_NIGHT",
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

            # Récupérer la config Tempo depuis la base
            from sqlalchemy import select

            from app.models import AppConfig

            stmt = select(AppConfig).where(
                AppConfig.key.in_(["tempo_target_soc_red", "tempo_precharge_power"])
            )
            result = await db.execute(stmt)
            configs = {row.key: row.value for row in result.scalars().all()}
            target_soc = int(configs.get("tempo_target_soc_red", "95"))
            precharge_power = int(configs.get("tempo_precharge_power", "2000"))

            # Vérifier si précharge nécessaire
            async with TempoService() as tempo_service:
                should_activate = await tempo_service.should_activate_precharge()

                if should_activate:
                    tomorrow = datetime.now().date() + timedelta(days=1)
                    logger.info(
                        "tempo_red_day_detected",
                        date=tomorrow.isoformat(),
                        action="activating_precharge",
                        target_soc=target_soc,
                    )

                    manager = BatteryManager()
                    controller = ModeController(manager)

                    # Activer la précharge avec le SOC et la puissance configurés
                    await controller.activate_tempo_precharge(
                        db, target_soc=target_soc, power_limit=precharge_power
                    )

                    logger.info(
                        "tempo_precharge_activated",
                        date=tomorrow.isoformat(),
                        target_soc=target_soc,
                        precharge_power=precharge_power,
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
    """Exécuté toutes les 10 minutes - Rafraîchit le cache des batteries.

    Récupère le status de chaque batterie avec délai entre chaque
    pour éviter le rate limiting des VenusE.
    """
    logger.info("scheduled_job_started", job="monitor_batteries")

    async with async_session_maker() as db:
        try:
            from sqlalchemy import select, update

            from app.models import Battery

            manager = BatteryManager()

            # Récupérer les batteries actives
            stmt = select(Battery).where(Battery.is_active)
            result = await db.execute(stmt)
            batteries = result.scalars().all()

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
