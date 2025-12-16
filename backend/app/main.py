"""FastAPI application entry point."""

import os
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import get_settings
from app.core.logger import configure_logging, get_logger
from app.database import init_db
from app.scheduler.scheduler import init_scheduler, shutdown_scheduler, start_scheduler

configure_logging()
logger = get_logger(__name__)
settings = get_settings()

# Rate limiter global
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="API pour l'automatisation des batteries Marstek Venus-E",
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware - restrictive configuration
# In production, set ALLOWED_ORIGINS environment variable
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:8501").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["X-Request-ID"],
)


@app.on_event("startup")
async def startup_event() -> None:
    """Startup event handler."""
    logger.info(
        "application_starting", app_name=settings.app_name, env=settings.app_env
    )

    # Initialiser la base de données
    try:
        await init_db()
        logger.info("database_initialized")
    except Exception as e:
        logger.error("database_init_failed", error=str(e))
        # Ne pas bloquer le démarrage si la DB existe déjà

    # Initialiser et démarrer le scheduler
    try:
        scheduler = init_scheduler()
        start_scheduler()
        logger.info("scheduler_started")
    except Exception as e:
        logger.error("scheduler_start_failed", error=str(e), exc_info=True)
        # Le scheduler est optionnel, on continue sans


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Shutdown event handler."""
    logger.info("application_shutting_down")

    # Arrêter proprement le scheduler
    try:
        await shutdown_scheduler()
    except Exception as e:
        logger.error("scheduler_shutdown_error", error=str(e))


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "message": "Marstek Automation API",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


# Import routers
from app.api.routes import batteries, modes, scheduler, tempo

app.include_router(batteries.router, prefix="/api/v1")
app.include_router(modes.router, prefix="/api/v1")
app.include_router(scheduler.router, prefix="/api/v1")
app.include_router(tempo.router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app_env == "development",
    )
