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
from typing import List, TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from balance.models import Transaction
from balance.services.constants import TransactionTypeChoices

if TYPE_CHECKING:
    from balance.models import Transaction


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
    def validate_transaction(cls, transaction: Transaction) -> None:
        """
        Валидация транзакции перед выполнением.

        Args:
            transaction: Транзакция для валидации

        Raises:
            ValidationError: Если транзакция не прошла валидацию
        """
        errors = []

        # Проверка наличия обязательных сумм
        if transaction.amount_euro is None:
            errors.append("Сумма в евро обязательна")
        if transaction.amount_rub is None:
            errors.append("Сумма в рублях обязательна")

        # Если хотя бы одна сумма отсутствует, прерываем дальнейшую валидацию
        if errors:
            raise ValidationError(errors)

        # Проверка положительности сумм
        if transaction.amount_euro <= Decimal(
            "0.00"
        ) or transaction.amount_rub <= Decimal("0.00"):
            errors.append("Суммы должны быть положительными")

        # Проверка достаточности средств для списания
        if transaction.transaction_type == TransactionTypeChoices.EXPENSE:
            balance = transaction.balance
            if (
                balance.balance_euro < transaction.amount_euro
                or balance.balance_rub < transaction.amount_rub
            ):
                errors.append(
                    f"Недостаточно средств для списания. "
                    f"Текущий баланс: {balance.balance_euro}€, {balance.balance_rub}₽. "
                    f"Требуется: {transaction.amount_euro}€, {transaction.amount_rub}₽"
                )

        if errors:
            raise ValidationError(errors)

    @classmethod
    def execute_transaction(cls, transaction) -> None:
        # Импорт внутри метода
        from balance.models import Transaction

        cls.validate_transaction(transaction)

        with db_transaction.atomic():
            balance = transaction.balance

            # Обновляем баланс в зависимости от типа транзакции
            if transaction.transaction_type == TransactionTypeChoices.EXPENSE:
                balance.balance_euro -= transaction.amount_euro
                balance.balance_rub -= transaction.amount_rub
            else:
                balance.balance_euro += transaction.amount_euro
                balance.balance_rub += transaction.amount_rub

            balance.save()

    @classmethod
    def update_balance(cls, transaction: "Transaction") -> None:
        """
        Обновляет баланс на основе транзакции.

        Args:
            transaction: Транзакция для обработки
        """
        with db_transaction.atomic():
            balance = transaction.balance

            if transaction.transaction_type == TransactionTypeChoices.EXPENSE:
                balance.balance_euro -= transaction.amount_euro
                balance.balance_rub -= transaction.amount_rub
            elif transaction.transaction_type == TransactionTypeChoices.REPLENISHMENT:
                balance.balance_euro += transaction.amount_euro
                balance.balance_rub += transaction.amount_rub
            elif transaction.transaction_type == TransactionTypeChoices.PAYBACK:
                balance.balance_euro += transaction.amount_euro
                balance.balance_rub += transaction.amount_rub

            balance.save(allow_balance_update=True)


def process_batch_transactions(transactions: List["Transaction"]) -> None:
    """
    Обработка пакета транзакций.

    Args:
        transactions: Список транзакций для обработки
    """
    with db_transaction.atomic():
        for tr in transactions:
            tr.save()
