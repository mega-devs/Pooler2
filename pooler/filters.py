from django.conf import settings
from django.core.cache import cache

class DynamicLoggingFilter:
    def filter(self, record):
        # Fetch the setting dynamically from cache or fallback to default
        return cache.get('LOGGING_ENABLED', getattr(settings, "LOGGING_ENABLED", True))
