"""Battery manager for orchestrating multiple Marstek batteries."""

import asyncio
from collections.abc import Awaitable
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.marstek_client import MarstekUDPClient
from app.core.marstek_modbus_client import MarstekModbusClient
from app.models import Battery, BatteryStatusLog

logger = structlog.get_logger(__name__)

# Cache en mémoire pour les status des batteries (évite les requêtes répétées)
_battery_status_cache: dict[int, dict] = {}
_battery_cache_timestamps: dict[int, datetime] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes de cache

# Historique de connectivité pour détecter les réinitialisations API
_battery_connectivity_history: dict[int, list[dict]] = {}
MAX_CONNECTIVITY_HISTORY = 100  # Garder les 100 derniers états


class BatteryManager:
    """Gère les 3 batteries Marstek en parallèle.

    Coordonne les opérations sur toutes les batteries simultanément
    avec gestion d'erreurs individuelles et logging structuré.
    """

    def __init__(
        self,
        client: MarstekUDPClient | None = None,
        modbus_client: MarstekModbusClient | None = None,
    ) -> None:
        """Initialize battery manager.

        Args:
            client: Marstek UDP client (creates new one if None)
            modbus_client: Read-only Modbus client (creates new one if None)
        """
        self.client = client or MarstekUDPClient(
            timeout=20.0, max_retries=3, retry_backoff=1.0
        )
        self.modbus_client = modbus_client or MarstekModbusClient()
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

    async def get_all_status(self, db: AsyncSession) -> dict[int, dict[str, Any]]:
        """Retourne le status depuis le cache (mis à jour par le scheduler).

        Args:
            db: Database session

        Returns:
            Dictionnaire {battery_id: {status, es_status, mode_info}}
        """
        global _battery_status_cache, _battery_cache_timestamps

        # Récupérer toutes les batteries actives
        stmt = select(Battery).where(Battery.is_active)
        result = await db.execute(stmt)
        batteries = result.scalars().all()

        if not batteries:
            logger.warning("no_active_batteries")
            return {}

        status_dict: dict[int, dict[str, Any]] = {}

        for battery in batteries:
            if battery.id in _battery_status_cache:
                cache_time = _battery_cache_timestamps.get(battery.id, datetime.min)
                cache_age = (datetime.utcnow() - cache_time).total_seconds()
                status_dict[battery.id] = _battery_status_cache[battery.id]
                status_dict[battery.id]["cache_age_seconds"] = int(cache_age)
            else:
                status_dict[battery.id] = {
                    "error": "No cached data - wait for scheduler"
                }

        return status_dict

    def _track_connectivity(
        self,
        battery_id: int,
        battery_name: str,
        ip: str,
        port: int,
        success: bool,
        error_type: str | None = None,
        error_msg: str | None = None,
    ) -> None:
        """Enregistre l'historique de connectivité pour détecter les réinitialisations API.

        Args:
            battery_id: ID de la batterie
            battery_name: Nom de la batterie
            ip: Adresse IP
            port: Port UDP
            success: True si la communication a réussi
            error_type: Type d'erreur (timeout, connection_refused, etc.)
            error_msg: Message d'erreur détaillé
        """
        global _battery_connectivity_history

        if battery_id not in _battery_connectivity_history:
            _battery_connectivity_history[battery_id] = []

        history = _battery_connectivity_history[battery_id]

        # Récupérer l'état précédent
        was_connected = False
        consecutive_failures = 0
        if history:
            was_connected = history[-1].get("success", False)
            # Compter les échecs consécutifs
            for entry in reversed(history):
                if not entry.get("success", False):
                    consecutive_failures += 1
                else:
                    break

        # Enregistrer le nouvel état
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "success": success,
            "ip": ip,
            "port": port,
            "error_type": error_type,
            "error_msg": error_msg,
        }
        history.append(entry)

        # Limiter la taille de l'historique
        if len(history) > MAX_CONNECTIVITY_HISTORY:
            history.pop(0)

        # DÉTECTION DE PERTE DE CONNEXION (probable reset API)
        if was_connected and not success:
            logger.warning(
                "BATTERY_CONNECTION_LOST",
                battery_id=battery_id,
                battery_name=battery_name,
                ip=ip,
                port=port,
                error_type=error_type,
                error_msg=error_msg,
                message="⚠️ La batterie ne répond plus - POSSIBLE RESET API/PORT",
                action_required="Vérifier dans l'app Marstek si l'API est toujours activée",
            )

        # DÉTECTION DE RECONNEXION APRÈS PERTE
        if not was_connected and success and consecutive_failures > 0:
            logger.info(
                "BATTERY_CONNECTION_RESTORED",
                battery_id=battery_id,
                battery_name=battery_name,
                ip=ip,
                port=port,
                previous_failures=consecutive_failures,
                message="✅ La batterie répond à nouveau",
            )

        # ALERTE APRÈS PLUSIEURS ÉCHECS CONSÉCUTIFS
        if not success:
            new_consecutive = consecutive_failures + 1
            if new_consecutive == 3:
                logger.error(
                    "BATTERY_MULTIPLE_FAILURES",
                    battery_id=battery_id,
                    battery_name=battery_name,
                    ip=ip,
                    port=port,
                    consecutive_failures=new_consecutive,
                    message="🚨 3 échecs consécutifs - Vérifier l'état de la batterie",
                    possible_causes=[
                        "API désactivée sur la batterie",
                        "Port UDP changé",
                        "Batterie hors ligne",
                        "Problème réseau",
                        "Firmware v153 bug connu",
                    ],
                )
            elif new_consecutive == 10:
                logger.critical(
                    "BATTERY_OFFLINE",
                    battery_id=battery_id,
                    battery_name=battery_name,
                    ip=ip,
                    port=port,
                    consecutive_failures=new_consecutive,
                    message="🔴 Batterie considérée HORS LIGNE après 10 échecs",
                )

    async def refresh_single_battery(self, battery: Battery) -> dict[str, Any]:
        """Rafraîchit le cache pour une seule batterie (appelé par scheduler).

        Args:
            battery: Battery model instance

        Returns:
            Status de la batterie
        """
        global _battery_status_cache, _battery_cache_timestamps

        try:
            result = await self._get_single_battery_status(battery)

            # Tracker la connectivité
            success = result.get("bat_status") is not None
            error_type = None
            error_msg = None
            if not success:
                error_msg = result.get("error", "Unknown error")
                if "timeout" in error_msg.lower():
                    error_type = "timeout"
                elif "connection" in error_msg.lower():
                    error_type = "connection_error"
                else:
                    error_type = "unknown"

            self._track_connectivity(
                battery_id=battery.id,
                battery_name=battery.name,
                ip=battery.ip_address,
                port=battery.udp_port,
                success=success,
                error_type=error_type,
                error_msg=error_msg,
            )

            # Ne mettre à jour le cache que si on a des données valides (bat_status non null)
            if result.get("bat_status") is not None:
                _battery_status_cache[battery.id] = result
                _battery_cache_timestamps[battery.id] = datetime.utcnow()
                logger.info(
                    "battery_cache_updated", battery_id=battery.id, success=True
                )
            else:
                # Données partielles : garder l'ancien cache si disponible
                if battery.id in _battery_status_cache and _battery_status_cache[
                    battery.id
                ].get("bat_status"):
                    cache_age = _battery_cache_timestamps.get(battery.id, datetime.min)
                    logger.warning(
                        "battery_refresh_partial_keeping_old",
                        battery_id=battery.id,
                        old_cache_age_seconds=int(
                            (datetime.utcnow() - cache_age).total_seconds()
                        ),
                    )
                    # Marquer le cache comme stale mais garder les données
                    _battery_status_cache[battery.id]["stale"] = True
                    return _battery_status_cache[battery.id]
                else:
                    # Pas de cache précédent valide - stocker l'erreur
                    _battery_status_cache[battery.id] = result
                    _battery_cache_timestamps[battery.id] = datetime.utcnow()
                    logger.warning("battery_cache_error_stored", battery_id=battery.id)

            return result
        except Exception as e:
            # Tracker l'exception comme échec de connectivité
            self._track_connectivity(
                battery_id=battery.id,
                battery_name=battery.name,
                ip=battery.ip_address,
                port=battery.udp_port,
                success=False,
                error_type="exception",
                error_msg=str(e),
            )
            logger.error("battery_refresh_failed", battery_id=battery.id, error=str(e))
            return {"error": str(e)}

    async def _get_single_battery_status(self, battery: Battery) -> dict[str, Any]:
        """Récupère le status d'une seule batterie.

        Args:
            battery: Battery model instance

        Returns:
            Dict avec status, es_status, mode_info
        """
        try:
            # Récupérer UNIQUEMENT Bat.GetStatus (plus fiable sur VenusE)
            # ES.GetStatus et ES.GetMode timeout souvent - on les skip
            bat_status: Any = None
            es_status: Any = None
            mode_info: Any = None

            try:
                bat_status = await self.client.get_battery_status(
                    battery.ip_address, battery.udp_port
                )
            except Exception as e:
                bat_status = e

            # Attendre 30 secondes avant ES.GetStatus (rate limiting VenusE)
            await asyncio.sleep(45.0)  # 30s requis pour éviter rate limiting

            try:
                es_status = await self.client.get_es_status(
                    battery.ip_address, battery.udp_port
                )
            except Exception as e:
                es_status = e

            result: dict[str, Any] = {}
            data_incomplete = False

            if isinstance(bat_status, Exception):
                logger.warning(
                    "battery_status_error",
                    battery_id=battery.id,
                    error=str(bat_status),
                )
                result["bat_status"] = None
                data_incomplete = True
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

            # Récupérer le mode avec délai supplémentaire
            await asyncio.sleep(45.0)  # 30s requis pour éviter rate limiting

            try:
                mode_info = await self.client.get_current_mode(
                    battery.ip_address, battery.udp_port
                )
                result["mode_info"] = mode_info.model_dump()
            except Exception as e:
                logger.warning("mode_info_error", battery_id=battery.id, error=str(e))
                result["mode_info"] = None

            # Marquer comme incomplet si Bat.GetStatus a échoué
            if data_incomplete:
                result["error"] = "Données partielles - Bat.GetStatus timeout"

            return result

        except Exception as e:
            logger.error(
                "battery_status_fetch_exception",
                battery_id=battery.id,
                error=str(e),
            )
            raise

    async def get_battery_diagnostics(self, battery: Battery) -> dict[str, Any]:
        """Build a read-only diagnostic snapshot for one battery.

        Args:
            battery: Battery model instance

        Returns:
            Diagnostic data with per-source errors.
        """
        errors: dict[str, str] = {}
        bat_status = await self._safe_read_source(
            "bat_status",
            errors,
            self.client.get_battery_status(battery.ip_address, battery.udp_port),
        )
        es_status = await self._safe_read_source(
            "es_status",
            errors,
            self.client.get_es_status(battery.ip_address, battery.udp_port),
        )
        mode_info = await self._safe_read_source(
            "mode_info",
            errors,
            self.client.get_current_mode(battery.ip_address, battery.udp_port),
        )
        em_status = await self._safe_read_source(
            "em_status",
            errors,
            self.client.get_em_status(battery.ip_address, battery.udp_port),
        )
        pv_status = await self._safe_read_source(
            "pv_status",
            errors,
            self.client.get_pv_status(battery.ip_address, battery.udp_port),
        )
        modbus_status = await self._safe_read_source(
            "modbus",
            errors,
            self.modbus_client.read_diagnostics(battery.ip_address),
        )

        bat_data = self._model_to_dict(bat_status)
        es_data = self._model_to_dict(es_status)
        mode_data = self._model_to_dict(mode_info)
        em_data = self._model_to_dict(em_status)
        pv_data = self._model_to_dict(pv_status)
        modbus_data = self._model_to_dict(modbus_status)

        if modbus_data:
            modbus_errors = modbus_data.pop("errors", {})
            for field_name, error in modbus_errors.items():
                errors[f"modbus.{field_name}"] = error

        return {
            "battery_id": battery.id,
            "battery_name": battery.name,
            "timestamp": datetime.utcnow(),
            "ip_address": battery.ip_address,
            "udp_port": battery.udp_port,
            "soc": self._first_present(
                bat_data.get("soc"), es_data.get("bat_soc"), mode_data.get("bat_soc")
            ),
            "charg_flag": bat_data.get("charg_flag"),
            "dischrg_flag": bat_data.get("dischrg_flag"),
            "mode": mode_data.get("mode"),
            "bat_power": es_data.get("bat_power"),
            "pv_power": self._first_present(
                pv_data.get("pv_power"), es_data.get("pv_power")
            ),
            "pv_voltage": pv_data.get("pv_voltage"),
            "pv_current": pv_data.get("pv_current"),
            "pv_state": pv_data.get("pv_state"),
            "ongrid_power": self._first_present(
                mode_data.get("ongrid_power"), es_data.get("ongrid_power")
            ),
            "offgrid_power": self._first_present(
                mode_data.get("offgrid_power"), es_data.get("offgrid_power")
            ),
            "ct_state": self._first_present(
                em_data.get("ct_state"), mode_data.get("ct_state")
            ),
            "a_power": self._first_present(
                em_data.get("a_power"), mode_data.get("a_power")
            ),
            "b_power": self._first_present(
                em_data.get("b_power"), mode_data.get("b_power")
            ),
            "c_power": self._first_present(
                em_data.get("c_power"), mode_data.get("c_power")
            ),
            "total_power": self._first_present(
                em_data.get("total_power"), mode_data.get("total_power")
            ),
            "input_energy": self._first_present(
                em_data.get("input_energy"), mode_data.get("input_energy")
            ),
            "output_energy": self._first_present(
                em_data.get("output_energy"), mode_data.get("output_energy")
            ),
            "modbus": modbus_data or None,
            "errors": errors,
        }

    async def _safe_read_source(
        self,
        source: str,
        errors: dict[str, str],
        awaitable: Awaitable[Any],
    ) -> Any:
        """Read one diagnostic source without failing the whole snapshot."""
        try:
            return await awaitable
        except Exception as exc:
            errors[source] = str(exc)
            logger.warning("diagnostic_source_failed", source=source, error=str(exc))
        return None

    def _model_to_dict(self, value: Any) -> dict[str, Any]:
        """Convert Pydantic models or dictionaries to a plain dictionary."""
        if value is None:
            return {}
        if hasattr(value, "model_dump"):
            dumped = value.model_dump()
            return dumped if isinstance(dumped, dict) else {}
        if isinstance(value, dict):
            return dict(value)
        return {}

    def _first_present(self, *values: Any) -> Any:
        """Return the first value that is not None."""
        return next((value for value in values if value is not None), None)

    async def set_mode_all(
        self, db: AsyncSession, mode_config: dict[str, Any]
    ) -> dict[int, bool]:
        """Applique un mode à toutes les batteries avec gestion d'erreurs individuelles.

        Args:
            db: Database session
            mode_config: Configuration du mode à appliquer
                - Pour Auto: {"mode": "auto"}
                - Pour Manual: {"mode": "manual", "config": ManualConfig dict}
                - Pour Passive (charge/décharge directe, affichage type UPS) :
                  {"mode": "passive", "power": int, "cd_time": int}

        Returns:
            Dictionnaire {battery_id: success} indiquant le succès pour chaque batterie
        """
        # Récupérer toutes les batteries actives
        stmt = select(Battery).where(Battery.is_active)
        db_result = await db.execute(stmt)
        batteries = db_result.scalars().all()

        if not batteries:
            logger.warning("no_active_batteries_for_mode_change")
            return {}

        mode = mode_config.get("mode", "").lower()
        logger.info("setting_mode_all", mode=mode, battery_count=len(batteries))

        # Appliquer le mode SÉQUENTIELLEMENT avec délais pour éviter rate limiting
        success_dict: dict[int, bool] = {}

        for i, battery in enumerate(batteries):
            # Délai entre batteries (sauf la première)
            if i > 0:
                logger.info("waiting_between_batteries", delay_seconds=30)
                await asyncio.sleep(30.0)

            try:
                if mode == "auto":
                    result = await self.client.set_mode_auto(
                        battery.ip_address, battery.udp_port
                    )
                elif mode == "manual":
                    manual_config = mode_config.get("config")
                    if not manual_config:
                        logger.error("manual_config_missing", battery_id=battery.id)
                        result = False
                    else:
                        from app.models.marstek_api import ManualConfig

                        config = ManualConfig(**manual_config)
                        result = await self.client.set_mode_manual(
                            battery.ip_address, battery.udp_port, config
                        )
                elif mode == "passive":
                    power = mode_config.get("power")
                    cd_time = mode_config.get("cd_time")
                    if power is None or cd_time is None:
                        logger.error(
                            "passive_config_missing",
                            battery_id=battery.id,
                            power=power,
                            cd_time=cd_time,
                        )
                        result = False
                    else:
                        result = await self.client.set_mode_passive(
                            battery.ip_address,
                            battery.udp_port,
                            int(power),
                            int(cd_time),
                        )
                else:
                    logger.error("unknown_mode", mode=mode, battery_id=battery.id)
                    result = False

                success_dict[battery.id] = result
                logger.info(
                    "mode_set_success",
                    battery_id=battery.id,
                    mode=mode,
                    success=result,
                )
            except Exception as e:
                logger.error(
                    "mode_set_failed",
                    battery_id=battery.id,
                    mode=mode,
                    error=str(e),
                )
                success_dict[battery.id] = False

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
        stmt = select(Battery).where(Battery.is_active)
        result = await db.execute(stmt)
        {b.id: b for b in result.scalars().all()}

        # Créer les logs
        logs_created = 0

        for battery_id, status_data in status_dict.items():
            if "error" in status_data:
                continue  # Skip les batteries en erreur

            try:
                bat_status = status_data.get("bat_status")
                es_status = status_data.get("es_status")
                mode_info = status_data.get("mode_info")

                if not bat_status:
                    continue  # Pas de données de batterie

                # Créer le log (gérer es_status et mode_info null)
                es = es_status or {}
                mode = mode_info or {}
                log = BatteryStatusLog(
                    battery_id=battery_id,
                    timestamp=datetime.utcnow(),
                    soc=bat_status.get("soc", 0),
                    bat_power=es.get("bat_power"),
                    pv_power=es.get("pv_power"),
                    ongrid_power=es.get("ongrid_power"),
                    offgrid_power=es.get("offgrid_power"),
                    mode=mode.get("mode", "Unknown"),
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
