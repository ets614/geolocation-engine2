"""Structured logging with ELK (Elasticsearch, Logstash, Kibana) integration."""
import logging
import json
from datetime import datetime
from typing import Any, Dict, Optional


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record.

        Returns:
            JSON formatted log string.
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


class StructuredLogger:
    """Wrapper for structured logging with context."""

    def __init__(self, logger: logging.Logger):
        """Initialize structured logger.

        Args:
            logger: Python logger instance.
        """
        self.logger = logger

    def log_with_context(
        self,
        level: int,
        message: str,
        **kwargs: Any,
    ):
        """Log message with additional context fields.

        Args:
            level: Log level.
            message: Log message.
            **kwargs: Additional context fields.
        """
        record = logging.LogRecord(
            name=self.logger.name,
            level=level,
            pathname="",
            lineno=0,
            msg=message,
            args=(),
            exc_info=None,
        )
        record.extra_fields = kwargs
        self.logger.handle(record)

    def info(self, message: str, **kwargs: Any):
        """Log info level message.

        Args:
            message: Log message.
            **kwargs: Additional context fields.
        """
        self.log_with_context(logging.INFO, message, **kwargs)

    def error(self, message: str, **kwargs: Any):
        """Log error level message.

        Args:
            message: Log message.
            **kwargs: Additional context fields.
        """
        self.log_with_context(logging.ERROR, message, **kwargs)

    def warning(self, message: str, **kwargs: Any):
        """Log warning level message.

        Args:
            message: Log message.
            **kwargs: Additional context fields.
        """
        self.log_with_context(logging.WARNING, message, **kwargs)

    def debug(self, message: str, **kwargs: Any):
        """Log debug level message.

        Args:
            message: Log message.
            **kwargs: Additional context fields.
        """
        self.log_with_context(logging.DEBUG, message, **kwargs)


def setup_structured_logging(
    logger_name: str = "detection-api",
    log_level: str = "INFO",
    log_file: Optional[str] = None,
) -> StructuredLogger:
    """Set up structured logging.

    Args:
        logger_name: Logger name.
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Optional log file path.

    Returns:
        StructuredLogger instance.
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, log_level.upper()))

    formatter = JSONFormatter()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return StructuredLogger(logger)


class LogContext:
    """Context manager for adding context to logs within a scope."""

    def __init__(self, logger: StructuredLogger, context: Dict[str, Any]):
        """Initialize log context.

        Args:
            logger: StructuredLogger instance.
            context: Context dictionary to add to logs.
        """
        self.logger = logger
        self.context = context

    def __enter__(self):
        """Enter context."""
        return self.logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        if exc_type:
            self.logger.error(
                "Exception in log context",
                exception_type=exc_type.__name__,
                exception_message=str(exc_val),
            )
        return False
