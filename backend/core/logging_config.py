"""
Logging configuration for the File Vault application.

This module configures structured logging for the application,
with appropriate log levels for development and production.
"""

import logging
import sys
from django.conf import settings


def configure_logging():
    """
    Configure logging for the application.
    
    Sets up:
    - Console handler with appropriate format
    - Log level based on DEBUG setting
    - Structured logging for better debugging
    """
    # Determine log level based on DEBUG setting
    log_level = logging.DEBUG if getattr(settings, 'DEBUG', False) else logging.INFO
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    # Set specific loggers
    logging.getLogger('django').setLevel(logging.INFO)
    logging.getLogger('django.db.backends').setLevel(
        logging.DEBUG if getattr(settings, 'DEBUG', False) else logging.WARNING
    )
    logging.getLogger('files').setLevel(log_level)

