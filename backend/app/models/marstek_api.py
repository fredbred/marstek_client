"""Pydantic models for Marstek API responses."""

from typing import Literal

from pydantic import BaseModel, Field


class DeviceInfo(BaseModel):
    """Device information from Marstek.GetDevice."""

    device: str = Field(description="Device model (e.g., 'VenusC', 'VenusE')")
    ver: int = Field(description="Device firmware version")
    ble_mac: str = Field(description="Bluetooth MAC address")
    wifi_mac: str = Field(description="WiFi MAC address")
    wifi_name: str | None = Field(default=None, description="WiFi network name")
    ip: str = Field(description="Device IP address")


class BatteryStatus(BaseModel):
    """Battery status from Bat.GetStatus."""

    id: int = Field(description="Instance ID")
    soc: int = Field(description="State of Charge [%]", ge=0, le=100)
    charg_flag: bool = Field(description="Charging permission flag")
    dischrg_flag: bool = Field(description="Discharge permission flag")
    bat_temp: float | None = Field(default=None, description="Battery temperature [°C]")
<<<<<<< HEAD
    bat_capacity: float | None = Field(default=None, description="Battery remaining capacity [Wh]")
    rated_capacity: float | None = Field(default=None, description="Battery rated capacity [Wh]")
=======
    bat_capacity: float | None = Field(
        default=None, description="Battery remaining capacity [Wh]"
    )
    rated_capacity: float | None = Field(
        default=None, description="Battery rated capacity [Wh]"
    )
>>>>>>> origin/main


class ESStatus(BaseModel):
    """Energy System status from ES.GetStatus."""

    id: int | None = Field(default=None, description="Instance ID")
<<<<<<< HEAD
    bat_soc: int | None = Field(default=None, description="Total battery SOC [%]", ge=0, le=100)
=======
    bat_soc: int | None = Field(
        default=None, description="Total battery SOC [%]", ge=0, le=100
    )
>>>>>>> origin/main
    bat_cap: int | None = Field(default=None, description="Total battery capacity [Wh]")
    pv_power: float | None = Field(default=None, description="Solar charging power [W]")
    ongrid_power: float | None = Field(default=None, description="Grid-tied power [W]")
    offgrid_power: float | None = Field(default=None, description="Off-grid power [W]")
    bat_power: float | None = Field(default=None, description="Battery power [W]")
<<<<<<< HEAD
    total_pv_energy: float | None = Field(default=None, description="Total solar energy generated [Wh]")
=======
    total_pv_energy: float | None = Field(
        default=None, description="Total solar energy generated [Wh]"
    )
>>>>>>> origin/main
    total_grid_output_energy: float | None = Field(
        default=None, description="Total grid output energy [Wh]"
    )
    total_grid_input_energy: float | None = Field(
        default=None, description="Total grid input energy [Wh]"
    )
    total_load_energy: float | None = Field(
        default=None, description="Total load (or off-grid) energy consumed [Wh]"
    )


class ModeInfo(BaseModel):
    """Mode information from ES.GetMode."""

    id: int | None = Field(default=None, description="Instance ID")
    mode: str | None = Field(
        default=None,
        description="Device power generation mode: 'Auto', 'AI', 'Manual', or 'Passive'",
    )
    ongrid_power: float | None = Field(default=None, description="Grid-tied power [W]")
    offgrid_power: float | None = Field(default=None, description="Off-grid power [W]")
<<<<<<< HEAD
    bat_soc: int | None = Field(default=None, description="Battery SOC [%]", ge=0, le=100)
=======
    bat_soc: int | None = Field(
        default=None, description="Battery SOC [%]", ge=0, le=100
    )
>>>>>>> origin/main


class AutoConfig(BaseModel):
    """Configuration for Auto mode."""

    enable: Literal[1] = Field(description="ON: 1; OFF: Set another mode")


class AIConfig(BaseModel):
    """Configuration for AI mode."""

    enable: Literal[1] = Field(description="ON: 1; OFF: Set another mode")


class ManualConfig(BaseModel):
    """Configuration for Manual mode."""

<<<<<<< HEAD
    time_num: int = Field(description="Time period serial number, Venus C/E supports 0-9", ge=0, le=9)
    start_time: str = Field(
        description="Start time, hours:minutes [hh:mm]", pattern=r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$"
    )
    end_time: str = Field(
        description="End time, hours:minutes [hh:mm]", pattern=r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$"
=======
    time_num: int = Field(
        description="Time period serial number, Venus C/E supports 0-9", ge=0, le=9
    )
    start_time: str = Field(
        description="Start time, hours:minutes [hh:mm]",
        pattern=r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$",
    )
    end_time: str = Field(
        description="End time, hours:minutes [hh:mm]",
        pattern=r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$",
>>>>>>> origin/main
    )
    week_set: int = Field(
        description="Week setting: byte 8 bits, low 7 bits effective. 1=Monday, 3=Mon+Tue, 127=all week",
        ge=0,
        le=127,
    )
    power: int = Field(description="Setting power [W]", ge=0)
<<<<<<< HEAD
    enable: Literal[0, 1] = Field(description="ON: 1; OFF: 0")
=======
    enable: bool = Field(description="ON: 1; OFF: 0")
>>>>>>> origin/main


class PassiveConfig(BaseModel):
    """Configuration for Passive mode."""

    power: int = Field(description="Setting power [W]", ge=0)
    cd_time: int = Field(description="Power countdown [s]", ge=0)


class ModeConfig(BaseModel):
    """Mode configuration for ES.SetMode."""

    mode: Literal["Auto", "AI", "Manual", "Passive"] = Field(
        description="Device power generation mode"
    )
<<<<<<< HEAD
    auto_cfg: AutoConfig | None = Field(default=None, description="Configuration for Auto mode")
    ai_cfg: AIConfig | None = Field(default=None, description="Configuration for AI mode")
    manual_cfg: ManualConfig | None = Field(default=None, description="Configuration for Manual mode")
=======
    auto_cfg: AutoConfig | None = Field(
        default=None, description="Configuration for Auto mode"
    )
    ai_cfg: AIConfig | None = Field(
        default=None, description="Configuration for AI mode"
    )
    manual_cfg: ManualConfig | None = Field(
        default=None, description="Configuration for Manual mode"
    )
>>>>>>> origin/main
    passive_cfg: PassiveConfig | None = Field(
        default=None, description="Configuration for Passive mode"
    )


class SetModeResult(BaseModel):
    """Result from ES.SetMode."""

    id: int = Field(description="Instance ID")
<<<<<<< HEAD
    set_result: bool = Field(description="true: succeeded in setting; false: failed in setting")

=======
    set_result: bool = Field(
        description="true: succeeded in setting; false: failed in setting"
    )
>>>>>>> origin/main
