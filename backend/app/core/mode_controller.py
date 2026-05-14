"""Mode controller for battery operation modes."""

from datetime import datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.battery_manager import BatteryManager

logger = structlog.get_logger(__name__)

# Durée Passive (UPS) couvrant la plage HC 22h00–06h00 (8 h).
NIGHT_HC_PRECHARGE_DURATION_SEC = 8 * 3600

# Puissance de charge par défaut si `tempo_precharge_power` absent (W, valeur API négative).
DEFAULT_TEMPO_CHARGE_WATTS = -1000


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

    @staticmethod
    def _charge_watts_from_config_value(raw: str | int | None) -> int:
        """Convertit `tempo_precharge_power` (positif = W de charge côté UI) en W API.

        L'API Marstek attend une puissance négative pour la charge (Manual/Passive).

        Args:
            raw: Valeur lue en base (ex. \"2000\") ou None

        Returns:
            Puissance en watts, toujours négative ou zéro
        """
        if raw is None:
            return DEFAULT_TEMPO_CHARGE_WATTS
        try:
            v = int(raw)
        except (TypeError, ValueError):
            return DEFAULT_TEMPO_CHARGE_WATTS
        if v == 0:
            return DEFAULT_TEMPO_CHARGE_WATTS
        return -abs(v)

    async def switch_to_auto_mode(
        self, db: AsyncSession, max_retries: int = 3
    ) -> dict[int, bool]:
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
            logger.info(
                "retrying_failed_batteries", retry=retry, failed_batteries=failed
            )
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

    async def switch_to_manual_night(
        self, db: AsyncSession, max_retries: int = 3
    ) -> dict[int, bool]:
        """Vérifie Tempo à 22h et lance uniquement la précharge rouge.

        Si demain est rouge Tempo, charge les batteries en mode Passive / UPS.
        Sinon, conserve le mode Auto/autoconsommation sans appel batterie.

        Args:
            db: Database session
            max_retries: Nombre max de tentatives sur échec

        Returns:
            Dictionnaire {battery_id: success}; vide si aucune action batterie.
        """
        import asyncio

        from sqlalchemy import select

        from app.core.tempo_service import TempoService
        from app.models import AppConfig

        # Vérifier si demain est un jour rouge Tempo
        is_red_tomorrow = False
        charge_power_watts = DEFAULT_TEMPO_CHARGE_WATTS

        try:
            async with TempoService() as tempo_service:
                # API fraîche : évite un cache Redis « demain rouge » alors que le calendrier a changé.
                is_red_tomorrow = await tempo_service.should_activate_precharge(
                    force_refresh=True
                )

            if is_red_tomorrow:
                stmt = select(AppConfig).where(AppConfig.key == "tempo_precharge_power")
                result = await db.execute(stmt)
                config = result.scalar_one_or_none()
                charge_power_watts = self._charge_watts_from_config_value(
                    config.value if config else None
                )
        except Exception as e:
            logger.warning("tempo_check_failed_in_manual_night", error=str(e))

        if is_red_tomorrow:
            logger.info(
                "switching_to_passive_precharge_red_tomorrow",
                max_retries=max_retries,
                reason="jour_rouge_demain",
                power_watts=charge_power_watts,
                cd_time_sec=NIGHT_HC_PRECHARGE_DURATION_SEC,
            )

            # Mode Passive (affichage type « UPS » sur l'app) : charge limitée en W, durée HC.
            mode_config = {
                "mode": "passive",
                "power": charge_power_watts,
                "cd_time": NIGHT_HC_PRECHARGE_DURATION_SEC,
            }

            results = await self.battery_manager.set_mode_all(db, mode_config)

            for retry in range(1, max_retries):
                failed = [bid for bid, success in results.items() if not success]
                if not failed:
                    break
                logger.info(
                    "retrying_passive_precharge",
                    retry=retry,
                    failed_batteries=failed,
                )
                await asyncio.sleep(60.0)
                retry_results = await self.battery_manager.set_mode_all(db, mode_config)
                for bid, success in retry_results.items():
                    if success:
                        results[bid] = True

            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)
            logger.info(
                "passive_precharge_result",
                success_count=success_count,
                total_count=total_count,
                power_watts=charge_power_watts,
            )

            if success_count < total_count:
                failed_batteries = [bid for bid, success in results.items() if not success]
                if self.notification_service:
                    await self._send_notification(
                        "⚠️ Précharge Tempo - Échec partiel",
                        f"{success_count}/{total_count} batteries en mode Passive / UPS "
                        f"(charge {charge_power_watts} W). Batteries en échec: "
                        f"{failed_batteries}",
                        level="warning",
                    )
            elif self.notification_service:
                await self._send_notification(
                    "⚡ Précharge Tempo (Passive / UPS)",
                    f"Toutes les batteries ({total_count}) sont en mode Passive / UPS "
                    f"pour la charge de nuit ({charge_power_watts} W, 22h-6h).",
                    level="info",
                )

            return results

        logger.info(
            "tempo_night_check_auto_preserved",
            max_retries=max_retries,
            reason="no_red_tempo_tomorrow",
        )

        if self.notification_service:
            await self._send_notification(
                "🌙 Auto conservé cette nuit",
                "Demain n'est pas rouge Tempo : aucune bascule Manual/UPS "
                "envoyée, les batteries restent en autoconsommation / Auto.",
                level="info",
            )

        return {}

    async def activate_tempo_precharge(
        self, db: AsyncSession, target_soc: int = 95, power_limit: int = -1000
    ) -> dict[int, bool]:
        """Active une charge réseau (appel manuel / API), en mode Passive (type UPS).

        Le job planifié à 12h30 ne doit plus appeler cette méthode (heures pleines) :
        la précharge automatique a lieu à 22h via `switch_to_manual_night`.

        Args:
            db: Database session
            target_soc: SOC cible (information notifications / logs)
            power_limit: Puissance de charge : valeur négative en W, ou positif (abs pris)

        Returns:
            Dictionnaire {battery_id: success} indiquant le succès pour chaque batterie
        """
        import asyncio

        power_watts = (
            power_limit if power_limit <= 0 else self._charge_watts_from_config_value(
                power_limit
            )
        )

        logger.info(
            "activating_tempo_precharge_passive",
            target_soc=target_soc,
            power_watts=power_watts,
            cd_time_sec=NIGHT_HC_PRECHARGE_DURATION_SEC,
        )

        mode_config = {
            "mode": "passive",
            "power": power_watts,
            "cd_time": NIGHT_HC_PRECHARGE_DURATION_SEC,
        }

        results = await self.battery_manager.set_mode_all(db, mode_config)

        for retry in range(1, 3):
            failed = [bid for bid, success in results.items() if not success]
            if not failed:
                break
            logger.info("retrying_tempo_precharge", retry=retry, failed_batteries=failed)
            await asyncio.sleep(60.0)
            retry_results = await self.battery_manager.set_mode_all(db, mode_config)
            for bid, success in retry_results.items():
                if success:
                    results[bid] = True

        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)

        logger.info(
            "tempo_precharge_result",
            success_count=success_count,
            total_count=total_count,
            power_watts=power_watts,
        )

        if self.notification_service:
            await self._send_notification(
                "⚡ Précharge Tempo (Passive / UPS)",
                f"Les batteries ({success_count}/{total_count}) sont en mode Passive "
                f"(cible SOC indicatif {target_soc} %, puissance {power_watts} W, "
                f"durée {NIGHT_HC_PRECHARGE_DURATION_SEC // 3600} h).",
                level="info",
            )

        return results

    async def get_recommended_mode(
        self, db: AsyncSession, current_time: datetime | None = None
    ) -> str:
        """Détermine le mode optimal selon le contexte.

        Prend en compte :
        - L'heure actuelle (Auto conservé jour et nuit hors précharge Tempo)
        - Les jours Tempo (précharge si jour rouge à venir)
        - L'état des batteries

        Args:
            db: Database session
            current_time: Heure actuelle (default: maintenant)

        Returns:
            Mode recommandé: "auto" ou "tempo_precharge"
        """
        if current_time is None:
            current_time = datetime.now()

        current_hour = current_time.hour

        # Hors précharge Tempo rouge, on conserve Auto / autoconsommation.
        recommended = "auto"

        logger.debug(
            "mode_recommendation",
            current_hour=current_hour,
            recommended_mode=recommended,
        )

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
            elif level == "warning" and hasattr(self.notification_service, "send_warning"):
                await self.notification_service.send_warning(title, message)
            elif level == "error" and hasattr(self.notification_service, "send_error"):
                await self.notification_service.send_error(title, message)
            elif hasattr(self.notification_service, "send_info"):
                await self.notification_service.send_info(title, message)
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
