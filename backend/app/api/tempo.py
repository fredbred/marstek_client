"""API endpoints for Tempo RTE integration."""

from datetime import date, timedelta

import structlog
from fastapi import APIRouter, Depends, HTTPException

<<<<<<< HEAD
from app.core.tempo_service import TempoCalendar, TempoColor, TempoService
=======
from app.core.tempo_service import TempoCalendar, TempoService
>>>>>>> origin/main

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/tempo", tags=["tempo"])


async def get_tempo_service() -> TempoService:
    """Dependency for TempoService."""
    return TempoService()


@router.get("/today", response_model=dict)
async def get_tempo_today(
    tempo_service: TempoService = Depends(get_tempo_service),
) -> dict:
    """Récupère la couleur Tempo pour aujourd'hui.

    Returns:
        Dict avec date et color
    """
    try:
        today = date.today()
        color = await tempo_service.get_tempo_color(today)

        calendar = TempoCalendar(date=today, color=color)

        logger.info("tempo_api_today_requested", color=color.value)

        return calendar.to_dict()

    except Exception as e:
        logger.error("tempo_api_today_error", error=str(e))
<<<<<<< HEAD
        raise HTTPException(status_code=500, detail=f"Error fetching Tempo data: {str(e)}")
=======
        raise HTTPException(
            status_code=500, detail=f"Error fetching Tempo data: {str(e)}"
        )
>>>>>>> origin/main


@router.get("/tomorrow", response_model=dict)
async def get_tempo_tomorrow(
    tempo_service: TempoService = Depends(get_tempo_service),
) -> dict:
    """Récupère la couleur Tempo pour demain (J+1).

    La couleur J+1 est généralement disponible à partir de 11h.

    Returns:
        Dict avec date et color
    """
    try:
        tomorrow = date.today() + timedelta(days=1)
        color = await tempo_service.get_tomorrow_color()

        calendar = TempoCalendar(date=tomorrow, color=color)

        logger.info("tempo_api_tomorrow_requested", color=color.value)

        return calendar.to_dict()

    except Exception as e:
        logger.error("tempo_api_tomorrow_error", error=str(e))
<<<<<<< HEAD
        raise HTTPException(status_code=500, detail=f"Error fetching Tempo data: {str(e)}")
=======
        raise HTTPException(
            status_code=500, detail=f"Error fetching Tempo data: {str(e)}"
        )
>>>>>>> origin/main


@router.get("/precharge", response_model=dict)
async def should_activate_precharge(
    tempo_service: TempoService = Depends(get_tempo_service),
) -> dict:
    """Vérifie si la précharge doit être activée.

    Returns:
        Dict avec should_activate (bool) et détails
    """
    try:
        should_activate = await tempo_service.should_activate_precharge()

        today = date.today()
        tomorrow = today + timedelta(days=1)

        today_color = await tempo_service.get_tempo_color(today)
        tomorrow_color = await tempo_service.get_tomorrow_color()

        return {
            "should_activate": should_activate,
            "today": {"date": today.isoformat(), "color": today_color.value},
            "tomorrow": {"date": tomorrow.isoformat(), "color": tomorrow_color.value},
        }

    except Exception as e:
        logger.error("tempo_api_precharge_error", error=str(e))
<<<<<<< HEAD
        raise HTTPException(status_code=500, detail=f"Error checking precharge: {str(e)}")
=======
        raise HTTPException(
            status_code=500, detail=f"Error checking precharge: {str(e)}"
        )
>>>>>>> origin/main


@router.get("/remaining", response_model=dict)
async def get_remaining_days(
    tempo_service: TempoService = Depends(get_tempo_service),
) -> dict:
    """Récupère le nombre de jours restants par couleur dans la saison.

    Returns:
        Dict avec BLUE, WHITE, RED
    """
    try:
        remaining = await tempo_service.get_remaining_days()

        return {
            "remaining_days": remaining,
        }

    except Exception as e:
        logger.error("tempo_api_remaining_error", error=str(e))
<<<<<<< HEAD
        raise HTTPException(status_code=500, detail=f"Error fetching remaining days: {str(e)}")

=======
        raise HTTPException(
            status_code=500, detail=f"Error fetching remaining days: {str(e)}"
        )
>>>>>>> origin/main
