"""Валидаторы для финансовых операций."""

from decimal import Decimal
from typing import Dict, Any, Optional

from django.core.exceptions import ValidationError
from balance.services.constants import TransactionTypeChoices


class TransactionValidator:
    """Валидатор для финансовых транзакций."""

    @staticmethod
    def validate_amounts(
        amount_euro: Optional[Decimal], amount_rub: Optional[Decimal]
    ) -> None:
        """Валидация сумм транзакции."""
        errors = []

        # Проверка на None и тип данных
        if amount_euro is None or not isinstance(amount_euro, Decimal):
            errors.append("Сумма в евро должна быть указана.")
        if amount_rub is None or not isinstance(amount_rub, Decimal):
            errors.append("Сумма в рублях должна быть указана.")

        # Если есть ошибки валидации, прерываем проверку
        if errors:
            raise ValidationError(errors)

        # Проверка на положительные значения
        if amount_euro <= Decimal("0.00") or amount_rub <= Decimal("0.00"):
            errors.append("Суммы должны быть положительными")

        if errors:
            raise ValidationError(errors)

    @staticmethod
    def validate_balance_for_expense(
        balance_euro: Decimal,
        balance_rub: Decimal,
        amount_euro: Decimal,
        amount_rub: Decimal,
    ) -> None:
        """Валидация достаточности средств."""
        if balance_euro < amount_euro or balance_rub < amount_rub:
            raise ValidationError(
                f"Недостаточно средств для списания. "
                f"Текущий баланс: {balance_euro}€, {balance_rub}₽. "
                f"Требуется: {amount_euro}€, {amount_rub}₽"
            )


class TransactionDataValidator:
    """Валидатор данных для создания транзакции."""

    REQUIRED_FIELDS = {"balance", "transaction_type", "amount_euro", "amount_rub"}

    @classmethod
    def validate(cls, data: Dict[str, Any]) -> None:
        """
        Валидация данных для создания транзакции.

        Args:
            data: Словарь с данными транзакции

        Raises:
            ValidationError: Если данные не прошли валидацию
        """
        errors = []

        # Проверка наличия обязательных полей
        missing_fields = cls.REQUIRED_FIELDS - set(data.keys())
        if missing_fields:
            errors.append(f"Отсутствуют обязательные поля: {', '.join(missing_fields)}")
            raise ValidationError(errors)

        # Проверка типа транзакции
        transaction_type = data.get("transaction_type")
        valid_choices = dict(TransactionTypeChoices.choices)
        if transaction_type not in valid_choices:
            errors.append(
                f"Неверный тип транзакции. Допустимые значения: "
                f"{', '.join(f'{value} ({label})' for value, label in TransactionTypeChoices.choices)}"
            )

        # Проверка сумм
        try:
            amount_euro = Decimal(str(data.get("amount_euro", 0)))
            amount_rub = Decimal(str(data.get("amount_rub", 0)))
            TransactionValidator.validate_amounts(amount_euro, amount_rub)
        except (TypeError, ValueError):
            errors.append("Некорректный формат сумм")
        except ValidationError as e:
            errors.extend(e.messages)

        # Проверка баланса
        balance = data.get("balance")
        if balance is None:
            errors.append("Баланс обязателен")
        elif transaction_type == TransactionTypeChoices.EXPENSE:
            try:
                TransactionValidator.validate_balance_for_expense(
                    balance.balance_euro,
                    balance.balance_rub,
                    amount_euro,
                    amount_rub,
                )
            except ValidationError as e:
                errors.extend(e.messages)

        if errors:
            raise ValidationError(errors)


# Пример использования:
"""
data = {
    "balance": user_balance,
    "transaction_type": TransactionTypeChoices.REPLENISHMENT,
    "amount_euro": "100.00",
    "amount_rub": "10000.00",
    "comment": "Пополнение"
}

try:
    TransactionDataValidator.validate(data)
    transaction = Transaction.objects.create(**data)
except ValidationError as e:
    print(f"Ошибка валидации: {e}")
"""
