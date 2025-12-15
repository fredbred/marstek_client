"""API routes for Tempo RTE integration."""

from datetime import date, timedelta

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.schemas import TempoCalendarResponse
from app.core.tempo_service import TempoCalendar, TempoService

logger = structlog.get_logger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/tempo", tags=["tempo"])

# Add rate limit exception handler
router.state.limiter = limiter
router.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


async def get_tempo_service() -> TempoService:
    """Dependency for TempoService."""
    return TempoService()


@router.get("/today", response_model=TempoCalendarResponse)
@limiter.limit("60/minute")
async def get_tempo_today(
    request: Request,
    tempo_service: TempoService = Depends(get_tempo_service),
) -> TempoCalendarResponse:
    """Récupère la couleur Tempo pour aujourd'hui.

    Returns:
        Couleur Tempo aujourd'hui
    """
    try:
        today = date.today()
        color = await tempo_service.get_tempo_color(today)

        calendar = TempoCalendar(date=today, color=color)

        logger.info("tempo_api_today_requested", color=color.value)

        return TempoCalendarResponse(date=calendar.date, color=calendar.color.value)

    except Exception as e:
        logger.error("tempo_api_today_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching Tempo data: {str(e)}",
        )


@router.get("/tomorrow", response_model=TempoCalendarResponse)
@limiter.limit("60/minute")
async def get_tempo_tomorrow(
    request: Request,
    tempo_service: TempoService = Depends(get_tempo_service),
) -> TempoCalendarResponse:
    """Récupère la couleur Tempo pour demain (J+1).

    La couleur J+1 est généralement disponible à partir de 11h.

    Returns:
        Couleur Tempo demain
    """
    try:
        tomorrow = date.today() + timedelta(days=1)
        color = await tempo_service.get_tomorrow_color()

        calendar = TempoCalendar(date=tomorrow, color=color)

        logger.info("tempo_api_tomorrow_requested", color=color.value)

        return TempoCalendarResponse(date=calendar.date, color=calendar.color.value)

    except Exception as e:
        logger.error("tempo_api_tomorrow_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching Tempo data: {str(e)}",
        )


@router.get("/calendar", response_model=list[TempoCalendarResponse])
@limiter.limit("30/minute")
async def get_tempo_calendar(
    request: Request,
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    tempo_service: TempoService = Depends(get_tempo_service),
) -> list[TempoCalendarResponse]:
    """Récupère le calendrier Tempo pour une plage de dates.

    Args:
        start_date: Date de début
        end_date: Date de fin
        tempo_service: Tempo service

    Returns:
        Liste des couleurs Tempo pour la plage de dates

    Raises:
        HTTPException: Si la plage est invalide (> 30 jours) ou erreur API
    """
    try:
        # Valider la plage de dates
        if end_date < start_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="end_date must be after start_date",
            )

        delta = (end_date - start_date).days
        if delta > 30:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Date range cannot exceed 30 days",
            )

        # Récupérer les couleurs pour chaque date
        calendar: list[TempoCalendarResponse] = []

        current_date = start_date
        while current_date <= end_date:
            color = await tempo_service.get_tempo_color(current_date)
            calendar.append(
                TempoCalendarResponse(date=current_date, color=color.value)
            )
            current_date += timedelta(days=1)

        logger.info(
            "tempo_calendar_requested",
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            count=len(calendar),
        )

        return calendar

    except HTTPException:
        raise
    except Exception as e:
        logger.error("tempo_calendar_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching Tempo calendar: {str(e)}",
        )
