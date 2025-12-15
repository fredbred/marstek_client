"""Scheduler for automated battery management."""

from app.scheduler.jobs import (
    job_check_tempo_tomorrow,
    job_health_check,
    job_monitor_batteries,
    job_switch_to_auto,
    job_switch_to_manual_night,
)
from app.scheduler.scheduler import (
    get_scheduler,
    init_scheduler,
    shutdown_scheduler,
    start_scheduler,
    stop_scheduler,
)

__all__ = [
    "init_scheduler",
    "start_scheduler",
    "stop_scheduler",
    "shutdown_scheduler",
    "get_scheduler",
    "job_switch_to_auto",
    "job_switch_to_manual_night",
    "job_check_tempo_tomorrow",
    "job_monitor_batteries",
    "job_health_check",
]
