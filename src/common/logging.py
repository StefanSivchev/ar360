import logging
import sys

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars


def configure_logging(level: str = "INFO", json_logs: bool = True) -> None:
    """Configure structlog once, at process start."""
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)

    renderer = structlog.processors.JSONRenderer() if json_logs else structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "ar360") -> structlog.BoundLogger:
    """Return a logger, Call after configure_logging() to ensure proper configuration."""
    return structlog.get_logger(name)


def bind_run(**kwargs: object) -> None:
    """Bind run scoped keys onto every sebsequent log message."""
    clear_contextvars()
    bind_contextvars(**kwargs)
