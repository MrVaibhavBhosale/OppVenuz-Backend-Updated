# admin_master/apps.py
from django.apps import AppConfig


class AdminMasterConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "admin_master"

    def ready(self):
        # import signals so post_migrate receiver is registered
        from . import signals  # noqa: F401
