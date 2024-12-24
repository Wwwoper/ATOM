"""
Сервис для обработки финансовых транзакций.

Этот модуль предоставляет функциональность для:
- Валидации финансовых транзакций
- Выполнения транзакций в атомарном режиме
- Обработки ошибок при выполнении транзакций
- Интеграции с сервисами баланса и истории

Основные компоненты:
- TransactionProcessor: Основной класс для обработки транзакций
- Интеграция с Django ORM для атомарных операций
- Валидация бизнес-правил для транзакций
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from django.utils import timezone

from .balance_history_service import BalanceHistoryService
from .balance_service import BalanceService


class TransactionProcessor:
    """
    Сервис для обработки и валидации финансовых транзакций.

    Отвечает за:
    - Валидацию транзакций перед выполнением
    - Проверку бизнес-правил и ограничений
    - Атомарное выполнение транзакций
    - Управление балансом пользователя
    - Создание записей в истории операций

    Attributes:
        MAX_AMOUNT (Decimal): Максимальная сумма для одной транзакции
        MIN_AMOUNT (Decimal): Минимальная сумма для одной транзакции

    Example:
        >>> transaction_data = {
        ...     "balance": user_balance,
        ...     "transaction_type": "REPLENISHMENT",
        ...     "amount_euro": Decimal("100.00"),
        ...     "amount_rub": Decimal("5000.00"),
        ...     "comment": "Пополнение счета"
        ... }
        >>> transaction = TransactionProcessor.execute_transaction(transaction_data)
    """

    MAX_AMOUNT = Decimal("1000000")
    MIN_AMOUNT = Decimal("0")

    @classmethod
    def validate_transaction(cls, transaction) -> "Transaction":
        """
        Проверяет корректность транзакции перед выполнением.

        Выполняет следующие проверки:
        1. Наличие объекта транзакции
        2. Корректность сумм (положительные, не превышают лимит)
        3. Наличие привязки к балансу
        4. Корректность даты транзакции

        Args:
            transaction (Transaction): Объект транзакции для валидации

        Returns:
            Transaction: Валидная транзакция

        Raises:
            ValidationError: Если транзакция не соответствует требованиям:
                - Отсутствует объект транзакции
                - Некорректные суммы
                - Отсутствует баланс
                - Некорректная дата

        Example:
            >>> transaction = Transaction(amount_euro=100, amount_rub=5000)
            >>> validated_transaction = TransactionProcessor.validate_transaction(transaction)
        """
        if transaction is None:
            raise ValidationError("Транзакция не может быть None")

        errors = []

        # Проверка сумм
        try:
            if any(
                [
                    transaction.amount_euro <= cls.MIN_AMOUNT,
                    transaction.amount_rub <= cls.MIN_AMOUNT,
                ]
            ):
                errors.append("Суммы должны быть положительными")

            if any(
                [
                    transaction.amount_euro > cls.MAX_AMOUNT,
                    transaction.amount_rub > cls.MAX_AMOUNT,
                ]
            ):
                errors.append(
                    f"Превышена максимальная сумма транзакции ({cls.MAX_AMOUNT})"
                )
        except (TypeError, AttributeError):
            errors.append("Некорректный формат сумм транзакции")

        # Проверка баланса
        if not transaction.balance:
            errors.append("Не указан баланс для транзакции")

        # Проверка даты
        try:
            if transaction.transaction_date > timezone.now():
                errors.append("Дата транзакции не может быть в будущем")
        except (TypeError, AttributeError):
            errors.append("Некорректный формат даты транзакции")

        if errors:
            raise ValidationError(errors)

        return transaction

    @classmethod
    def execute_transaction(cls, transaction_data: dict) -> "Transaction":
        """Выполняет транзакцию атомарно."""
        from ..models import Transaction

        with db_transaction.atomic():
            # 1. Создание транзакции
            if isinstance(transaction_data, dict):
                transaction = Transaction(
                    balance=transaction_data["balance"],
                    transaction_type=transaction_data["transaction_type"],
                    amount_euro=transaction_data["amount_euro"],
                    amount_rub=transaction_data["amount_rub"],
                    comment=transaction_data["comment"],
                )
            else:
                transaction = transaction_data

            # 2. Валидация
            cls.validate_transaction(transaction)

            # 3. Сохранение без обработки
            transaction.save(process_transaction=False)

            # 4. Обновление баланса
            BalanceService.handle_balance_transaction(transaction)

            # 5. Создание записи в истории
            BalanceHistoryService.create_balance_history_record(transaction)

            return transaction
