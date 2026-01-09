"""Mode controller for battery operation modes."""

from datetime import datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.battery_manager import BatteryManager
from app.models.marstek_api import ManualConfig

logger = structlog.get_logger(__name__)


class ModeController:
    """Logique métier des modes de fonctionnement des batteries.

    Gère les transitions entre modes selon le contexte (heure, jours Tempo, etc.)
    avec notifications et logging structuré.
    """

    def __init__(
        self,
        battery_manager: BatteryManager,
        notification_service: Any | None = None,
    ) -> None:
        """Initialize mode controller.

        Args:
            battery_manager: Battery manager instance
            notification_service: Service de notifications (Apprise, Telegram, etc.)
        """
        self.battery_manager = battery_manager
        self.notification_service = notification_service

    async def switch_to_auto_mode(self, db: AsyncSession, max_retries: int = 3) -> dict[int, bool]:
        """Passe toutes les batteries en mode AUTO pour la journée (6h-22h).

        Args:
            db: Database session
            max_retries: Nombre max de tentatives sur échec

        Returns:
            Dictionnaire {battery_id: success} indiquant le succès pour chaque batterie
        """
        import asyncio
        logger.info("switching_to_auto_mode", max_retries=max_retries)

        mode_config = {"mode": "auto"}

        results = await self.battery_manager.set_mode_all(db, mode_config)
        
        # Retry pour les batteries en échec
        for retry in range(1, max_retries):
            failed = [bid for bid, success in results.items() if not success]
            if not failed:
                break
            logger.info("retrying_failed_batteries", retry=retry, failed_batteries=failed)
            await asyncio.sleep(60.0)  # 60s avant retry
            retry_results = await self.battery_manager.set_mode_all(db, mode_config)
            for bid, success in retry_results.items():
                if success:
                    results[bid] = True

        # Vérifier les résultats et envoyer notifications
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)

        if success_count < total_count:
            failed_batteries = [bid for bid, success in results.items() if not success]
            failed_batteries = [bid for bid, success in results.items() if not success]

            logger.warning(
                "auto_mode_partial_failure",
                success_count=success_count,
                total_count=total_count,
                failed_batteries=failed_batteries,
            )

            if self.notification_service:
                await self._send_notification(
                    "⚠️ Mode AUTO - Échec partiel",
                    f"{success_count}/{total_count} batteries en mode AUTO. "
                    f"Batteries en échec: {failed_batteries}",
                    level="warning",
                )
        else:
            logger.info("auto_mode_success", battery_count=total_count)

            if self.notification_service:
                await self._send_notification(
                    "✅ Mode AUTO activé",
                    f"Toutes les batteries ({total_count}) sont maintenant en mode AUTO.",
                    level="info",
                )

        return results

    async def switch_to_manual_night(self, db: AsyncSession, max_retries: int = 3) -> dict[int, bool]:
        """Passe toutes les batteries en mode MANUAL pour la nuit HC (22h-6h).

        Si demain est un jour rouge Tempo, charge les batteries.
        Sinon, standby (0W).

        Args:
            db: Database session
            max_retries: Nombre max de tentatives sur échec

        Returns:
            Dictionnaire {battery_id: success} indiquant le succès pour chaque batterie
        """
        import asyncio
        from sqlalchemy import select
        from app.models import AppConfig
        from app.core.tempo_service import TempoService
        
        # Vérifier si demain est un jour rouge Tempo
        is_red_tomorrow = False
        precharge_power = -1000  # Valeur par défaut pour charge
        
        try:
            async with TempoService() as tempo_service:
                is_red_tomorrow = await tempo_service.should_activate_precharge()
            
            if is_red_tomorrow:
                # Récupérer la puissance de précharge depuis la config
                stmt = select(AppConfig).where(AppConfig.key == "tempo_precharge_power")
                result = await db.execute(stmt)
                config = result.scalar_one_or_none()
                if config:
                    precharge_power = int(config.value)
        except Exception as e:
            logger.warning("tempo_check_failed_in_manual_night", error=str(e))
        
        if is_red_tomorrow:
            logger.info("switching_to_manual_night_CHARGE_PASSIVE", 
                       max_retries=max_retries, 
                       reason="jour_rouge_demain",
                       power=precharge_power)
            
            # Utiliser mode PASSIVE pour la charge forcée (8h = 28800s)
            from sqlalchemy import select as sql_select
            from app.models import Battery
            
            stmt = sql_select(Battery).where(Battery.is_active)
            result = await db.execute(stmt)
            batteries = result.scalars().all()
            
            results: dict[int, bool] = {}
            cd_time = 28800  # 8 heures
            
            for battery in batteries:
                try:
                    success = await self.battery_manager.client.set_mode_passive(
                        battery.ip_address,
                        battery.udp_port,
                        power=precharge_power,
                        cd_time=cd_time,
                    )
                    results[battery.id] = success
                    logger.info(
                        "passive_charge_battery_result",
                        battery_id=battery.id,
                        success=success,
                        power=precharge_power,
                    )
                except Exception as e:
                    logger.error(
                        "passive_charge_battery_failed",
                        battery_id=battery.id,
                        error=str(e),
                    )
                    results[battery.id] = False
            
            return results
        
        logger.info("switching_to_manual_night_STANDBY", max_retries=max_retries)
        power_setting = 0  # Standby normal

        # Configuration mode manuel nuit (standby)
        manual_config = ManualConfig(
            time_num=0,
            start_time="22:00",
            end_time="06:00",
            week_set=127,  # Tous les jours
            power=power_setting,
            enable=1,  # 1 = ON, 0 = OFF
        )

        mode_config = {
            "mode": "manual",
            "config": manual_config.model_dump(),
        }

        results = await self.battery_manager.set_mode_all(db, mode_config)
        
        # Retry pour les batteries en échec
        for retry in range(1, max_retries):
            failed = [bid for bid, success in results.items() if not success]
            if not failed:
                break
            logger.info("retrying_manual_night", retry=retry, failed_batteries=failed)
            await asyncio.sleep(60.0)  # 60s avant retry
            retry_results = await self.battery_manager.set_mode_all(db, mode_config)
            for bid, success in retry_results.items():
                if success:
                    results[bid] = True

        # Vérifier les résultats
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)

        if success_count < total_count:
            failed_batteries = [bid for bid, success in results.items() if not success]

            logger.warning(
                "manual_night_partial_failure",
                success_count=success_count,
                total_count=total_count,
                failed_batteries=failed_batteries,
            )

            if self.notification_service:
                await self._send_notification(
                    "⚠️ Mode MANUAL Nuit - Échec partiel",
                    f"{success_count}/{total_count} batteries en mode MANUAL nuit. "
                    f"Batteries en échec: {failed_batteries}",
                    level="warning",
                )
        else:
            logger.info("manual_night_success", battery_count=total_count)

            if self.notification_service:
                await self._send_notification(
                    "🌙 Mode MANUAL Nuit activé",
                    f"Toutes les batteries ({total_count}) sont maintenant en mode MANUAL "
                    f"(0W décharge, 22h-6h).",
                    level="info",
                )

        return results

    async def activate_tempo_precharge(
        self, db: AsyncSession, target_soc: int = 95, power_limit: int = -1000
    ) -> dict[int, bool]:
        """Active la charge forcée la veille d'un jour rouge Tempo.

        Configure les batteries pour charger depuis le réseau jusqu'à target_soc% 
        avant le jour rouge.

        Args:
            db: Database session
            target_soc: SOC cible pour la précharge (default: 95%)
            power_limit: Puissance de charge en watts, NÉGATIF pour charger (default: -1000W)

        Returns:
            Dictionnaire {battery_id: success} indiquant le succès pour chaque batterie
        """
        logger.info("activating_tempo_precharge", target_soc=target_soc, power_limit=power_limit)

        # Pour la précharge Tempo, on utilise le mode PASSIVE avec power négatif
        # pour forcer la charge depuis le réseau (durée 8h = 28800s)
        from sqlalchemy import select
        from app.models import Battery
        
        stmt = select(Battery).where(Battery.is_active)
        result = await db.execute(stmt)
        batteries = result.scalars().all()
        
        results: dict[int, bool] = {}
        cd_time = 28800  # 8 heures
        
        for battery in batteries:
            try:
                success = await self.battery_manager.client.set_mode_passive(
                    battery.ip_address,
                    battery.udp_port,
                    power=power_limit,  # Valeur négative = CHARGE
                    cd_time=cd_time,
                )
                results[battery.id] = success
                logger.info(
                    "tempo_precharge_battery_result",
                    battery_id=battery.id,
                    success=success,
                    power=power_limit,
                    cd_time=cd_time,
                )
            except Exception as e:
                logger.error(
                    "tempo_precharge_battery_failed",
                    battery_id=battery.id,
                    error=str(e),
                )
                results[battery.id] = False

        if self.notification_service:
            sum(1 for success in results.values() if success)
            await self._send_notification(
                "⚡ Précharge Tempo activée",
                f"Les batteries sont en mode AUTO pour précharger à {target_soc}% "
                f"(puissance max: {power_limit}W) avant le jour rouge Tempo.",
                level="info",
            )

        return results

    async def get_recommended_mode(
        self, db: AsyncSession, current_time: datetime | None = None
    ) -> str:
        """Détermine le mode optimal selon le contexte.

        Prend en compte :
        - L'heure actuelle (6h-22h = Auto, 22h-6h = Manual nuit)
        - Les jours Tempo (précharge si jour rouge à venir)
        - L'état des batteries

        Args:
            db: Database session
            current_time: Heure actuelle (default: maintenant)

        Returns:
            Mode recommandé: "auto", "manual_night", ou "tempo_precharge"
        """
        if current_time is None:
            current_time = datetime.now()

        current_hour = current_time.hour

        # Logique basique : Auto 6h-22h, Manual nuit 22h-6h
        if 6 <= current_hour < 22:
            recommended = "auto"
        else:
            recommended = "manual_night"

        logger.debug(
            "mode_recommendation",
            current_hour=current_hour,
            recommended_mode=recommended,
        )

        # TODO: Intégrer la logique Tempo RTE pour détecter les jours rouges
        # et recommander "tempo_precharge" la veille

        return recommended

    async def _send_notification(
        self, title: str, message: str, level: str = "info"
    ) -> None:
        """Envoie une notification via le service de notifications.

        Args:
            title: Titre de la notification
            message: Message de la notification
            level: Niveau (info, warning, error)
        """
        if not self.notification_service:
            return

        try:
            # Adapter selon le service de notifications utilisé
            if hasattr(self.notification_service, "send_notification"):
                await self.notification_service.send_notification(
                    title, message, level=level
                )
            elif hasattr(self.notification_service, "notify"):
                await self.notification_service.notify(title, message)
            else:
                logger.warning(
                    "notification_service_incompatible",
                    service_type=type(self.notification_service).__name__,
                )
        except Exception as e:
            logger.error(
                "notification_send_failed",
                error=str(e),
                title=title,
            )
