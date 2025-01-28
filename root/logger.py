import os
import sys
from django.conf import settings
from django.core.cache import cache
import logging


def getLogger(name='root'):
    """
    Returns a configured logger with logging behavior controlled by settings and cache.
    """
    logger = logging.getLogger(name)

    # Retrieve the logging enabled flag from cache or settings
    enable_log = cache.get('LOGGING_ENABLED', getattr(settings, "LOGGING_ENABLED", True))

    if enable_log:
        # Enable logging
        logging.disable(logging.NOTSET)  # Re-enable logging at all levels
        logger.disabled = False
        logger.setLevel(logging.INFO)

        # Remove any NullHandler if present
        if any(isinstance(handler, logging.NullHandler) for handler in logger.handlers):
            logger.handlers = [handler for handler in logger.handlers if not isinstance(handler, logging.NullHandler)]
        
    else:
        # Disable logging
        logging.disable(logging.CRITICAL)  # Suppress all log messages
        logger.disabled = True
        logger.setLevel(logging.CRITICAL + 1)

        # Clear existing handlers
        while logger.handlers:
            logger.handlers.pop()

        # Add a NullHandler to safely handle logs
        logger.addHandler(logging.NullHandler())
        logging.shutdown()

    # Avoid propagating logs to the root logger
    logger.propagate = False
    return logger
