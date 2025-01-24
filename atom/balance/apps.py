from django.apps import AppConfig


class BalanceConfig(AppConfig):
    """Конфигурация приложения balance."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "balance"

    def ready(self):
        """Подключает сигналы при загрузке приложения."""
        import balance.signals  # noqa
