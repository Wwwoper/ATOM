"""
Модуль, содержащий стратегии для работы с балансом.

Этот модуль реализует паттерн "Стратегия" для выполнения различных операций с балансом.
Основные компоненты:
- Balance: Класс для представления баланса в разных валютах
- BaseBalanceStrategy: Абстрактный базовый класс для всех стратегий
- IncreaseBalanceStrategy: Стратегия увеличения баланса
- DecreaseBalanceStrategy: Стратегия уменьшения баланса
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar

from django.core.exceptions import ValidationError


@dataclass(frozen=True)
class Balance:
    """
    Неизменяемый класс для хранения баланса в разных валютах.

    Attributes:
        euro (Decimal): Сумма в евро
        rub (Decimal): Сумма в рублях
        PRECISION (ClassVar[str]): Точность округления для всех денежных операций

    Example:
        >>> balance = Balance(euro=100.50, rub=5000.75)
        >>> print(balance.euro)  # 100.50
        >>> print(balance.rub)   # 5000.75
    """

    euro: Decimal
    rub: Decimal

    PRECISION: ClassVar[str] = "0.01"

    def __post_init__(self):
        """
        Инициализация объекта с округлением значений до заданной точности.
        Вызывается автоматически после создания объекта.
        """
        object.__setattr__(
            self, "euro", Decimal(str(self.euro)).quantize(Decimal(self.PRECISION))
        )
        object.__setattr__(
            self, "rub", Decimal(str(self.rub)).quantize(Decimal(self.PRECISION))
        )

    def __add__(self, other: "Balance") -> "Balance":
        """
        Операция сложения двух балансов.

        Args:
            other (Balance): Баланс для сложения

        Returns:
            Balance: Новый объект баланса с суммированными значениями

        Example:
            >>> balance1 = Balance(euro=100, rub=5000)
            >>> balance2 = Balance(euro=50, rub=2500)
            >>> result = balance1 + balance2  # Balance(euro=150, rub=7500)
        """
        return Balance(euro=self.euro + other.euro, rub=self.rub + other.rub)

    def __sub__(self, other: "Balance") -> "Balance":
        """
        Операция вычитания балансов.

        Args:
            other (Balance): Баланс для вычитания

        Returns:
            Balance: Новый объект баланса с вычтенными значениями

        Example:
            >>> balance1 = Balance(euro=100, rub=5000)
            >>> balance2 = Balance(euro=50, rub=2500)
            >>> result = balance1 - balance2  # Balance(euro=50, rub=2500)
        """
        return Balance(euro=self.euro - other.euro, rub=self.rub - other.rub)


class BaseBalanceStrategy(ABC):
    """
    Базовый абстрактный класс для всех стратегий работы с балансом.

    Определяет общий интерфейс и базовую функциональность для всех стратегий:
    - Валидация сумм
    - Выполнение операций
    - Обработка ошибок
    """

    @staticmethod
    def validate_amounts(amount_euro: Decimal, amount_rub: Decimal) -> None:
        """
        Проверка корректности денежных сумм.

        Args:
            amount_euro (Decimal): Сумма в евро
            amount_rub (Decimal): Сумма в рублях

        Raises:
            ValidationError: Если любая из сумм отрицательная

        Example:
            >>> BaseBalanceStrategy.validate_amounts(100, 5000)  # OK
            >>> BaseBalanceStrategy.validate_amounts(-100, 5000)  # Raises ValidationError
        """
        if amount_euro < 0 or amount_rub < 0:
            raise ValidationError("Сумма не может быть отрицательной")

    def execute(self, current: Balance, amount: Balance) -> Balance:
        """
        Выполнить операцию с балансом.

        Args:
            current (Balance): Текущий баланс
            amount (Balance): Сумма для операции

        Returns:
            Balance: Новый баланс после выполнения операции

        Raises:
            ValidationError: При ошибках валидации или вычислений
        """
        self.validate_amounts(amount.euro, amount.rub)
        try:
            return self._perform_calculation(current, amount)
        except (TypeError, ValueError, ArithmeticError) as e:
            raise ValidationError(f"Ошибка при расчете баланса: {str(e)}")

    @abstractmethod
    def _perform_calculation(self, current: Balance, amount: Balance) -> Balance:
        """
        Выполнить конкретную операцию с балансом.

        Args:
            current (Balance): Текущий баланс
            amount (Balance): Сумма для операции

        Returns:
            Balance: Результирующий баланс
        """
        pass


class IncreaseBalanceStrategy(BaseBalanceStrategy):
    """
    Стратегия увеличения баланса.

    Используется для операций пополнения баланса, начисления бонусов и т.д.
    """

    def _perform_calculation(self, current: Balance, amount: Balance) -> Balance:
        """
        Увеличить текущий баланс на указанную сумму.

        Args:
            current (Balance): Текущий баланс
            amount (Balance): Сумма для добавления

        Returns:
            Balance: Новый увеличенный баланс
        """
        return current + amount


class DecreaseBalanceStrategy(BaseBalanceStrategy):
    """
    Стратегия уменьшения баланса.

    Используется для операций списания средств, оплаты услуг и т.д.
    """

    def _perform_calculation(self, current: Balance, amount: Balance) -> Balance:
        """
        Уменьшить текущий баланс на указанную сумму.

        Args:
            current (Balance): Текущий баланс
            amount (Balance): Сумма для списания

        Returns:
            Balance: Новый уменьшенный баланс

        Raises:
            ValidationError: Если недостаточно средств для списания
        """
        if current.euro < amount.euro or current.rub < amount.rub:
            raise ValidationError(
                f"Недостаточно средств для списания. "
                f"Текущий баланс: {current.euro}€, {current.rub}₽. "
                f"Требуется: {amount.euro}€, {amount.rub}₽"
            )
        return current - amount
