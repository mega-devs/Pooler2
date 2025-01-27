from django.apps import AppConfig


class PoolerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pooler'

    settings = {}

    @classmethod
    def set_setting(cls, key, value):
        cls.settings[key] = value

    @classmethod
    def get_setting(cls, key, default=None):
        return cls.settings.get(key, default)
