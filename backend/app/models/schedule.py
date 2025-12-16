"""Schedule configuration model."""

from datetime import time

from sqlalchemy import String, Integer, Boolean, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ScheduleConfig(Base):
    """Schedule configuration for battery mode switching."""

    __tablename__ = "schedule_configs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Schedule name (e.g., 'Auto Day', 'Manual Night')",
    )
    mode_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Mode type: 'auto', 'manual_night', 'tempo_red', etc.",
    )
    start_time: Mapped[time] = mapped_column(
        Time, nullable=False, comment="Start time for this schedule"
    )
    end_time: Mapped[time] = mapped_column(
        Time, nullable=False, comment="End time for this schedule"
    )
    week_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=127,
        comment="Week days bitmap: 0-127 (1=Monday, 3=Mon+Tue, 127=all week)",
    )
    power_setpoint: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Power setpoint [W] (0 = no limit)",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="Whether schedule is active"
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<ScheduleConfig(id={self.id}, name={self.name}, "
            f"mode_type={self.mode_type}, start={self.start_time}, end={self.end_time})>"
        )
