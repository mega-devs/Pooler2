from django.conf import settings
from django.core.cache import cache

import logging
import logging.handlers


def getLogger(name='root'):
    logger = logging.getLogger(name)
    enable_log = cache.get('LOGGING_ENABLED', getattr(settings, "LOGGING_ENABLED", True))
    if enable_log:
        logger.disabled = False
        logger.setLevel(logging.INFO)
        logger.removeFilter(lambda record: False)
    else:
        logger.setLevel(logging.CRITICAL + 1)
        logger.disabled = True
        logger.addFilter(lambda record: False)
        for handler in logger.handlers.copy():
            try:
                logger.removeHandler(handler)
            except ValueError:  # in case another thread has already removed it
                pass
        logger.addHandler(logging.NullHandler())
        logger.propagate = False
    
    return logger