"""Structured logging configuration for Interview Copilot API."""

import logging
import sys
from pythonjsonlogger import jsonlogger
from config import config


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields."""

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record['app'] = 'interview-copilot'
        log_record['environment'] = 'production' if not config.api_debug else 'development'
        log_record['level'] = record.levelname


def setup_logging():
    """Configure structured JSON logging."""
    # Create logger
    logger = logging.getLogger('interview_copilot')
    logger.setLevel(logging.DEBUG if config.api_debug else logging.INFO)

    # Remove existing handlers
    logger.handlers = []

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if config.api_debug else logging.INFO)

    # Use JSON formatter for structured logs
    formatter = CustomJsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s %(pathname)s %(lineno)d',
        rename_fields={'timestamp': '@timestamp', 'level': 'severity'}
    )
    console_handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(console_handler)

    return logger


# Create logger instance
logger = setup_logging()


def log_info(message: str, **kwargs):
    """Log info message with additional context."""
    logger.info(message, extra=kwargs)


def log_error(message: str, **kwargs):
    """Log error message with additional context."""
    logger.error(message, extra=kwargs, exc_info=True)


def log_warning(message: str, **kwargs):
    """Log warning message with additional context."""
    logger.warning(message, extra=kwargs)


def log_debug(message: str, **kwargs):
    """Log debug message with additional context."""
    logger.debug(message, extra=kwargs)
