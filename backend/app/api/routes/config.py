"""API routes for application configuration."""

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session
from app.models import AppConfig

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/config", tags=["config"])


class TempoConfig(BaseModel):
    """Tempo configuration schema."""

    enabled: bool = True
    target_soc_red: int = 95
    precharge_hour: str = "22:00"
    precharge_power: int = 2000  # Puissance en watts


class ConfigResponse(BaseModel):
    """Generic config response."""

    key: str
    value: str


@router.get("/tempo", response_model=TempoConfig)
async def get_tempo_config(
    db: AsyncSession = Depends(get_db_session),
) -> TempoConfig:
    """Récupère la configuration Tempo.

    Returns:
        Configuration Tempo actuelle
    """
    try:
        stmt = select(AppConfig).where(AppConfig.key.like("tempo_%"))
        result = await db.execute(stmt)
        configs = {row.key: row.value for row in result.scalars().all()}

        return TempoConfig(
            enabled=configs.get("tempo_enabled", "true").lower() == "true",
            target_soc_red=int(configs.get("tempo_target_soc_red", "95")),
            precharge_hour=configs.get("tempo_precharge_hour", "22:00"),
            precharge_power=int(configs.get("tempo_precharge_power", "2000")),
        )
    except Exception as e:
        logger.error("tempo_config_get_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Error getting config: {e}")


@router.put("/tempo", response_model=TempoConfig)
async def update_tempo_config(
    config: TempoConfig,
    db: AsyncSession = Depends(get_db_session),
) -> TempoConfig:
    """Met à jour la configuration Tempo.

    Args:
        config: Nouvelle configuration Tempo

    Returns:
        Configuration Tempo mise à jour
    """
    try:
        from datetime import datetime

        # Mettre à jour chaque clé
        configs_to_update = {
            "tempo_enabled": str(config.enabled).lower(),
            "tempo_target_soc_red": str(config.target_soc_red),
            "tempo_precharge_hour": config.precharge_hour,
            "tempo_precharge_power": str(config.precharge_power),
        }

        for key, value in configs_to_update.items():
            stmt = select(AppConfig).where(AppConfig.key == key)
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                existing.value = value
                existing.updated_at = datetime.utcnow()
            else:
                db.add(AppConfig(key=key, value=value))

        await db.commit()

        logger.info("tempo_config_updated", config=configs_to_update)
        return config

    except Exception as e:
        logger.error("tempo_config_update_error", error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating config: {e}")


@router.get("/{key}", response_model=ConfigResponse)
async def get_config_value(
    key: str,
    db: AsyncSession = Depends(get_db_session),
) -> ConfigResponse:
    """Récupère une valeur de configuration.

    Args:
        key: Clé de configuration

    Returns:
        Valeur de configuration
    """
    stmt = select(AppConfig).where(AppConfig.key == key)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail=f"Config key '{key}' not found")

    return ConfigResponse(key=config.key, value=config.value)
