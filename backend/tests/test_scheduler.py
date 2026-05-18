"""Tests for scheduler system."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.scheduler.jobs import job_monitor_batteries, job_switch_to_auto
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
    """Test job_monitor_batteries execution with no batteries."""
    mock_db = MagicMock()
    mock_db.__aenter__ = AsyncMock(return_value=db_session)
    mock_db.__aexit__ = AsyncMock(return_value=None)

    # Mock database query returning no batteries
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    db_session.execute = AsyncMock(return_value=result_mock)

    with patch("app.scheduler.jobs.async_session_maker", return_value=mock_db):
        # Should not raise when no batteries exist
        try:
            await job_monitor_batteries()
        except Exception as e:
            pytest.fail(f"job_monitor_batteries raised {e}")


async def test_scheduler_persistence() -> None:
    """Test scheduler can restart without requiring a real PostgreSQL job store."""
    from app.scheduler.scheduler import shutdown_scheduler

    await shutdown_scheduler()  # Reset scheduler

    with patch(
        "app.scheduler.scheduler.SQLAlchemyJobStore",
        lambda **_: MemoryJobStore(),
    ):
        try:
            scheduler1 = init_scheduler()
            scheduler1.start()
            initial_count = len(scheduler1.get_jobs())

            await shutdown_scheduler()

            scheduler2 = init_scheduler()
            scheduler2.start()
            restored_count = len(scheduler2.get_jobs())

            assert initial_count == 4
            assert restored_count == 4

        finally:
            await shutdown_scheduler()


@pytest.mark.asyncio
async def test_scheduler_job_registration() -> None:
    """Test that all expected jobs are registered."""
    with patch(
        "app.scheduler.scheduler.SQLAlchemyJobStore",
        lambda **_: MemoryJobStore(),
    ):
        try:
            scheduler = init_scheduler()
            scheduler.start()

            job_ids = {job.id for job in scheduler.get_jobs()}

            assert job_ids == {
                "switch_to_auto",
                "switch_to_manual_night",
                "check_tempo_tomorrow",
                "monitor_batteries",
            }

        finally:
            await shutdown_scheduler()
