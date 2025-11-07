"""
Logging configuration for Arcane Arsenal.

Provides centralized logging setup with consistent formatting and levels.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    level: str = 'INFO',
    log_file: Optional[str] = None,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Configure logging for Arcane Arsenal.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output
        format_string: Optional custom format string

    Returns:
        Configured root logger

    Example:
        logger = setup_logging(level='DEBUG', log_file='arcane_arsenal.log')
        logger.info("Application started")
    """
    # Default format: timestamp - level - module - message
    if format_string is None:
        format_string = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Console handler (always add)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(format_string))
    logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # Log everything to file
        file_handler.setFormatter(logging.Formatter(format_string))
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance

    Example:
        logger = get_logger(__name__)
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")
    """
    return logging.getLogger(name)


# Default logger for direct imports
logger = get_logger('arcane_arsenal')


__all__ = ['setup_logging', 'get_logger', 'logger']
