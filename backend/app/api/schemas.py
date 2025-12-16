"""Pydantic schemas for API requests and responses."""

from datetime import date, datetime, time
<<<<<<< HEAD
from typing import Any
=======
>>>>>>> origin/main

from pydantic import BaseModel, Field


class BatteryResponse(BaseModel):
    """Response schema for battery information."""

    id: int
    name: str
    ip_address: str
    udp_port: int
    ble_mac: str
    wifi_mac: str
    is_active: bool
    last_seen_at: datetime | None = None

    class Config:
        from_attributes = True


class BatteryUpdate(BaseModel):
    """Schema for updating battery information."""

    name: str | None = Field(default=None, max_length=50)
    ip_address: str | None = Field(default=None, max_length=15)
    udp_port: int | None = Field(default=None, ge=1, le=65535)
    is_active: bool | None = None


class BatteryStatusResponse(BaseModel):
    """Response schema for battery status."""

    battery_id: int
    timestamp: datetime
    soc: int = Field(description="State of Charge [%]", ge=0, le=100)
    bat_power: float | None = Field(default=None, description="Battery power [W]")
    pv_power: float | None = Field(default=None, description="PV power [W]")
    ongrid_power: float | None = Field(default=None, description="Grid power [W]")
    offgrid_power: float | None = Field(default=None, description="Off-grid power [W]")
    mode: str = Field(description="Current mode")
    bat_temp: float | None = Field(default=None, description="Battery temperature [°C]")
<<<<<<< HEAD
    bat_capacity: float | None = Field(default=None, description="Battery capacity [Wh]")
=======
    bat_capacity: float | None = Field(
        default=None, description="Battery capacity [Wh]"
    )
>>>>>>> origin/main


class ManualModeConfig(BaseModel):
    """Configuration for manual mode."""

    time_num: int = Field(ge=0, le=9, description="Time period number")
<<<<<<< HEAD
    start_time: str = Field(pattern=r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$", description="Start time [hh:mm]")
    end_time: str = Field(pattern=r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$", description="End time [hh:mm]")
=======
    start_time: str = Field(
        pattern=r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$", description="Start time [hh:mm]"
    )
    end_time: str = Field(
        pattern=r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$", description="End time [hh:mm]"
    )
>>>>>>> origin/main
    week_set: int = Field(ge=0, le=127, description="Week days bitmap")
    power: int = Field(ge=0, description="Power setpoint [W]")
    enable: int = Field(ge=0, le=1, description="Enable (1) or disable (0)")


class ModeStatusResponse(BaseModel):
    """Response schema for current mode status."""

    battery_id: int
    battery_name: str
    mode: str
    ongrid_power: float | None = None
    offgrid_power: float | None = None
    bat_soc: int | None = Field(default=None, ge=0, le=100)


class ScheduleCreate(BaseModel):
    """Schema for creating a schedule."""

    name: str = Field(max_length=100)
<<<<<<< HEAD
    mode_type: str = Field(description="Mode type: 'auto', 'manual_night', 'tempo_red', etc.")
=======
    mode_type: str = Field(
        description="Mode type: 'auto', 'manual_night', 'tempo_red', etc."
    )
>>>>>>> origin/main
    start_time: time
    end_time: time
    week_days: int = Field(default=127, ge=0, le=127, description="Week days bitmap")
    power_setpoint: int = Field(default=0, ge=0, description="Power setpoint [W]")
    is_active: bool = Field(default=True)


class ScheduleUpdate(BaseModel):
    """Schema for updating a schedule."""

    name: str | None = Field(default=None, max_length=100)
    mode_type: str | None = None
    start_time: time | None = None
    end_time: time | None = None
    week_days: int | None = Field(default=None, ge=0, le=127)
    power_setpoint: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class ScheduleResponse(BaseModel):
    """Response schema for schedule."""

    id: int
    name: str
    mode_type: str
    start_time: time
    end_time: time
    week_days: int
    power_setpoint: int
    is_active: bool

    class Config:
        from_attributes = True


class TempoCalendarResponse(BaseModel):
    """Response schema for Tempo calendar."""

    date: date
    color: str = Field(description="Tempo color: BLUE, WHITE, RED, UNKNOWN")


class OverrideModeRequest(BaseModel):
    """Request schema for mode override."""

    mode: str = Field(description="Mode to set: 'auto', 'manual'")
<<<<<<< HEAD
    duration_seconds: int = Field(ge=60, le=86400, description="Override duration in seconds (min 60, max 86400)")
=======
    duration_seconds: int = Field(
        ge=60, le=86400, description="Override duration in seconds (min 60, max 86400)"
    )
>>>>>>> origin/main


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
    success: bool = True
