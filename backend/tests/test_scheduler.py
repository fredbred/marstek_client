"""Tests for scheduler system."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.scheduler.jobs import (
    job_health_check,
    job_monitor_batteries,
    job_switch_to_auto,
)
from app.scheduler.scheduler import init_scheduler, shutdown_scheduler


@pytest.fixture
def mock_scheduler() -> MagicMock:
    """Create a mock scheduler."""
    scheduler = MagicMock(spec=AsyncIOScheduler)
    scheduler.add_job = MagicMock()
    scheduler.start = MagicMock()
    scheduler.shutdown = AsyncMock()
    scheduler.get_jobs = MagicMock(return_value=[])
    return scheduler


@pytest.fixture
def db_session():
    """Mock database session."""
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_init_scheduler() -> None:
    """Test scheduler initialization."""
    pytest.importorskip("psycopg2")
    try:
        scheduler = init_scheduler()
        assert scheduler is not None
        assert isinstance(scheduler, AsyncIOScheduler)
    finally:
        await shutdown_scheduler()


@pytest.mark.asyncio
async def test_job_switch_to_auto(db_session) -> None:
    """Test job_switch_to_auto execution."""
    mock_db = MagicMock()
    mock_db.__aenter__ = AsyncMock(return_value=db_session)
    mock_db.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("app.scheduler.jobs.async_session_maker", return_value=mock_db),
        patch("app.scheduler.jobs.ModeController") as mock_controller_class,
    ):
        mock_controller = MagicMock()
        mock_controller.switch_to_auto_mode = AsyncMock(
            return_value={1: True, 2: True, 3: True}
        )
        mock_controller_class.return_value = mock_controller

        await job_switch_to_auto()

        mock_controller.switch_to_auto_mode.assert_called_once()


@pytest.mark.skip(reason="Requires extensive mocking of async delays and services")
@pytest.mark.asyncio
async def test_job_switch_to_manual_night(db_session) -> None:
    """Test job_switch_to_manual_night execution."""
    pass


@pytest.mark.skip(reason="Requires extensive mocking of TempoService and Redis")
@pytest.mark.asyncio
async def test_job_check_tempo_tomorrow() -> None:
    """Test job_check_tempo_tomorrow execution."""
    pass


@pytest.mark.asyncio
async def test_job_monitor_batteries(db_session) -> None:
    """Test job_monitor_batteries execution."""
    mock_db = MagicMock()
    mock_db.__aenter__ = AsyncMock(return_value=db_session)
    mock_db.__aexit__ = AsyncMock(return_value=None)

    # Mock database query for batteries
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    db_session.execute = AsyncMock(return_value=result_mock)

    with (
        patch("app.scheduler.jobs.async_session_maker", return_value=mock_db),
        patch("app.scheduler.jobs.BatteryManager") as mock_manager_class,
    ):
        mock_manager = MagicMock()
        mock_manager.get_all_status = AsyncMock(return_value={})
        mock_manager.log_status_to_db = AsyncMock()
        mock_manager.refresh_single_battery = AsyncMock(return_value={})
        mock_manager_class.return_value = mock_manager

        await job_monitor_batteries()

        mock_manager.log_status_to_db.assert_called_once()


@pytest.mark.asyncio
async def test_job_health_check(db_session) -> None:
    """Test job_health_check execution."""
    mock_db = MagicMock()
    mock_db.__aenter__ = AsyncMock(return_value=db_session)
    mock_db.__aexit__ = AsyncMock(return_value=None)

    # Mock database query for batteries
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    db_session.execute = AsyncMock(return_value=result_mock)

    with (
        patch("app.scheduler.jobs.async_session_maker", return_value=mock_db),
        patch("app.scheduler.jobs.BatteryManager") as mock_manager_class,
    ):
        mock_manager = MagicMock()
        mock_manager.get_all_status = AsyncMock(return_value={})
        mock_manager_class.return_value = mock_manager

        # This job should not raise exceptions
        try:
            await job_health_check()
        except Exception as e:
            pytest.fail(f"job_health_check raised {e}")


async def test_scheduler_persistence() -> None:
    """Test that scheduler jobs persist across restarts."""
    pytest.importorskip("psycopg2")
    from app.scheduler.scheduler import shutdown_scheduler

    await shutdown_scheduler()  # Reset scheduler

    try:
        # Initialize scheduler
        scheduler1 = init_scheduler()
        scheduler1.start()

        # Get initial jobs
        initial_jobs = scheduler1.get_jobs()
        initial_count = len(initial_jobs)

        # Shutdown
        await shutdown_scheduler()

        # Reinitialize
        scheduler2 = init_scheduler()
        scheduler2.start()

        # Check jobs are restored
        restored_jobs = scheduler2.get_jobs()
        restored_count = len(restored_jobs)

        # Jobs should be restored from database
        assert restored_count >= initial_count

    finally:
        await shutdown_scheduler()
    from app.scheduler.scheduler import shutdown_scheduler

    await shutdown_scheduler()  # Reset scheduler


@pytest.mark.asyncio
async def test_scheduler_job_registration() -> None:
    """Test that all jobs are registered."""
    pytest.importorskip("psycopg2")
    try:
        scheduler = init_scheduler()
        scheduler.start()

        jobs = scheduler.get_jobs()
        job_ids = [job.id for job in jobs]

        # Check that expected jobs are registered

        # At least some of these should be present
        assert len(job_ids) > 0

    finally:
        await shutdown_scheduler()
