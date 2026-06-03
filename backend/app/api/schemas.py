"""Pydantic schemas for API requests and responses."""

from datetime import date, datetime, time

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
    bat_capacity: float | None = Field(
        default=None, description="Battery capacity [Wh]"
    )


class ModbusDiagnosticsResponse(BaseModel):
    """Read-only Modbus diagnostic values."""

    ac_voltage: float | None = Field(default=None, description="AC voltage [V]")
    ac_frequency: float | None = Field(default=None, description="AC frequency [Hz]")
    inverter_state: int | None = Field(default=None, description="Inverter state")
    battery_discharge_current_limit: int | None = Field(
        default=None, description="Battery discharge current limit raw register value"
    )
    max_discharge_power: int | None = Field(
        default=None, description="Maximum discharge power [W]"
    )


class BatteryDiagnosticsResponse(BaseModel):
    """Read-only battery diagnostic summary."""

    battery_id: int
    battery_name: str
    timestamp: datetime
    ip_address: str
    udp_port: int
    soc: int | None = Field(default=None, ge=0, le=100)
    charg_flag: bool | None = None
    dischrg_flag: bool | None = None
    mode: str | None = None
    bat_power: float | None = Field(default=None, description="Battery power [W]")
    pv_power: float | None = Field(default=None, description="PV power [W]")
    pv_voltage: float | None = Field(default=None, description="PV voltage [V]")
    pv_current: float | None = Field(default=None, description="PV current [A]")
    pv_state: int | str | None = Field(default=None, description="PV state")
    ongrid_power: float | None = Field(default=None, description="Grid-tied power [W]")
    offgrid_power: float | None = Field(default=None, description="Off-grid power [W]")
    ct_state: int | None = Field(default=None, description="CT clamp state")
    a_power: float | None = Field(default=None, description="Phase A power [W]")
    b_power: float | None = Field(default=None, description="Phase B power [W]")
    c_power: float | None = Field(default=None, description="Phase C power [W]")
    total_power: float | None = Field(default=None, description="Total meter power [W]")
    input_energy: float | None = Field(default=None, description="Imported energy [Wh]")
    output_energy: float | None = Field(
        default=None, description="Exported energy [Wh]"
    )
    modbus: ModbusDiagnosticsResponse | None = None
    errors: dict[str, str] = Field(default_factory=dict)


class ManualModeConfig(BaseModel):
    """Configuration for manual mode."""

    time_num: int = Field(ge=0, le=9, description="Time period number")
    start_time: str = Field(
        pattern=r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$", description="Start time [hh:mm]"
    )
    end_time: str = Field(
        pattern=r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$", description="End time [hh:mm]"
    )
    week_set: int = Field(ge=0, le=127, description="Week days bitmap")
    power: int = Field(
        description="Power setpoint [W], positive=discharge, negative=charge"
    )
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
    mode_type: str = Field(
        description="Mode type: 'auto', 'manual_night', 'tempo_red', etc."
    )
    start_time: time
    end_time: time
    week_days: int = Field(default=127, ge=0, le=127, description="Week days bitmap")
    power_setpoint: int = Field(
        default=0, description="Power setpoint [W], positive=discharge, negative=charge"
    )
    is_active: bool = Field(default=True)


class ScheduleUpdate(BaseModel):
    """Schema for updating a schedule."""

    name: str | None = Field(default=None, max_length=100)
    mode_type: str | None = None
    start_time: time | None = None
    end_time: time | None = None
    week_days: int | None = Field(default=None, ge=0, le=127)
    power_setpoint: int | None = Field(default=None)
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
    duration_seconds: int = Field(
        ge=60, le=86400, description="Override duration in seconds (min 60, max 86400)"
    )


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
    success: bool = True
