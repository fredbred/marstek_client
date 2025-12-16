"""API routes for battery management."""


import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_battery_manager, get_db_session
from app.api.schemas import (
    BatteryResponse,
    BatteryStatusResponse,
    BatteryUpdate,
)
from app.core import BatteryManager
from app.models import Battery

logger = structlog.get_logger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/batteries", tags=["batteries"])

# Add rate limit exception handler


@router.get("", response_model=list[BatteryResponse])
@limiter.limit("30/minute")
async def list_batteries(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> list[BatteryResponse]:
    """Liste toutes les batteries enregistrées.

    Returns:
        Liste des batteries
    """
    try:
        stmt = select(Battery).order_by(Battery.id)
        result = await db.execute(stmt)
        batteries = result.scalars().all()

        logger.info("batteries_listed", count=len(batteries))

        return [BatteryResponse.model_validate(battery) for battery in batteries]

    except Exception as e:
        logger.error("batteries_list_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing batteries: {str(e)}",
        )


@router.get("/{battery_id}/status", response_model=BatteryStatusResponse)
@limiter.limit("60/minute")
async def get_battery_status(
    request: Request,
    battery_id: int,
    db: AsyncSession = Depends(get_db_session),
    manager: BatteryManager = Depends(get_battery_manager),
) -> BatteryStatusResponse:
    """Récupère le status actuel d'une batterie.

    Args:
        battery_id: ID de la batterie
        db: Database session
        manager: Battery manager

    Returns:
        Status de la batterie

    Raises:
        HTTPException: Si la batterie n'existe pas ou erreur de récupération
    """
    try:
        # Vérifier que la batterie existe
        stmt = select(Battery).where(Battery.id == battery_id)
        result = await db.execute(stmt)
        battery = result.scalar_one_or_none()

        if not battery:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Battery {battery_id} not found",
            )

        # Récupérer le status
        status_dict = await manager.get_all_status(db)

        if battery_id not in status_dict:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Unable to retrieve status for battery {battery_id}",
            )

        status_data = status_dict[battery_id]

        if "error" in status_data:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Error retrieving status: {status_data['error']}",
            )

        bat_status = status_data.get("bat_status", {})
        es_status = status_data.get("es_status", {})
        mode_info = status_data.get("mode_info", {})

        from datetime import datetime

        return BatteryStatusResponse(
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

    except HTTPException:
        raise
    except Exception as e:
        logger.error("battery_status_error", battery_id=battery_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving battery status: {str(e)}",
        )


@router.post("/discover", response_model=list[BatteryResponse])
@limiter.limit("5/minute")
async def discover_batteries(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    manager: BatteryManager = Depends(get_battery_manager),
) -> list[BatteryResponse]:
    """Découvre et enregistre les batteries sur le réseau.

    Utilise UDP broadcast pour découvrir les devices Marstek.

    Returns:
        Liste des batteries découvertes et enregistrées
    """
    try:
        logger.info("battery_discovery_requested")

        batteries = await manager.discover_and_register(db)

        logger.info("battery_discovery_complete", batteries_found=len(batteries))

        return [BatteryResponse.model_validate(battery) for battery in batteries]

    except Exception as e:
        logger.error("battery_discovery_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error discovering batteries: {str(e)}",
        )


@router.patch("/{battery_id}", response_model=BatteryResponse)
@limiter.limit("20/minute")
async def update_battery(
    request: Request,
    battery_id: int,
    data: BatteryUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> BatteryResponse:
    """Met à jour les informations d'une batterie.

    Args:
        battery_id: ID de la batterie
        data: Données de mise à jour
        db: Database session

    Returns:
        Batterie mise à jour

    Raises:
        HTTPException: Si la batterie n'existe pas
    """
    try:
        stmt = select(Battery).where(Battery.id == battery_id)
        result = await db.execute(stmt)
        battery = result.scalar_one_or_none()

        if not battery:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Battery {battery_id} not found",
            )

        # Mettre à jour les champs fournis
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(battery, field, value)

        await db.commit()
        await db.refresh(battery)

        logger.info(
            "battery_updated", battery_id=battery_id, fields=list(update_data.keys())
        )

        return BatteryResponse.model_validate(battery)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("battery_update_error", battery_id=battery_id, error=str(e))
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating battery: {str(e)}",
        )
