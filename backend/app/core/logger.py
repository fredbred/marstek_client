"""Structured logging configuration."""

import logging
import sys
from pathlib import Path

import structlog
from structlog.types import Processor

from app.config import get_settings

settings = get_settings()


def configure_logging() -> None:
    """Configure structured logging with structlog."""
    # Create logs directory if needed
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level),
    )

    # Configure structlog processors
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    # Use JSON format in production, console in development
    if settings.app_env == "production":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.extend(
            [
                structlog.dev.ConsoleRenderer(colors=True),
            ]
        )

    # Add file handler
    file_handler = logging.FileHandler(log_dir / "marstek.log")
    file_handler.setLevel(getattr(logging, settings.log_level))
    logging.getLogger().addHandler(file_handler)

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a configured logger instance.

    Args:
        name: Logger name (default: module name)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)

