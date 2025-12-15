"""Client UDP pour communication avec batteries Marstek Venus-E.

Utilise le protocole JSON-RPC over UDP selon MarstekDeviceOpenApi.pdf.
"""

import asyncio
import json
import socket
import time
from dataclasses import dataclass
from typing import Any

from marstek.core.config import BatteryConfig
from marstek.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class BatteryStatus:
    """Status d'une batterie Marstek."""

    battery_id: str
    voltage: float | None = None
    current: float | None = None
    power: float | None = None
    soc: float | None = None  # State of Charge (0-100)
    temperature: float | None = None
    mode: str | None = None  # Auto, Manual, AI, Passive
    error_code: int | None = None
    timestamp: float | None = None
    # Champs additionnels de l'API Marstek
    bat_capacity: float | None = None  # Capacité restante [Wh]
    rated_capacity: float | None = None  # Capacité nominale [Wh]
    charg_flag: bool | None = None  # Permission de charge
    dischrg_flag: bool | None = None  # Permission de décharge
    bat_power: float | None = None  # Puissance batterie [W]
    ongrid_power: float | None = None  # Puissance réseau [W]
    offgrid_power: float | None = None  # Puissance hors réseau [W]


class MarstekClient:
    """Client UDP pour communication avec batteries Marstek.

    Gère la communication UDP avec gestion robuste des erreurs réseau.
    """

    def __init__(
        self, battery_config: BatteryConfig, timeout: float = 5.0, instance_id: int = 0
    ) -> None:
        """Initialize Marstek client.

        Args:
            battery_config: Configuration de la batterie
            timeout: Timeout pour les requêtes UDP (secondes)
            instance_id: ID d'instance du device (default: 0)
        """
        self.config = battery_config
        self.timeout = timeout
        self.instance_id = instance_id
        self._socket: socket.socket | None = None
        self._request_id = 0

    async def connect(self) -> None:
        """Établit la connexion UDP (no-op pour UDP, mais garde l'interface)."""
        # UDP est connectionless, mais on peut initialiser le socket
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.settimeout(self.timeout)
        logger.info("marstek_client_initialized", battery_id=self.config.id, ip=self.config.ip)

    async def disconnect(self) -> None:
        """Ferme la connexion UDP."""
        if self._socket:
            self._socket.close()
            self._socket = None
            logger.info("marstek_client_disconnected", battery_id=self.config.id)

    async def read_status(self, retries: int = 3) -> BatteryStatus:
        """Lit le status complet de la batterie.

        Combine Bat.GetStatus, ES.GetStatus et ES.GetMode pour obtenir
        toutes les informations nécessaires.

        Args:
            retries: Nombre de tentatives en cas d'erreur

        Returns:
            Status de la batterie

        Raises:
            ConnectionError: Si la connexion échoue après tous les retries
            TimeoutError: Si la requête timeout
        """
        if not self._socket:
            await self.connect()

        # Récupérer les informations depuis plusieurs endpoints
        bat_status = await self._call_method("Bat.GetStatus", {"id": self.instance_id}, retries)
        es_status = await self._call_method("ES.GetStatus", {"id": self.instance_id}, retries)
        es_mode = await self._call_method("ES.GetMode", {"id": self.instance_id}, retries)

        # Combiner les résultats
        bat_result = bat_status.get("result", {}) if bat_status else {}
        es_result = es_status.get("result", {}) if es_status else {}
        mode_result = es_mode.get("result", {}) if es_mode else {}

        # Extraire le mode (peut être un nombre ou une string selon la doc)
        mode = mode_result.get("mode")
        if isinstance(mode, int):
            mode_map = {0: "Auto", 1: "AI", 2: "Manual", 3: "Passive"}
            mode = mode_map.get(mode, "Unknown")
        elif mode is None:
            mode = "Unknown"

        status = BatteryStatus(
            battery_id=self.config.id,
            soc=bat_result.get("soc") or mode_result.get("bat_soc"),
            temperature=bat_result.get("bat_temp"),
            bat_capacity=bat_result.get("bat_capacity"),
            rated_capacity=bat_result.get("rated_capacity"),
            charg_flag=bat_result.get("charg_flag"),
            dischrg_flag=bat_result.get("dischrg_flag"),
            bat_power=es_result.get("bat_power"),
            ongrid_power=es_result.get("ongrid_power") or mode_result.get("ongrid_power"),
            offgrid_power=es_result.get("offgrid_power") or mode_result.get("offgrid_power"),
            power=es_result.get("bat_power"),  # Utiliser bat_power comme power principal
            mode=mode,
            timestamp=time.time(),
        )

        logger.debug(
            "battery_status_read",
            battery_id=self.config.id,
            soc=status.soc,
            mode=status.mode,
        )

        return status

    async def set_mode(self, mode: str, retries: int = 3) -> bool:
        """Change le mode de fonctionnement de la batterie.

        Args:
            mode: Mode à définir ("Auto", "Manual", "AI", "Passive")
            retries: Nombre de tentatives en cas d'erreur

        Returns:
            True si succès, False sinon

        Raises:
            ValueError: Si le mode est invalide
        """
        valid_modes = ["Auto", "Manual", "AI", "Passive"]
        mode_normalized = mode.capitalize()
        if mode_normalized not in valid_modes:
            raise ValueError(f"Invalid mode: {mode}. Must be one of {valid_modes}")

        if not self._socket:
            await self.connect()

        # Construire la configuration selon le mode
        config: dict[str, Any] = {"mode": mode_normalized}

        if mode_normalized == "Auto":
            config["auto_cfg"] = {"enable": 1}
        elif mode_normalized == "AI":
            config["ai_cfg"] = {"enable": 1}
        elif mode_normalized == "Manual":
            # Mode Manual nécessite une configuration de période
            # Pour l'instant, on utilise une configuration par défaut
            # L'utilisateur peut étendre cette méthode pour personnaliser
            config["manual_cfg"] = {
                "time_num": 0,
                "start_time": "06:00",
                "end_time": "22:00",
                "week_set": 127,  # Tous les jours
                "power": 0,  # Pas de limite de puissance
                "enable": 1,
            }
        elif mode_normalized == "Passive":
            config["passive_cfg"] = {
                "power": 0,
                "cd_time": 0,
            }

        params = {"id": self.instance_id, "config": config}

        response = await self._call_method("ES.SetMode", params, retries)

        if response and "result" in response:
            result = response["result"]
            success = result.get("set_result", False)

            if success:
                logger.info(
                    "battery_mode_changed",
                    battery_id=self.config.id,
                    mode=mode_normalized,
                )
                return True

        logger.error(
            "marstek_set_mode_failed",
            battery_id=self.config.id,
            mode=mode_normalized,
        )
        return False

    async def _call_method(
        self, method: str, params: dict[str, Any], retries: int = 3
    ) -> dict[str, Any] | None:
        """Appelle une méthode JSON-RPC sur le device.

        Args:
            method: Nom de la méthode (ex: "Bat.GetStatus")
            params: Paramètres de la méthode
            retries: Nombre de tentatives en cas d'erreur

        Returns:
            Réponse JSON-RPC ou None en cas d'échec

        Raises:
            ConnectionError: Si la connexion échoue après tous les retries
            TimeoutError: Si la requête timeout
        """
        if not self._socket:
            await self.connect()

        self._request_id += 1
        request_id = self._request_id

        request = {
            "id": request_id,
            "method": method,
            "params": params,
        }

        request_json = json.dumps(request)
        request_bytes = request_json.encode("utf-8")

        last_error: Exception | None = None

        for attempt in range(1, retries + 1):
            try:
                # Envoyer la requête UDP
                self._socket.sendto(request_bytes, (self.config.ip, self.config.port))

                # Attendre la réponse
                response_data, addr = await asyncio.to_thread(
                    self._socket.recvfrom, 4096
                )

                # Parser la réponse JSON
                response_json = response_data.decode("utf-8")
                response = json.loads(response_json)

                # Vérifier que c'est la bonne réponse (même ID)
                if response.get("id") != request_id:
                    logger.warning(
                        "marstek_response_id_mismatch",
                        battery_id=self.config.id,
                        expected_id=request_id,
                        received_id=response.get("id"),
                    )
                    continue

                # Vérifier les erreurs JSON-RPC
                if "error" in response:
                    error = response["error"]
                    logger.error(
                        "marstek_jsonrpc_error",
                        battery_id=self.config.id,
                        method=method,
                        error_code=error.get("code"),
                        error_message=error.get("message"),
                    )
                    raise ConnectionError(
                        f"JSON-RPC error: {error.get('message')} (code: {error.get('code')})"
                    )

                logger.debug(
                    "marstek_method_success",
                    battery_id=self.config.id,
                    method=method,
                    attempt=attempt,
                )

                return response

            except json.JSONDecodeError as e:
                last_error = e
                logger.error(
                    "marstek_json_decode_error",
                    battery_id=self.config.id,
                    method=method,
                    attempt=attempt,
                    error=str(e),
                    response_preview=response_data[:100] if response_data else None,
                )
                if attempt < retries:
                    await asyncio.sleep(0.5 * attempt)

            except socket.timeout as e:
                last_error = e
                logger.warning(
                    "marstek_request_timeout",
                    battery_id=self.config.id,
                    method=method,
                    attempt=attempt,
                    retries=retries,
                )
                if attempt < retries:
                    await asyncio.sleep(0.5 * attempt)

            except OSError as e:
                last_error = e
                logger.error(
                    "marstek_network_error",
                    battery_id=self.config.id,
                    method=method,
                    attempt=attempt,
                    error=str(e),
                )
                if attempt < retries:
                    await asyncio.sleep(0.5 * attempt)

        # Tous les retries ont échoué
        logger.error(
            "marstek_method_failed",
            battery_id=self.config.id,
            method=method,
            retries=retries,
            error=str(last_error) if last_error else "Unknown error",
        )

        if isinstance(last_error, socket.timeout):
            raise TimeoutError(
                f"Timeout calling {method} on battery {self.config.id} after {retries} attempts"
            ) from last_error

        raise ConnectionError(
            f"Failed to call {method} on battery {self.config.id} after {retries} attempts"
        ) from last_error

    async def __aenter__(self) -> "MarstekClient":
        """Context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        await self.disconnect()

