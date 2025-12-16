"""API routes for schedule management."""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session
from app.api.schemas import MessageResponse, ScheduleCreate, ScheduleResponse, ScheduleUpdate
from app.models import ScheduleConfig

logger = structlog.get_logger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/schedules", tags=["schedules"])

# Add rate limit exception handler


@router.get("", response_model=list[ScheduleResponse])
@limiter.limit("30/minute")
async def list_schedules(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> list[ScheduleResponse]:
    """Liste toutes les configurations de planning.

    Returns:
        Liste des schedules
    """
    try:
        stmt = select(ScheduleConfig).order_by(ScheduleConfig.id)
        result = await db.execute(stmt)
        schedules = result.scalars().all()

        logger.info("schedules_listed", count=len(schedules))

        return [ScheduleResponse.model_validate(schedule) for schedule in schedules]

    except Exception as e:
        logger.error("schedules_list_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing schedules: {str(e)}",
        )


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def create_schedule(
    request: Request,
    config: ScheduleCreate,
    db: AsyncSession = Depends(get_db_session),
) -> ScheduleResponse:
    """Crée une nouvelle configuration de planning.

    Args:
        config: Configuration du schedule
        db: Database session

    Returns:
        Schedule créé
    """
    try:
        schedule = ScheduleConfig(**config.model_dump())

        db.add(schedule)
        await db.commit()
        await db.refresh(schedule)

        logger.info("schedule_created", schedule_id=schedule.id, name=schedule.name)

        return ScheduleResponse.model_validate(schedule)

    except Exception as e:
        logger.error("schedule_create_error", error=str(e))
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating schedule: {str(e)}",
        )


@router.put("/{schedule_id}", response_model=ScheduleResponse)
@limiter.limit("20/minute")
async def update_schedule(
    request: Request,
    schedule_id: int,
    config: ScheduleUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> ScheduleResponse:
    """Met à jour une configuration de planning.

    Args:
        schedule_id: ID du schedule
        config: Données de mise à jour
        db: Database session

    Returns:
        Schedule mis à jour

    Raises:
        HTTPException: Si le schedule n'existe pas
    """
    try:
        stmt = select(ScheduleConfig).where(ScheduleConfig.id == schedule_id)
        result = await db.execute(stmt)
        schedule = result.scalar_one_or_none()

        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule {schedule_id} not found",
            )

        # Mettre à jour les champs fournis
        update_data = config.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(schedule, field, value)

        await db.commit()
        await db.refresh(schedule)

        logger.info("schedule_updated", schedule_id=schedule_id, fields=list(update_data.keys()))

        return ScheduleResponse.model_validate(schedule)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("schedule_update_error", schedule_id=schedule_id, error=str(e))
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating schedule: {str(e)}",
        )


@router.delete("/{schedule_id}", response_model=MessageResponse)
@limiter.limit("20/minute")
async def delete_schedule(
    request: Request,
    schedule_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """Supprime une configuration de planning.

    Args:
        schedule_id: ID du schedule
        db: Database session

    Returns:
        Message de confirmation

    Raises:
        HTTPException: Si le schedule n'existe pas
    """
    try:
        stmt = select(ScheduleConfig).where(ScheduleConfig.id == schedule_id)
        result = await db.execute(stmt)
        schedule = result.scalar_one_or_none()

        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule {schedule_id} not found",
            )

        await db.delete(schedule)
        await db.commit()

        logger.info("schedule_deleted", schedule_id=schedule_id)

        return MessageResponse(message=f"Schedule {schedule_id} deleted successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("schedule_delete_error", schedule_id=schedule_id, error=str(e))
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting schedule: {str(e)}",
        )
