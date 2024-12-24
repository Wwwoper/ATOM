"""Модуль для работы с балансом пользователей."""

from django.core.exceptions import ValidationError

from .constants import TransactionTypeChoices
from .strategies import (
    Balance,
    BaseBalanceStrategy,
    DecreaseBalanceStrategy,
    IncreaseBalanceStrategy,
)


class BalanceService:
    """Сервис для работы с балансом."""

    _strategies = {
        TransactionTypeChoices.REPLENISHMENT: IncreaseBalanceStrategy(),
        TransactionTypeChoices.EXPENSE: DecreaseBalanceStrategy(),
        TransactionTypeChoices.PAYBACK: IncreaseBalanceStrategy(),
    }

    @classmethod
    def handle_balance_transaction(cls, transaction):
        """Обработка транзакции баланса пользователя.

        Args:
            transaction: Объект транзакции, содержащий информацию о:
                - transaction_type: тип транзакции (пополнение/списание/возврат)
                - balance: связанный баланс пользователя
                - amount_euro: сумма в евро
                - amount_rub: сумма в рублях

        Returns:
            tuple: Кортеж (balance_euro, balance_rub) с новыми значениями баланса

        Raises:
            ValidationError: Если указан неподдерживаемый тип транзакции

        Note:
            Метод выполняется в атомарной транзакции для обеспечения целостности данных.
            Использует паттерн Стратегия для различных типов операций с балансом.
            При сохранении баланса передается флаг allow_balance_update=True для
            разрешения изменения защищенных полей баланса.
        """
        try:
            strategy = cls._strategies[
                TransactionTypeChoices(transaction.transaction_type)
            ]
        except KeyError:
            raise ValidationError(
                f"Неподдерживаемый тип транзакции: {transaction.transaction_type}"
            )

        current_balance = Balance(
            euro=transaction.balance.balance_euro, rub=transaction.balance.balance_rub
        )
        amount = Balance(euro=transaction.amount_euro, rub=transaction.amount_rub)

        new_balance = strategy.execute(current_balance, amount)

        transaction.balance.balance_euro = new_balance.euro
        transaction.balance.balance_rub = new_balance.rub
        transaction.balance.save(allow_balance_update=True)

        return new_balance.euro, new_balance.rub

    @classmethod
    def register_strategy(
        cls, transaction_type: TransactionTypeChoices, strategy: BaseBalanceStrategy
    ):
        """Регистрация новой стратегии обработки баланса.

        Метод позволяет динамически добавлять новые стратегии обработки транзакций
        в сервис баланса.

        Args:
            transaction_type (TransactionTypeChoices): Тип транзакции, для которой
                регистрируется стратегия
            strategy (BalanceStrategy): Экземпляр класса стратегии, реализующий
                интерфейс BalanceStrategy

        Example:
            >>> service = BalanceService
            >>> service.register_strategy(
            ...     TransactionTypeChoices.REPLENISHMENT,
            ...     CustomBalanceStrategy()
            ... )
        """
        cls._strategies[TransactionTypeChoices(transaction_type)] = strategy
