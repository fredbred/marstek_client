"""SQLAlchemy models for TimescaleDB."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from marstek.core.config import DatabaseConfig
from marstek.core.logger import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class BatteryStatusRecord(Base):
    """Modèle pour enregistrer les status des batteries dans TimescaleDB."""

    __tablename__ = "battery_status"

    id = Column(Integer, primary_key=True, autoincrement=True)
    battery_id = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # Status values
    voltage = Column(Float)
    current = Column(Float)
    power = Column(Float)
    soc = Column(Float)  # State of Charge (0-100)
    temperature = Column(Float)
    mode = Column(String(20))  # AUTO, MANUAL, etc.
    error_code = Column(Integer)

    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<BatteryStatusRecord(battery_id={self.battery_id}, "
            f"timestamp={self.timestamp}, soc={self.soc}%)>"
        )


class ModeChangeRecord(Base):
    """Modèle pour enregistrer les changements de mode."""

    __tablename__ = "mode_changes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    battery_id = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    old_mode = Column(String(20))
    new_mode = Column(String(20), nullable=False)
    reason = Column(String(100))  # AUTO_SCHEDULE, MANUAL, TEMPO, etc.
    success = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<ModeChangeRecord(battery_id={self.battery_id}, "
            f"{self.old_mode} -> {self.new_mode})>"
        )


class TempoDayRecord(Base):
    """Modèle pour enregistrer les jours Tempo."""

    __tablename__ = "tempo_days"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime(timezone=True), nullable=False, unique=True, index=True)
    color = Column(String(10), nullable=False)  # RED, BLUE, WHITE
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    def __repr__(self) -> str:
        """String representation."""
        return f"<TempoDayRecord(date={self.date}, color={self.color})>"


class Database:
    """Gestionnaire de base de données avec SQLAlchemy async."""

    def __init__(self, config: DatabaseConfig) -> None:
        """Initialize database manager.

        Args:
            config: Database configuration
        """
        self.config = config
        self.engine = create_async_engine(
            config.url,
            echo=False,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
        self.async_session = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def create_tables(self) -> None:
        """Crée toutes les tables (et hypertables TimescaleDB)."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Créer les hypertables TimescaleDB pour les tables temporelles
        from sqlalchemy import text

        async with self.engine.begin() as conn:
            # Hypertable pour battery_status
            try:
                await conn.execute(
                    text(
                        "SELECT create_hypertable('battery_status', 'timestamp', if_not_exists => TRUE);"
                    )
                )
            except Exception as e:
                # TimescaleDB peut ne pas être disponible en test
                logger.warning("failed_to_create_hypertable", table="battery_status", error=str(e))

            # Hypertable pour mode_changes
            try:
                await conn.execute(
                    text(
                        "SELECT create_hypertable('mode_changes', 'timestamp', if_not_exists => TRUE);"
                    )
                )
            except Exception as e:
                logger.warning("failed_to_create_hypertable", table="mode_changes", error=str(e))

    async def close(self) -> None:
        """Ferme la connexion à la base de données."""
        await self.engine.dispose()

    async def __aenter__(self) -> "Database":
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Context manager exit."""
        await self.close()

