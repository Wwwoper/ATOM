"""
Интеграционные тесты для финансового модуля.

Этот модуль содержит набор интеграционных тестов, которые проверяют:
1. Корректность выполнения финансовых операций:
   - пополнение баланса
   - списание средств
   - возврат средств
2. Взаимодействие компонентов системы:
   - модели Balance и Transaction
   - сервисы для работы с балансом
   - механизмы валидации
3. Целостность данных:
   - корректность сохранения транзакций
   - правильность расчета баланса
   - сохранение истории операций
4. Бизнес-правила:
   - запрет отрицательного баланса
   - валидация сумм операций
   - последовательность транзакций

Особенности реализации:
- Используется реальная база данных (тестовая)
- Тесты изолированы друг от друга
- Каждый тест проверяет конкретный сценарий
- Фикстуры для подготовки тестовых данных
"""

import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from balance.models import Transaction
from balance.services.constants import TransactionTypeChoices


@pytest.mark.django_db
def test_initial_balance(user_balance):
    """Проверка начального баланса."""
    assert user_balance.balance_euro == Decimal("0.00")
    assert user_balance.balance_rub == Decimal("0.00")


@pytest.mark.django_db
def test_deposit_flow(user_balance, deposit_transaction):
    """
    Тест сценария пополнения баланса.

    Проверяет:
    1. Корректность изменения баланса после пополнения
    2. Создание транзакции с правильными параметрами
    3. Наличие транзакции в истории операций
    """
    # Проверка баланса
    user_balance.refresh_from_db()
    assert user_balance.balance_euro == Decimal("100.00")
    assert user_balance.balance_rub == Decimal("10000.00")

    # Проверка транзакции
    assert deposit_transaction.transaction_type == TransactionTypeChoices.REPLENISHMENT
    assert deposit_transaction.amount_euro == Decimal("100.00")
    assert deposit_transaction.amount_rub == Decimal("10000.00")
    assert deposit_transaction.balance == user_balance

    # Проверка истории транзакций
    transactions = Transaction.objects.filter(balance=user_balance)
    assert transactions.count() == 1
    assert transactions.first() == deposit_transaction


@pytest.mark.django_db
def test_withdrawal_after_deposit(
    user_balance, deposit_transaction, withdrawal_transaction
):
    """
    Тест сценария списания с баланса.

    Проверяет:
    1. Корректность изменения баланса после списания
    2. Создание транзакции списания с правильными параметрами
    3. Наличие транзакции в истории операций
    """
    # Проверка баланса
    user_balance.refresh_from_db()
    assert user_balance.balance_euro == Decimal("50.00")  # 100 - 50
    assert user_balance.balance_rub == Decimal("5000.00")  # 10000 - 5000

    # Проверка транзакции
    assert withdrawal_transaction.transaction_type == TransactionTypeChoices.EXPENSE
    assert withdrawal_transaction.amount_euro == Decimal("50.00")
    assert withdrawal_transaction.amount_rub == Decimal("5000.00")
    assert withdrawal_transaction.balance == user_balance

    # Проверка истории транзакций
    transactions = Transaction.objects.filter(
        balance=user_balance, transaction_type=TransactionTypeChoices.EXPENSE
    )
    assert transactions.count() == 1
    assert transactions.first() == withdrawal_transaction


@pytest.mark.django_db
def test_refund_flow(
    user_balance, deposit_transaction, withdrawal_transaction, refund_transaction
):
    """
    Тест сценария возврата средств.

    Проверяет:
    1. Корректность изменения баланса после возврата
    2. Создание транзакции возврата с правильными параметрами
    3. Наличие транзакции в истории операций
    """
    # Проверка баланса
    user_balance.refresh_from_db()
    assert user_balance.balance_euro == Decimal("75.00")  # 100 - 50 + 25
    assert user_balance.balance_rub == Decimal("7500.00")  # 10000 - 5000 + 2500

    # Проверка транзакции
    assert refund_transaction.transaction_type == TransactionTypeChoices.PAYBACK
    assert refund_transaction.amount_euro == Decimal("25.00")
    assert refund_transaction.amount_rub == Decimal("2500.00")
    assert refund_transaction.balance == user_balance

    # Проверка истории транзакций
    transactions = Transaction.objects.filter(
        balance=user_balance, transaction_type=TransactionTypeChoices.PAYBACK
    )
    assert transactions.count() == 1
    assert transactions.first() == refund_transaction


@pytest.mark.django_db
def test_transaction_history(
    user_balance, deposit_transaction, withdrawal_transaction, refund_transaction
):
    """
    Тест истории транзакций.

    Проверяет:
    1. Общее количество транзакций
    2. Порядок транзакций
    3. Правильность типов транзакций
    """
    transactions = Transaction.objects.filter(balance=user_balance).order_by(
        "transaction_date"
    )
    assert transactions.count() == 3

    # Проверка порядка и типов транзакций
    assert transactions[0].transaction_type == TransactionTypeChoices.REPLENISHMENT
    assert transactions[1].transaction_type == TransactionTypeChoices.EXPENSE
    assert transactions[2].transaction_type == TransactionTypeChoices.PAYBACK


@pytest.mark.django_db
@pytest.mark.parametrize(
    "amount_euro,amount_rub",
    [
        (Decimal("-100.00"), Decimal("-10000.00")),
        (Decimal("0.00"), Decimal("0.00")),
    ],
)
def test_invalid_deposit_amounts(user_balance, amount_euro, amount_rub):
    """Тест валидации сумм при создании транзакции."""
    with pytest.raises(ValidationError, match="Суммы должны быть положительными"):
        Transaction.objects.create(
            balance=user_balance,
            amount_euro=amount_euro,
            amount_rub=amount_rub,
            transaction_type=TransactionTypeChoices.REPLENISHMENT,
            comment="Тестовое пополнение с неверными суммами",
        )


@pytest.mark.django_db
def test_deposit_transaction_in_db(user_balance, deposit_transaction):
    """Тест сохранения транзакции пополнения в базе данных."""
    transaction = Transaction.objects.get(id=deposit_transaction.id)
    assert transaction.transaction_type == TransactionTypeChoices.REPLENISHMENT
    assert transaction.amount_euro == Decimal("100.00")
    assert transaction.amount_rub == Decimal("10000.00")


@pytest.mark.django_db
def test_withdrawal_transaction_in_db(
    user_balance, deposit_transaction, withdrawal_transaction
):
    """Тест сохранения транзакции списания в базе данных."""
    transaction = Transaction.objects.get(id=withdrawal_transaction.id)
    assert transaction.transaction_type == TransactionTypeChoices.EXPENSE
    assert transaction.amount_euro == Decimal("50.00")
    assert transaction.amount_rub == Decimal("5000.00")


@pytest.mark.django_db
def test_refund_transaction_in_db(
    user_balance, deposit_transaction, withdrawal_transaction, refund_transaction
):
    """Тест сохранения транзакции возврата в базе данных."""
    transaction = Transaction.objects.get(id=refund_transaction.id)
    assert transaction.transaction_type == TransactionTypeChoices.PAYBACK
    assert transaction.amount_euro == Decimal("25.00")
    assert transaction.amount_rub == Decimal("2500.00")
