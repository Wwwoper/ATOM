"""Конфигурация приложения status."""

from django.apps import AppConfig


class StatusConfig(AppConfig):
    """Конфигурация приложения status."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "status"

    def ready(self):
        """Подключение сигналов при загрузке приложения."""
        import status.signals  # noqa
