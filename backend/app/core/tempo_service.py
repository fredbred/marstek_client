"""Service d'intégration API Tempo RTE avec cache Redis."""

from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any

import httpx
import redis.asyncio as aioredis
import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class TempoColor(str, Enum):
    """Couleurs Tempo RTE."""

    BLUE = "BLUE"  # Jour bleu (tarif bas)
    WHITE = "WHITE"  # Jour blanc (tarif moyen)
    RED = "RED"  # Jour rouge (tarif élevé)
    UNKNOWN = "UNKNOWN"  # Si API fail ou données indisponibles


class TempoCalendar:
    """Calendrier Tempo pour une date."""

    def __init__(self, date: date, color: TempoColor) -> None:
        """Initialize Tempo calendar entry.

        Args:
            date: Date du calendrier
            color: Couleur Tempo
        """
        self.date = date
        self.color = color

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {"date": self.date.isoformat(), "color": self.color.value}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TempoCalendar":
        """Create from dictionary."""
        return cls(
            date=date.fromisoformat(data["date"]),
            color=TempoColor(data["color"]),
        )


class TempoService:
    """Service pour interagir avec l'API Tempo RTE.

    Gère le cache Redis pour optimiser les appels API et réduire la latence.
    """

    BASE_URL = "https://www.api-couleur-tempo.fr/api"

    def __init__(self, redis_client: aioredis.Redis | None = None) -> None:
        """Initialize Tempo service.

        Args:
            redis_client: Client Redis async (créé si None)
        """
        self.config = settings.tempo
        self._redis = redis_client
        self._http_client: httpx.AsyncClient | None = None

    async def _get_redis(self) -> aioredis.Redis:
        """Get or create Redis client."""
        if self._redis is None:
<<<<<<< HEAD
            self._redis = aioredis.from_url(
                settings.redis.url, decode_responses=True
            )
=======
            self._redis = aioredis.from_url(settings.redis.url, decode_responses=True)
>>>>>>> origin/main
        return self._redis

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=self.config.timeout,
                headers={
                    "Accept": "application/json",
                },
            )
        return self._http_client

    def _get_cache_key(self, target_date: date) -> str:
        """Get Redis cache key for a date.

        Args:
            target_date: Date to cache

        Returns:
            Cache key string
        """
        return f"tempo:color:{target_date.isoformat()}"

    def _get_cache_ttl(self, target_date: date) -> int:
        """Get cache TTL in seconds.

        Args:
            target_date: Date to cache

        Returns:
            TTL in seconds
        """
        now = datetime.now()
<<<<<<< HEAD
        target_datetime = datetime.combine(target_date, datetime.min.time())
=======
        datetime.combine(target_date, datetime.min.time())
>>>>>>> origin/main

        if target_date == now.date():
            # Cache jusqu'à minuit
            midnight = (now + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            return int((midnight - now).total_seconds())
        elif target_date == (now.date() + timedelta(days=1)):
            # Cache J+1 jusqu'à 11h du lendemain
            tomorrow_11h = (now + timedelta(days=1)).replace(
                hour=11, minute=0, second=0, microsecond=0
            )
            if now.hour < 11:
                # Avant 11h, cache jusqu'à 11h aujourd'hui
                today_11h = now.replace(hour=11, minute=0, second=0, microsecond=0)
                return int((today_11h - now).total_seconds())
            else:
                # Après 11h, cache jusqu'à 11h demain
                return int((tomorrow_11h - now).total_seconds())
        else:
            # Dates futures, cache 24h
            return 86400

    async def get_tempo_color(self, target_date: date | None = None) -> TempoColor:
        """Récupère la couleur Tempo pour une date donnée.

        Utilise le cache Redis si disponible, sinon appelle l'API RTE.

        Args:
            target_date: Date cible (default: aujourd'hui)

        Returns:
            Couleur Tempo (BLUE, WHITE, RED, ou UNKNOWN en cas d'erreur)
        """
        if target_date is None:
            target_date = date.today()

        if not self.config.enabled:
            logger.debug("tempo_service_disabled", date=target_date.isoformat())
            return TempoColor.UNKNOWN

        # Vérifier le cache Redis
        try:
            redis = await self._get_redis()
            cache_key = self._get_cache_key(target_date)
            cached_color = await redis.get(cache_key)

            if cached_color:
                logger.debug(
                    "tempo_color_cache_hit",
                    date=target_date.isoformat(),
                    color=cached_color,
                )
                return TempoColor(cached_color)
        except Exception as e:
            logger.warning("tempo_cache_read_error", error=str(e))

        # Appel API
        try:
            http_client = await self._get_http_client()

            # Endpoint pour récupérer la couleur d'une date
            # Format attendu par l'API RTE
            # Documentation: https://data.rte-france.com/catalog/-/api/tempo
            # API alternative api-couleur-tempo.fr (gratuite, sans authentification)
            url = f"{self.BASE_URL}/joursTempo"
            response = await http_client.get(url)
            response.raise_for_status()
            data = response.json()
<<<<<<< HEAD
            
=======

>>>>>>> origin/main
            # Parser: {"dateJour": "YYYY-MM-DD", "codeJour": 1|2|3, "libCouleur": "Bleu|Blanc|Rouge"}
            date_str = target_date.isoformat()
            day_data = next((d for d in data if d.get("dateJour") == date_str), None)
            if day_data:
                lib_couleur = day_data.get("libCouleur", "").upper()
                if lib_couleur == "BLEU":
                    color_value = TempoColor.BLUE
                elif lib_couleur == "BLANC":
                    color_value = TempoColor.WHITE
                elif lib_couleur == "ROUGE":
                    color_value = TempoColor.RED
                else:
                    color_value = TempoColor.UNKNOWN
            else:
                logger.warning("tempo_date_not_found", date=date_str)
                color_value = TempoColor.UNKNOWN

            # Mettre en cache
            try:
                redis = await self._get_redis()
                cache_key = self._get_cache_key(target_date)
                ttl = self._get_cache_ttl(target_date)
                await redis.setex(cache_key, ttl, color_value.value)

                logger.debug(
                    "tempo_color_cached",
                    date=target_date.isoformat(),
                    color=color_value.value,
                    ttl=ttl,
                )
            except Exception as e:
                logger.warning("tempo_cache_write_error", error=str(e))

            logger.info(
                "tempo_color_retrieved",
                date=target_date.isoformat(),
                color=color_value.value,
            )

            return color_value

        except httpx.HTTPError as e:
            logger.error(
                "tempo_api_error",
                date=target_date.isoformat(),
                error=str(e),
<<<<<<< HEAD
                status_code=getattr(e.response, "status_code", None) if hasattr(e, "response") else None,
=======
                status_code=(
                    getattr(e.response, "status_code", None)
                    if hasattr(e, "response")
                    else None
                ),
>>>>>>> origin/main
            )
            return TempoColor.UNKNOWN
        except Exception as e:
            logger.error(
                "tempo_service_error",
                date=target_date.isoformat(),
                error=str(e),
                exc_info=True,
            )
            return TempoColor.UNKNOWN

<<<<<<< HEAD
    def _parse_api_response(self, data: dict[str, Any], target_date: date) -> TempoColor:
=======
    def _parse_api_response(
        self, data: dict[str, Any], target_date: date
    ) -> TempoColor:
>>>>>>> origin/main
        """Parse la réponse de l'API RTE.

        Args:
            data: Réponse JSON de l'API
            target_date: Date cible

        Returns:
            Couleur Tempo

        Raises:
            ValueError: Si le format de réponse est inattendu
        """
        # Format attendu : {"tempo_like_calendars": [{"date": "2024-01-15", "value": "RED"}]}
        # Ou : {"tempo_like_calendars": [{"date": "2024-01-15", "color": "RED"}]}
        calendars = data.get("tempo_like_calendars", [])

        if not calendars:
            logger.warning("tempo_api_empty_response", date=target_date.isoformat())
            return TempoColor.UNKNOWN

        # Chercher l'entrée pour la date cible
        date_str = target_date.isoformat()
        for entry in calendars:
            if entry.get("date") == date_str:
                color_str = entry.get("value") or entry.get("color", "").upper()
                try:
                    return TempoColor(color_str)
                except ValueError:
                    logger.warning(
                        "tempo_invalid_color",
                        date=date_str,
                        color=color_str,
                    )
                    return TempoColor.UNKNOWN

        logger.warning("tempo_date_not_found", date=date_str)
        return TempoColor.UNKNOWN

    async def get_tomorrow_color(self) -> TempoColor:
        """Récupère la couleur Tempo pour demain (J+1).

        La couleur J+1 est généralement disponible à partir de 11h.

        Returns:
            Couleur Tempo pour demain
        """
        tomorrow = date.today() + timedelta(days=1)
        return await self.get_tempo_color(tomorrow)

    async def should_activate_precharge(self) -> bool:
        """Détermine si la précharge doit être activée.

        Active la précharge si :
        - Demain est un jour rouge
        - Aujourd'hui n'est pas un jour rouge

        Returns:
            True si précharge nécessaire, False sinon
        """
        today = date.today()
<<<<<<< HEAD
        tomorrow = today + timedelta(days=1)
=======
        today + timedelta(days=1)
>>>>>>> origin/main

        today_color = await self.get_tempo_color(today)
        tomorrow_color = await self.get_tomorrow_color()

        should_activate = (
            tomorrow_color == TempoColor.RED and today_color != TempoColor.RED
        )

        logger.info(
            "tempo_precharge_check",
            today_color=today_color.value,
            tomorrow_color=tomorrow_color.value,
            should_activate=should_activate,
        )

        return should_activate

    async def get_remaining_days(self) -> dict[str, int]:
        """Récupère le nombre de jours restants par couleur dans la saison.

        Returns:
            Dictionnaire avec {"BLUE": X, "WHITE": Y, "RED": Z}
        """
        if not self.config.enabled:
            return {"BLUE": 0, "WHITE": 0, "RED": 0, "UNKNOWN": 0}

        try:
            http_client = await self._get_http_client()

            # Endpoint pour récupérer les statistiques de la saison
            # Documentation: https://data.rte-france.com/catalog/-/api/tempo
            # Calculer les jours restants depuis la liste complète
            url = f"{self.BASE_URL}/joursTempo"
            response = await http_client.get(url)
            response.raise_for_status()
            data = response.json()
<<<<<<< HEAD
            
=======

>>>>>>> origin/main
            # Compter les jours restants par couleur
            today = date.today()
            remaining = {"BLUE": 0, "WHITE": 0, "RED": 0}
            for day_data in data:
                day_date_str = day_data.get("dateJour", "")
                try:
                    day_date = date.fromisoformat(day_date_str)
                    if day_date >= today:
                        lib_couleur = day_data.get("libCouleur", "").upper()
                        if lib_couleur == "BLEU":
                            remaining["BLUE"] += 1
                        elif lib_couleur == "BLANC":
                            remaining["WHITE"] += 1
                        elif lib_couleur == "ROUGE":
                            remaining["RED"] += 1
                except (ValueError, TypeError):
                    continue

            return {
                "BLUE": remaining.get("BLUE", 0),
                "WHITE": remaining.get("WHITE", 0),
                "RED": remaining.get("RED", 0),
            }

        except Exception as e:
            logger.error("tempo_remaining_days_error", error=str(e))
            return {"BLUE": 0, "WHITE": 0, "RED": 0, "UNKNOWN": 0}

    async def close(self) -> None:
        """Ferme les connexions HTTP et Redis."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

        if self._redis:
            await self._redis.aclose()
            self._redis = None

    async def __aenter__(self) -> "TempoService":
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        await self.close()
<<<<<<< HEAD

=======
>>>>>>> origin/main
