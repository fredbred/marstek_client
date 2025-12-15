"""Repository pattern pour accès aux données."""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from marstek.api.marstek_client import BatteryStatus
from marstek.database.models import (
    BatteryStatusRecord,
    ModeChangeRecord,
    TempoDayRecord,
)


class BatteryStatusRepository:
    """Repository pour les status de batteries."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def save_status(self, battery_id: str, status: BatteryStatus) -> BatteryStatusRecord:
        """Sauvegarde un status de batterie.

        Args:
            battery_id: ID de la batterie
            status: Status à sauvegarder

        Returns:
            Enregistrement créé
        """
        record = BatteryStatusRecord(
            battery_id=battery_id,
            timestamp=datetime.fromtimestamp(status.timestamp) if status.timestamp else datetime.utcnow(),
            voltage=status.voltage,
            current=status.current,
            power=status.power,
            soc=status.soc,
            temperature=status.temperature,
            mode=status.mode,
            error_code=status.error_code,
        )

        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)

        return record

    async def get_latest_status(
        self, battery_id: str | None = None
    ) -> list[BatteryStatusRecord]:
        """Récupère le dernier status de chaque batterie (ou d'une seule).

        Args:
            battery_id: ID de la batterie (None pour toutes)

        Returns:
            Liste des derniers status
        """
        if battery_id:
            stmt = (
                select(BatteryStatusRecord)
                .where(BatteryStatusRecord.battery_id == battery_id)
                .order_by(BatteryStatusRecord.timestamp.desc())
                .limit(1)
            )
        else:
            # Pour chaque batterie, récupérer le dernier status
            # Utiliser une sous-requête avec MAX timestamp
            from sqlalchemy import func

            subquery = (
                select(
                    BatteryStatusRecord.battery_id,
                    func.max(BatteryStatusRecord.timestamp).label("max_timestamp"),
                )
                .group_by(BatteryStatusRecord.battery_id)
                .subquery()
            )

            stmt = (
                select(BatteryStatusRecord)
                .join(
                    subquery,
                    (BatteryStatusRecord.battery_id == subquery.c.battery_id)
                    & (BatteryStatusRecord.timestamp == subquery.c.max_timestamp),
                )
            )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_status_history(
        self,
        battery_id: str,
        start_time: datetime,
        end_time: datetime | None = None,
        limit: int = 1000,
    ) -> list[BatteryStatusRecord]:
        """Récupère l'historique des status.

        Args:
            battery_id: ID de la batterie
            start_time: Date de début
            end_time: Date de fin (None = maintenant)
            limit: Nombre maximum de résultats

        Returns:
            Liste des status historiques
        """
        if end_time is None:
            end_time = datetime.utcnow()

        stmt = (
            select(BatteryStatusRecord)
            .where(
                BatteryStatusRecord.battery_id == battery_id,
                BatteryStatusRecord.timestamp >= start_time,
                BatteryStatusRecord.timestamp <= end_time,
            )
            .order_by(BatteryStatusRecord.timestamp.desc())
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class ModeChangeRepository:
    """Repository pour les changements de mode."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def save_change(
        self,
        battery_id: str,
        old_mode: str,
        new_mode: str,
        reason: str,
        success: bool = True,
    ) -> ModeChangeRecord:
        """Sauvegarde un changement de mode.

        Args:
            battery_id: ID de la batterie
            old_mode: Ancien mode
            new_mode: Nouveau mode
            reason: Raison du changement
            success: Si le changement a réussi

        Returns:
            Enregistrement créé
        """
        record = ModeChangeRecord(
            battery_id=battery_id,
            timestamp=datetime.utcnow(),
            old_mode=old_mode,
            new_mode=new_mode,
            reason=reason,
            success=success,
        )

        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)

        return record

    async def get_recent_changes(
        self, battery_id: str | None = None, limit: int = 50
    ) -> list[ModeChangeRecord]:
        """Récupère les changements récents.

        Args:
            battery_id: ID de la batterie (None pour toutes)
            limit: Nombre maximum de résultats

        Returns:
            Liste des changements
        """
        stmt = select(ModeChangeRecord).order_by(
            ModeChangeRecord.timestamp.desc()
        )

        if battery_id:
            stmt = stmt.where(ModeChangeRecord.battery_id == battery_id)

        stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class TempoRepository:
    """Repository pour les jours Tempo."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def save_tempo_day(self, date: datetime, color: str) -> TempoDayRecord:
        """Sauvegarde un jour Tempo.

        Args:
            date: Date du jour
            color: Couleur (RED, BLUE, WHITE)

        Returns:
            Enregistrement créé ou existant
        """
        # Vérifier si existe déjà
        stmt = select(TempoDayRecord).where(TempoDayRecord.date == date)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.color = color
            await self.session.commit()
            await self.session.refresh(existing)
            return existing

        record = TempoDayRecord(date=date, color=color)
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)

        return record

    async def get_tempo_day(self, date: datetime) -> TempoDayRecord | None:
        """Récupère un jour Tempo.

        Args:
            date: Date à récupérer

        Returns:
            Enregistrement ou None
        """
        stmt = select(TempoDayRecord).where(TempoDayRecord.date == date)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

