"""Service d'intégration API Tempo RTE."""

from datetime import date, datetime
from typing import Any

import httpx
import structlog

from app.config import TempoSettings

logger = structlog.get_logger(__name__)


class TempoService:
    """Service pour interagir avec l'API Tempo RTE.

    Permet de récupérer les jours rouges/bleus/blancs pour optimisation.
    """

    def __init__(self, config: TempoSettings) -> None:
        """Initialize Tempo service.

        Args:
            config: Configuration Tempo RTE
        """
        self.config = config
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "TempoService":
        """Context manager entry."""
        if self.config.enabled:
            self._client = httpx.AsyncClient(timeout=self.config.timeout)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Ferme le client HTTP."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get_tempo_status(self, target_date: date | None = None) -> dict[str, Any]:
        """Récupère le statut Tempo pour une date.

        Args:
            target_date: Date cible (default: aujourd'hui)

        Returns:
            Dict avec les informations Tempo:
            - color: "RED", "BLUE", "WHITE"
            - date: date du statut
            - next_color: couleur du jour suivant (si disponible)

        Raises:
            httpx.HTTPError: Si la requête API échoue
        """
        if target_date is None:
            target_date = date.today()

        if not self.config.enabled:
            logger.warning("tempo_service_disabled")
            return {"color": "UNKNOWN", "date": target_date.isoformat()}

        if not self._client:
            self._client = httpx.AsyncClient(timeout=self.config.timeout)

        try:
            # API Tempo RTE - endpoint à vérifier selon la doc officielle
            url = f"{self.config.api_url}/tempo"
            params = {
                "date": target_date.isoformat(),
                "contract": self.config.contract_number,
            }

            response = await self._client.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            logger.info(
                "tempo_status_retrieved",
                date=target_date.isoformat(),
                color=data.get("color", "UNKNOWN"),
            )

            return {
                "color": data.get("color", "UNKNOWN"),  # RED, BLUE, WHITE
                "date": target_date.isoformat(),
                "next_color": data.get("next_color"),
            }

        except httpx.HTTPError as e:
            logger.error(
                "tempo_api_error",
                date=target_date.isoformat(),
                error=str(e),
            )
            raise

    async def is_red_day(self, target_date: date | None = None) -> bool:
        """Vérifie si c'est un jour rouge (tarif élevé).

        Args:
            target_date: Date cible (default: aujourd'hui)

        Returns:
            True si jour rouge, False sinon
        """
        try:
            status = await self.get_tempo_status(target_date)
            return status.get("color") == "RED"
        except Exception as e:
            logger.warning("tempo_check_failed", error=str(e), fallback=False)
            return False

    async def get_upcoming_red_days(self, days_ahead: int = 7) -> list[date]:
        """Récupère la liste des jours rouges à venir.

        Args:
            days_ahead: Nombre de jours à vérifier (max 7)

        Returns:
            Liste des dates de jours rouges
        """
        red_days: list[date] = []
        today = date.today()

        for i in range(min(days_ahead, 7)):
            check_date = date.fromordinal(today.toordinal() + i)
            if await self.is_red_day(check_date):
                red_days.append(check_date)

        logger.info("upcoming_red_days", count=len(red_days), days_ahead=days_ahead)
        return red_days

