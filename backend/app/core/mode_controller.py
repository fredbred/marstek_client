"""Mode controller for battery operation modes."""

from datetime import datetime, time
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.battery_manager import BatteryManager
from app.core.marstek_client import MarstekAPIError
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

    async def switch_to_auto_mode(self, db: AsyncSession) -> dict[int, bool]:
        """Passe toutes les batteries en mode AUTO pour la journée (6h-22h).

        Args:
            db: Database session

        Returns:
            Dictionnaire {battery_id: success} indiquant le succès pour chaque batterie
        """
        logger.info("switching_to_auto_mode")

        mode_config = {"mode": "auto"}

        results = await self.battery_manager.set_mode_all(db, mode_config)

        # Vérifier les résultats et envoyer notifications
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)

        if success_count < total_count:
            failed_batteries = [
                bid for bid, success in results.items() if not success
            ]

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

    async def switch_to_manual_night(self, db: AsyncSession) -> dict[int, bool]:
        """Passe toutes les batteries en mode MANUAL pour la nuit HC (22h-6h).

        Configure le mode manuel avec 0W de décharge pour éviter la consommation
        pendant les heures creuses.

        Args:
            db: Database session

        Returns:
            Dictionnaire {battery_id: success} indiquant le succès pour chaque batterie
        """
        logger.info("switching_to_manual_night")

        # Configuration mode manuel nuit : 0W décharge, tous les jours
        manual_config = ManualConfig(
            time_num=0,
            start_time="22:00",
            end_time="06:00",
            week_set=127,  # Tous les jours
            power=0,  # 0W décharge
            enable=1,
        )

        mode_config = {
            "mode": "manual",
            "config": manual_config.model_dump(),
        }

        results = await self.battery_manager.set_mode_all(db, mode_config)

        # Vérifier les résultats
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)

        if success_count < total_count:
            failed_batteries = [
                bid for bid, success in results.items() if not success
            ]

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
        self, db: AsyncSession, target_soc: int = 95
    ) -> dict[int, bool]:
        """Active la charge forcée la veille d'un jour rouge Tempo.

        Configure les batteries pour charger jusqu'à target_soc% avant le jour rouge.

        Args:
            db: Database session
            target_soc: SOC cible pour la précharge (default: 95%)

        Returns:
            Dictionnaire {battery_id: success} indiquant le succès pour chaque batterie
        """
        logger.info("activating_tempo_precharge", target_soc=target_soc)

        # Pour la précharge Tempo, on utilise le mode Auto qui gère automatiquement
        # la charge optimale. On pourrait aussi utiliser un mode Manual avec
        # une configuration spécifique si nécessaire.

        # Pour l'instant, on active le mode Auto qui devrait charger les batteries
        results = await self.switch_to_auto_mode(db)

        if self.notification_service:
            success_count = sum(1 for success in results.values() if success)
            await self._send_notification(
                "⚡ Précharge Tempo activée",
                f"Les batteries sont en mode AUTO pour précharger à {target_soc}% "
                f"avant le jour rouge Tempo.",
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

