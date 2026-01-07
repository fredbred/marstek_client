"""APScheduler configuration and initialization."""

import signal
from typing import Any

import structlog
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config import get_settings
from app.scheduler.jobs import (
    job_check_tempo_tomorrow,
    job_monitor_batteries,
    job_switch_to_auto,
    job_switch_to_manual_night,
)

logger = structlog.get_logger(__name__)
settings = get_settings()

# Global scheduler instance
_scheduler: AsyncIOScheduler | None = None


def init_scheduler() -> AsyncIOScheduler:
    """Configure et initialise APScheduler avec persistance PostgreSQL.

    Configure le scheduler avec :
    - JobStore SQLAlchemy pour persistance en base de données
    - Timezone Europe/Paris
    - Jobs programmés avec triggers cron/interval
    - Gestion graceful shutdown

    Returns:
        Instance configurée d'AsyncIOScheduler

    Raises:
        RuntimeError: Si le scheduler est déjà initialisé
    """
    global _scheduler

    if _scheduler is not None:
        raise RuntimeError("Scheduler already initialized")

    # Convertir l'URL asyncpg en URL SQLAlchemy standard pour le JobStore
    # SQLAlchemyJobStore n'utilise pas async, donc on doit utiliser psycopg2
    # Format: postgresql://user:pass@host:port/db
    db_url = settings.database.url.replace("+asyncpg", "").replace(
        "postgresql+asyncpg", "postgresql"
    )

    # Si l'URL contient encore asyncpg, la remplacer
    if "+asyncpg" in db_url:
        db_url = db_url.replace("+asyncpg", "")

    # Créer le scheduler avec JobStore PostgreSQL
    jobstores = {
        "default": SQLAlchemyJobStore(
            url=db_url,
            tablename="apscheduler_jobs",
        )
    }

    _scheduler = AsyncIOScheduler(
        jobstores=jobstores,
        timezone=settings.scheduler.timezone,
        max_workers=settings.scheduler.max_workers,
        coalesce=True,  # Fusionner les jobs en retard
        misfire_grace_time=300,  # 5 minutes de grâce pour les jobs manqués
    )

    # Enregistrer les jobs
    _register_jobs(_scheduler)

    # Configurer le graceful shutdown
    _setup_shutdown_handlers()

    logger.info(
        "scheduler_initialized",
        timezone=settings.scheduler.timezone,
        max_workers=settings.scheduler.max_workers,
    )

    return _scheduler


def _register_jobs(scheduler: AsyncIOScheduler) -> None:
    """Enregistre tous les jobs programmés.

    Args:
        scheduler: Instance du scheduler
    """
    # Job: Passage en mode AUTO à 6h00
    scheduler.add_job(
        job_switch_to_auto,
        trigger=CronTrigger(hour=6, minute=0, timezone=settings.scheduler.timezone),
        id="switch_to_auto",
        name="Switch to AUTO mode (6h00)",
        replace_existing=True,
        max_instances=1,  # Une seule instance à la fois
    )

    # Job: Passage en mode MANUAL nuit à 22h00
    scheduler.add_job(
        job_switch_to_manual_night,
        trigger=CronTrigger(hour=22, minute=0, timezone=settings.scheduler.timezone),
        id="switch_to_manual_night",
        name="Switch to MANUAL night mode (22h00)",
        replace_existing=True,
        max_instances=1,
    )

    # Job: Vérification Tempo RTE à 11h30
    scheduler.add_job(
        job_check_tempo_tomorrow,
        trigger=CronTrigger(hour=11, minute=30, timezone=settings.scheduler.timezone),
        id="check_tempo_tomorrow",
        name="Check Tempo RTE and activate precharge (11h30)",
        replace_existing=True,
        max_instances=1,
    )

    # Job: Monitoring batteries toutes les 10 minutes (espacé pour éviter instabilité)
    # Note: Batteries Marstek deviennent instables si interrogées trop fréquemment (<60s)
    scheduler.add_job(
        job_monitor_batteries,
        trigger=IntervalTrigger(minutes=10, timezone=settings.scheduler.timezone),
        id="monitor_batteries",
        name="Monitor batteries and log status (every 10min)",
        replace_existing=True,
        max_instances=1,
    )

    # Health check supprimé car trop fréquent (1min causait instabilité des batteries)
    # La vérification de santé est maintenant intégrée dans job_monitor_batteries

    logger.info("scheduler_jobs_registered", job_count=4)


def _setup_shutdown_handlers() -> None:
    """Configure les handlers pour graceful shutdown."""

    def signal_handler(signum: int, frame: Any) -> None:
        """Handler pour signaux d'arrêt."""
        logger.info("shutdown_signal_received", signal=signum)
        if _scheduler and _scheduler.running:
            import asyncio

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(shutdown_scheduler())
                else:
                    asyncio.run(shutdown_scheduler())
            except RuntimeError:
                # Pas de loop en cours, créer une nouvelle
                asyncio.run(shutdown_scheduler())

    # Enregistrer les handlers de signaux
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


async def shutdown_scheduler() -> None:
    """Arrête proprement le scheduler.

    Attend la fin des jobs en cours avant de fermer.
    """
    global _scheduler

    logger.info("scheduler_shutting_down")

    try:
        if _scheduler is not None and _scheduler.running:
            _scheduler.shutdown(wait=True, timeout=30)
        logger.info("scheduler_shutdown_complete")
    except Exception as e:
        logger.error("scheduler_shutdown_error", error=str(e))

    finally:
        _scheduler = None


def get_scheduler() -> AsyncIOScheduler | None:
    """Récupère l'instance du scheduler.

    Returns:
        Instance du scheduler ou None si non initialisé
    """
    return _scheduler


def start_scheduler() -> None:
    """Démarre le scheduler.

    Raises:
        RuntimeError: Si le scheduler n'est pas initialisé
    """
    if _scheduler is None:
        raise RuntimeError("Scheduler not initialized. Call init_scheduler() first.")

    if _scheduler.running:
        logger.warning("scheduler_already_running")
        return

    _scheduler.start()
    logger.info("scheduler_started", job_count=len(_scheduler.get_jobs()))


def stop_scheduler() -> None:
    """Arrête le scheduler."""
    if _scheduler is None or not _scheduler.running:
        return

    _scheduler.shutdown(wait=False)
    logger.info("scheduler_stopped")
