"""
Logging configuration for Arcane Arsenal.

Provides centralized logging setup with consistent formatting, levels, and color-coded output.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from colorama import Fore, Back, Style, init

# Initialize colorama for cross-platform color support
init(autoreset=True)


class ColoredFormatter(logging.Formatter):
    """
    Custom formatter that adds color to log output based on level.

    Colors:
    - DEBUG: Cyan
    - INFO: Green
    - WARNING: Yellow
    - ERROR: Red
    - CRITICAL: Red on white background
    """

    # Color scheme for different log levels
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Back.WHITE + Style.BRIGHT,
    }

    # Icons for each level (optional, but adds visual distinction)
    ICONS = {
        'DEBUG': '🔍',
        'INFO': 'ℹ️ ',
        'WARNING': '⚠️ ',
        'ERROR': '❌',
        'CRITICAL': '🚨',
    }

    def format(self, record):
        """Format log record with colors and icons."""
        # Get color for this log level
        color = self.COLORS.get(record.levelname, '')
        icon = self.ICONS.get(record.levelname, '')

        # Save original levelname
        original_levelname = record.levelname

        # Add color and icon to levelname
        record.levelname = f"{color}{icon} {record.levelname}{Style.RESET_ALL}"

        # Format the message
        formatted = super().format(record)

        # Restore original levelname (important for other handlers)
        record.levelname = original_levelname

        return formatted


def setup_logging(
    level: str = 'INFO',
    log_file: Optional[str] = None,
    format_string: Optional[str] = None,
    use_colors: bool = True
) -> logging.Logger:
    """
    Configure logging for Arcane Arsenal with color-coded output.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output
        format_string: Optional custom format string
        use_colors: Whether to use colored output (default: True)

    Returns:
        Configured root logger

    Example:
        logger = setup_logging(level='DEBUG', log_file='arcane_arsenal.log')
        logger.debug("Debug message")  # Cyan
        logger.info("Info message")    # Green
        logger.warning("Warning")      # Yellow
        logger.error("Error!")         # Red
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
    console_handler.setLevel(getattr(logging, level.upper()))  # Respect user's level choice

    if use_colors:
        console_handler.setFormatter(ColoredFormatter(format_string))
    else:
        console_handler.setFormatter(logging.Formatter(format_string))

    logger.addHandler(console_handler)

    # File handler (optional) - no colors in file output
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
