"""Модуль содержит константы для работы с балансом."""

from django.db import models


class TransactionTypeChoices(models.TextChoices):
    """Типы возможных транзакций в системе и используемые при добавлении стратегий.

    Перечисление определяет доступные типы операций с балансом пользователя.
    Используется в моделях Django для поля типа транзакции и в сервисном слое
    для определения стратегии обработки транзакции.

    Attributes:
        REPLENISHMENT (str): Пополнение баланса (например, внесение средств)
        EXPENSE (str): Списание средств (например, оплата услуг)
        PAYBACK (str): Возврат средств (например, отмена операции)

    Example:
        >>> transaction.transaction_type = TransactionTypeChoices.REPLENISHMENT
        >>> transaction.get_transaction_type_display()
        'Пополнение'

    Note:
        Наследуется от models.TextChoices для использования в полях модели Django
        и автоматической валидации значений.
    """

    REPLENISHMENT = "replenishment", "Пополнение"
    EXPENSE = "expense", "Списание"
    PAYBACK = "payback", "Возврат"
