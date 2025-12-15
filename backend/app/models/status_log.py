"""Battery status log model (TimescaleDB hypertable)."""

from datetime import datetime

from sqlalchemy import String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class BatteryStatusLog(Base):
    """Battery status log for TimescaleDB hypertable.

    This table will be converted to a TimescaleDB hypertable for efficient
    time-series data storage and queries.
    """

    __tablename__ = "battery_status_logs"

    battery_id: Mapped[int] = mapped_column(
        ForeignKey("batteries.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        comment="Foreign key to batteries table",
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        nullable=False,
        comment="Timestamp of the status reading",
    )
    soc: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="State of Charge [%]"
    )
    bat_power: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Battery power [W]"
    )
    pv_power: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Photovoltaic power [W]"
    )
    ongrid_power: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Grid-tied power [W]"
    )
    offgrid_power: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Off-grid power [W]"
    )
    mode: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="Device mode (Auto, Manual, AI, Passive)"
    )
    bat_temp: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Battery temperature [°C]"
    )
    bat_capacity: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Battery remaining capacity [Wh]"
    )

    # Relations
    battery: Mapped["Battery"] = relationship(
        "Battery", back_populates="status_history"
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<BatteryStatusLog(battery_id={self.battery_id}, "
            f"timestamp={self.timestamp}, soc={self.soc}%)>"
        )

