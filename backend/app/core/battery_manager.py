"""Battery manager for orchestrating multiple Marstek batteries."""

import asyncio
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.marstek_client import MarstekUDPClient
from app.models import Battery, BatteryStatusLog
from app.models.marstek_api import BatteryStatus, DeviceInfo, ESStatus, ModeInfo

logger = structlog.get_logger(__name__)


class BatteryManager:
    """Gère les 3 batteries Marstek en parallèle.

    Coordonne les opérations sur toutes les batteries simultanément
    avec gestion d'erreurs individuelles et logging structuré.
    """

    def __init__(self, client: MarstekUDPClient | None = None) -> None:
        """Initialize battery manager.

        Args:
            client: Marstek UDP client (creates new one if None)
        """
        self.client = client or MarstekUDPClient(timeout=5.0, max_retries=3)
        self._batteries_cache: dict[int, Battery] = {}

    async def discover_and_register(self, db: AsyncSession) -> list[Battery]:
        """Découvre et enregistre les batteries en base de données.

        Utilise UDP broadcast pour découvrir les devices Marstek sur le réseau,
        puis les enregistre ou met à jour dans la base de données.

        Args:
            db: Database session

        Returns:
            Liste des batteries découvertes et enregistrées
        """
        logger.info("battery_discovery_started")

        # Découvrir les devices via broadcast
        devices = await self.client.broadcast_discover(timeout=5.0)

        if not devices:
            logger.warning("no_batteries_discovered")
            return []

        registered: list[Battery] = []

        for device_info in devices:
            try:
                # Chercher si la batterie existe déjà (par BLE MAC)
                stmt = select(Battery).where(Battery.ble_mac == device_info.ble_mac)
                result = await db.execute(stmt)
                existing_battery = result.scalar_one_or_none()

                if existing_battery:
                    # Mettre à jour les informations
                    existing_battery.ip_address = device_info.ip
                    existing_battery.wifi_mac = device_info.wifi_mac
                    existing_battery.last_seen_at = datetime.utcnow()
                    battery = existing_battery

                    logger.info(
                        "battery_updated",
                        battery_id=battery.id,
                        name=battery.name,
                        ip=device_info.ip,
                    )
                else:
                    # Créer une nouvelle batterie
                    battery = Battery(
                        name=f"Batt{len(registered) + 1}",
                        ip_address=device_info.ip,
                        udp_port=30000,  # Port par défaut, à configurer
                        ble_mac=device_info.ble_mac,
                        wifi_mac=device_info.wifi_mac,
                        is_active=True,
                        last_seen_at=datetime.utcnow(),
                    )
                    db.add(battery)
                    await db.flush()  # Pour obtenir l'ID

                    logger.info(
                        "battery_registered",
                        battery_id=battery.id,
                        name=battery.name,
                        ip=device_info.ip,
                        device=device_info.device,
                    )

                await db.commit()
                registered.append(battery)
                self._batteries_cache[battery.id] = battery

            except Exception as e:
                logger.error(
                    "battery_registration_failed",
                    device_ip=device_info.ip,
                    error=str(e),
                )
                await db.rollback()

        logger.info("battery_discovery_complete", batteries_found=len(registered))
        return registered

    async def get_all_status(
        self, db: AsyncSession
    ) -> dict[int, dict[str, Any]]:
        """Récupère l'état des 3 batteries en parallèle.

        Args:
            db: Database session

        Returns:
            Dictionnaire {battery_id: {status, es_status, mode_info}}
        """
        # Récupérer toutes les batteries actives
        stmt = select(Battery).where(Battery.is_active == True)
        result = await db.execute(stmt)
        batteries = result.scalars().all()

        if not batteries:
            logger.warning("no_active_batteries")
            return {}

        logger.info("fetching_battery_status", count=len(batteries))

        # Récupérer les status en parallèle
        tasks = []
        for battery in batteries:
            tasks.append(self._get_single_battery_status(battery))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Construire le dictionnaire de résultats
        status_dict: dict[int, dict[str, Any]] = {}

        for battery, result in zip(batteries, results):
            if isinstance(result, Exception):
                logger.error(
                    "battery_status_fetch_failed",
                    battery_id=battery.id,
                    error=str(result),
                )
                status_dict[battery.id] = {"error": str(result)}
            else:
                status_dict[battery.id] = result

        return status_dict

    async def _get_single_battery_status(
        self, battery: Battery
    ) -> dict[str, Any]:
        """Récupère le status d'une seule batterie.

        Args:
            battery: Battery model instance

        Returns:
            Dict avec status, es_status, mode_info
        """
        try:
            # Récupérer les informations en parallèle
            bat_status, es_status, mode_info = await asyncio.gather(
                self.client.get_battery_status(battery.ip_address, battery.udp_port),
                self.client.get_es_status(battery.ip_address, battery.udp_port),
                self.client.get_current_mode(battery.ip_address, battery.udp_port),
                return_exceptions=True,
            )

            result: dict[str, Any] = {}

            if isinstance(bat_status, Exception):
                logger.warning(
                    "battery_status_error",
                    battery_id=battery.id,
                    error=str(bat_status),
                )
                result["bat_status"] = None
            else:
                result["bat_status"] = bat_status.model_dump()

            if isinstance(es_status, Exception):
                logger.warning(
                    "es_status_error",
                    battery_id=battery.id,
                    error=str(es_status),
                )
                result["es_status"] = None
            else:
                result["es_status"] = es_status.model_dump()

            if isinstance(mode_info, Exception):
                logger.warning(
                    "mode_info_error",
                    battery_id=battery.id,
                    error=str(mode_info),
                )
                result["mode_info"] = None
            else:
                result["mode_info"] = mode_info.model_dump()

            return result

        except Exception as e:
            logger.error(
                "battery_status_fetch_exception",
                battery_id=battery.id,
                error=str(e),
            )
            raise

    async def set_mode_all(
        self, db: AsyncSession, mode_config: dict[str, Any]
    ) -> dict[int, bool]:
        """Applique un mode à toutes les batteries avec gestion d'erreurs individuelles.

        Args:
            db: Database session
            mode_config: Configuration du mode à appliquer
                - Pour Auto: {"mode": "auto"}
                - Pour Manual: {"mode": "manual", "config": ManualConfig}

        Returns:
            Dictionnaire {battery_id: success} indiquant le succès pour chaque batterie
        """
        # Récupérer toutes les batteries actives
        stmt = select(Battery).where(Battery.is_active == True)
        result = await db.execute(stmt)
        batteries = result.scalars().all()

        if not batteries:
            logger.warning("no_active_batteries_for_mode_change")
            return {}

        mode = mode_config.get("mode", "").lower()
        logger.info("setting_mode_all", mode=mode, battery_count=len(batteries))

        # Appliquer le mode en parallèle
        tasks = []
        for battery in batteries:
            if mode == "auto":
                tasks.append(self.client.set_mode_auto(battery.ip_address, battery.udp_port))
            elif mode == "manual":
                manual_config = mode_config.get("config")
                if not manual_config:
                    logger.error("manual_config_missing", battery_id=battery.id)

                    async def _fail() -> bool:
                        return False

                    tasks.append(_fail())
                else:
                    from app.models.marstek_api import ManualConfig

                    config = ManualConfig(**manual_config)
                    tasks.append(
                        self.client.set_mode_manual(
                            battery.ip_address, battery.udp_port, config
                        )
                    )
            else:
                logger.error("unknown_mode", mode=mode, battery_id=battery.id)

                async def _fail() -> bool:
                    return False

                tasks.append(_fail())

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Construire le dictionnaire de résultats
        success_dict: dict[int, bool] = {}

        for battery, result in zip(batteries, results):
            if isinstance(result, Exception):
                logger.error(
                    "mode_set_failed",
                    battery_id=battery.id,
                    mode=mode,
                    error=str(result),
                )
                success_dict[battery.id] = False
            else:
                success_dict[battery.id] = result
                logger.info(
                    "mode_set_success",
                    battery_id=battery.id,
                    mode=mode,
                    success=result,
                )

        return success_dict

    async def log_status_to_db(self, db: AsyncSession) -> None:
        """Sauvegarde l'état actuel de toutes les batteries en TimescaleDB.

        Args:
            db: Database session
        """
        logger.debug("logging_battery_status_to_db")

        # Récupérer les status de toutes les batteries
        status_dict = await self.get_all_status(db)

        # Récupérer les batteries pour avoir les IDs
        stmt = select(Battery).where(Battery.is_active == True)
        result = await db.execute(stmt)
        batteries = {b.id: b for b in result.scalars().all()}

        # Créer les logs
        logs_created = 0

        for battery_id, status_data in status_dict.items():
            if "error" in status_data:
                continue  # Skip les batteries en erreur

            try:
                bat_status = status_data.get("bat_status")
                es_status = status_data.get("es_status")
                mode_info = status_data.get("mode_info")

                if not bat_status or not es_status or not mode_info:
                    continue  # Données incomplètes

                # Créer le log
                log = BatteryStatusLog(
                    battery_id=battery_id,
                    timestamp=datetime.utcnow(),
                    soc=bat_status.get("soc", 0),
                    bat_power=es_status.get("bat_power"),
                    pv_power=es_status.get("pv_power"),
                    ongrid_power=es_status.get("ongrid_power"),
                    offgrid_power=es_status.get("offgrid_power"),
                    mode=mode_info.get("mode", "Unknown"),
                    bat_temp=bat_status.get("bat_temp"),
                    bat_capacity=bat_status.get("bat_capacity"),
                )

                db.add(log)
                logs_created += 1

            except Exception as e:
                logger.error(
                    "status_log_creation_failed",
                    battery_id=battery_id,
                    error=str(e),
                )

        try:
            await db.commit()
            logger.info("battery_status_logged", logs_created=logs_created)
        except Exception as e:
            logger.error("status_log_commit_failed", error=str(e))
            await db.rollback()

