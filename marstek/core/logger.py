"""Structured logging configuration."""

import logging
import sys
from pathlib import Path
from typing import Any

import structlog
from structlog.types import Processor

from marstek.core.config import LoggingConfig


def configure_logging(config: LoggingConfig) -> None:
    """Configure structured logging with structlog.

    Args:
        config: Logging configuration
    """
    # Create logs directory if needed
    if config.file:
        log_path = Path(config.file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, config.level),
    )

    # Configure structlog processors
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if config.format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.extend(
            [
                structlog.dev.ConsoleRenderer(colors=True),
            ]
        )

    # Add file handler if configured
    if config.file:
        file_handler = logging.FileHandler(config.file)
        file_handler.setLevel(getattr(logging, config.level))
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

