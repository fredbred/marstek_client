"""Battery model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.status_log import BatteryStatusLog


class Battery(Base):
    """Battery device model."""

    __tablename__ = "batteries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Battery name (e.g., 'Batt1', 'Batt2', 'Batt3')",
    )
    ip_address: Mapped[str] = mapped_column(
        String(15), nullable=False, comment="Device IP address"
    )
    udp_port: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="UDP port for API communication"
    )
    ble_mac: Mapped[str] = mapped_column(
        String(12), unique=True, nullable=False, comment="Bluetooth MAC address"
    )
    wifi_mac: Mapped[str] = mapped_column(
        String(12), nullable=False, comment="WiFi MAC address"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="Whether battery is active"
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Last time battery was seen"
    )

    # Relations
    status_history: Mapped[list["BatteryStatusLog"]] = relationship(
        "BatteryStatusLog",
        back_populates="battery",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<Battery(id={self.id}, name={self.name}, ip={self.ip_address})>"

