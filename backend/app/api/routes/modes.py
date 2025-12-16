"""API routes for mode management."""

import structlog
<<<<<<< HEAD
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
=======
from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
>>>>>>> origin/main
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_battery_manager, get_db_session
from app.api.schemas import (
    ManualModeConfig,
    MessageResponse,
    ModeStatusResponse,
    OverrideModeRequest,
)
from app.core import BatteryManager, ModeController
from app.models import Battery

logger = structlog.get_logger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/modes", tags=["modes"])

# Add rate limit exception handler


@router.get("/current", response_model=list[ModeStatusResponse])
@limiter.limit("30/minute")
async def get_current_modes(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    manager: BatteryManager = Depends(get_battery_manager),
) -> list[ModeStatusResponse]:
    """Récupère le mode actuel de toutes les batteries.

    Returns:
        Liste des modes actuels par batterie
    """
    try:
        # Récupérer toutes les batteries
<<<<<<< HEAD
        stmt = select(Battery).where(Battery.is_active == True)
=======
        stmt = select(Battery).where(Battery.is_active)
>>>>>>> origin/main
        result = await db.execute(stmt)
        batteries = result.scalars().all()

        # Récupérer les status
        status_dict = await manager.get_all_status(db)

        modes: list[ModeStatusResponse] = []

        for battery in batteries:
            if battery.id in status_dict:
                status_data = status_dict[battery.id]
                mode_info = status_data.get("mode_info", {})

                modes.append(
                    ModeStatusResponse(
                        battery_id=battery.id,
                        battery_name=battery.name,
                        mode=mode_info.get("mode", "Unknown"),
                        ongrid_power=mode_info.get("ongrid_power"),
                        offgrid_power=mode_info.get("offgrid_power"),
                        bat_soc=mode_info.get("bat_soc"),
                    )
                )

        logger.info("current_modes_retrieved", count=len(modes))

        return modes

    except Exception as e:
        logger.error("current_modes_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving current modes: {str(e)}",
        )


@router.post("/auto", response_model=MessageResponse)
@limiter.limit("10/minute")
async def set_auto_mode(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    manager: BatteryManager = Depends(get_battery_manager),
) -> MessageResponse:
    """Passe toutes les batteries en mode AUTO.

    Returns:
        Message de confirmation
    """
    try:
        controller = ModeController(manager)

        results = await controller.switch_to_auto_mode(db)

        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)

        if success_count == total_count:
            message = f"All batteries ({total_count}) switched to AUTO mode"
            logger.info("auto_mode_set_success", battery_count=total_count)
        else:
            message = f"Partial success: {success_count}/{total_count} batteries switched to AUTO mode"
<<<<<<< HEAD
            logger.warning("auto_mode_set_partial", success_count=success_count, total_count=total_count)
=======
            logger.warning(
                "auto_mode_set_partial",
                success_count=success_count,
                total_count=total_count,
            )
>>>>>>> origin/main

        return MessageResponse(message=message, success=success_count == total_count)

    except Exception as e:
        logger.error("auto_mode_set_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error setting AUTO mode: {str(e)}",
        )


@router.post("/manual", response_model=MessageResponse)
@limiter.limit("10/minute")
async def set_manual_mode(
    request: Request,
    config: ManualModeConfig,
    db: AsyncSession = Depends(get_db_session),
    manager: BatteryManager = Depends(get_battery_manager),
) -> MessageResponse:
    """Passe toutes les batteries en mode MANUAL avec configuration.

    Args:
        config: Configuration du mode manuel
        db: Database session
        manager: Battery manager

    Returns:
        Message de confirmation
    """
    try:
        from app.models.marstek_api import ManualConfig

        manual_config = ManualConfig(
            time_num=config.time_num,
            start_time=config.start_time,
            end_time=config.end_time,
            week_set=config.week_set,
            power=config.power,
<<<<<<< HEAD
            enable=config.enable,
=======
            enable=bool(config.enable),
>>>>>>> origin/main
        )

        mode_config = {
            "mode": "manual",
            "config": manual_config.model_dump(),
        }

        results = await manager.set_mode_all(db, mode_config)

        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)

        if success_count == total_count:
            message = f"All batteries ({total_count}) switched to MANUAL mode"
            logger.info("manual_mode_set_success", battery_count=total_count)
        else:
            message = f"Partial success: {success_count}/{total_count} batteries switched to MANUAL mode"
<<<<<<< HEAD
            logger.warning("manual_mode_set_partial", success_count=success_count, total_count=total_count)
=======
            logger.warning(
                "manual_mode_set_partial",
                success_count=success_count,
                total_count=total_count,
            )
>>>>>>> origin/main

        return MessageResponse(message=message, success=success_count == total_count)

    except Exception as e:
        logger.error("manual_mode_set_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error setting MANUAL mode: {str(e)}",
        )


@router.post("/override", response_model=MessageResponse)
@limiter.limit("5/minute")
async def override_mode(
    request: Request,
    override_request: OverrideModeRequest,
    db: AsyncSession = Depends(get_db_session),
    manager: BatteryManager = Depends(get_battery_manager),
) -> MessageResponse:
    """Override temporaire du mode pour une durée spécifiée.

    Args:
        override_request: Requête avec mode et durée
        db: Database session
        manager: Battery manager

    Returns:
        Message de confirmation

    Note:
        L'override sera automatiquement annulé après duration_seconds.
        Un job scheduler devrait être créé pour restaurer le mode normal.
    """
    try:
        mode = override_request.mode.lower()

        if mode == "auto":
            controller = ModeController(manager)
            results = await controller.switch_to_auto_mode(db)
        elif mode == "manual":
            # Mode manuel par défaut (nuit)
            controller = ModeController(manager)
            results = await controller.switch_to_manual_night(db)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid mode: {mode}. Must be 'auto' or 'manual'",
            )

        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)

        # TODO: Créer un job scheduler pour restaurer le mode après duration_seconds

        message = (
            f"Mode override to {mode.upper()} activated for {override_request.duration_seconds}s. "
            f"Success: {success_count}/{total_count} batteries"
        )

        logger.info(
            "mode_override_activated",
            mode=mode,
            duration=override_request.duration_seconds,
            success_count=success_count,
        )

        return MessageResponse(message=message, success=success_count == total_count)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("mode_override_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error overriding mode: {str(e)}",
        )
