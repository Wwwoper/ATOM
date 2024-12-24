"""Модели приложения status."""

from django.contrib.contenttypes.models import ContentType
from django.db import models


class StatusGroup(models.Model):
    """Модель группы статусов."""

    name = models.CharField(max_length=100, verbose_name="Название группы")
    code = models.CharField(max_length=50, unique=True, verbose_name="Код группы")
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, verbose_name="Тип сущности"
    )
    allowed_status_transitions = models.JSONField(
        default=dict, blank=True, verbose_name="Разрешенные переходы между статусами"
    )
    transaction_type_by_status = models.JSONField(
        default=dict, blank=True, verbose_name="Типы транзакций для статусов"
    )

    def is_transition_allowed(self, from_status: str, to_status: str) -> bool:
        """
        Проверяет разрешен ли переход из одного статуса в другой.

        Пример:
        allowed_status_transitions = {
            "new": ["paid"],           # из "new" можно перейти только в "paid"
            "paid": ["refunded"],      # из "paid" можно перейти только в "refunded"
            "refunded": ["new"]        # из "refunded" можно перейти только в "new"
        }

        is_transition_allowed("new", "paid") -> True     # разрешено
        is_transition_allowed("new", "refunded") -> False # запрещено
        """
        allowed_transitions = self.allowed_status_transitions.get(
            from_status, []
        )  # получаем список разрешенных переходов из initial_data
        return (
            to_status in allowed_transitions
        )  # проверяем есть ли новый статус в списке

    def get_transaction_type_by_status(self, status: str) -> str:
        """
        Возвращает тип транзакции для указанного статуса.

        Пример:
        transaction_type_by_status = {
            "paid": TransactionTypeChoices.EXPENSE,     # при оплате - списание
            "refunded": TransactionTypeChoices.PAYBACK  # при возврате - возврат средств
        }

        get_transaction_type_by_status("paid") -> "EXPENSE"
        get_transaction_type_by_status("new") -> None  # для статуса new транзакция не нужна
        """
        return self.transaction_type_by_status.get(
            status
        )  # получаем тип транзакции для статуса

    class Meta:
        """Мета-класс модели."""

        verbose_name = "Группа статусов"
        verbose_name_plural = "Группы статусов"
        unique_together = ["code", "content_type"]

    def __str__(self):
        """Строковое представление модели."""
        return self.name


class Status(models.Model):
    """Модель статусов."""

    group = models.ForeignKey(
        StatusGroup,
        on_delete=models.CASCADE,
        related_name="status",
        verbose_name="Группа статусов",
    )
    code = models.CharField(max_length=50, verbose_name="Код статуса")
    name = models.CharField(max_length=50, verbose_name="Название статуса")
    description = models.TextField(blank=True, null=True, verbose_name="Описание")
    is_default = models.BooleanField(default=False, verbose_name="Статус по умолчанию")
    order = models.PositiveIntegerField(default=0, verbose_name="Порядок")

    class Meta:
        """Мета-класс модели."""

        verbose_name = "Статус"
        verbose_name_plural = "Статусы"
        ordering = ["group", "order"]
        unique_together = ["group", "code"]

    def __str__(self):
        """Строковое представление модели."""
        return self.name
