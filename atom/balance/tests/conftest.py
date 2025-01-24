"""Конфигурация и фикстуры для тестов баланса.

Этот модуль содержит общие фикстуры и настройки для тестирования:

Фикстуры для моделей:
1. user - базовый пользователь для тестов
2. balance - баланс пользователя
3. user_balance - пользователь с предустановленным балансом

Фикстуры для транзакций:
1. transaction - базовая транзакция
2. replenishment - транзакция пополнения
3. expense - транзакция списания
4. payback - транзакция возврата

Фикстуры для истории:
1. history_record - запись в истории баланса
2. history_sequence - последовательность записей

Особенности:
- Все фикстуры автоматически помечены как @pytest.fixture
- Используется scope="function" для изоляции тестов
- Фикстуры создают минимально необходимые данные
- Поддерживается автоматическая очистка после тестов
"""

import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from balance.models import Transaction
from balance.services.constants import TransactionTypeChoices
from user.services import UserService

User = get_user_model()


@pytest.fixture
def user_service():
    """Предоставляет экземпляр UserService для тестов."""
    return UserService()


@pytest.fixture
def new_user(user_service):
    """Создает тестового пользователя через сервис."""
    return user_service.create_user(
        username="test_user", email="test@example.com", password="test_password123"
    )


@pytest.fixture
def user_balance(new_user):
    """Получает баланс пользователя."""
    return new_user.balance


@pytest.fixture
def deposit_transaction(user_balance):
    """Создает транзакцию пополнения."""
    return Transaction.objects.create(
        balance=user_balance,
        amount_euro=Decimal("100.00"),
        amount_rub=Decimal("10000.00"),
        transaction_type=TransactionTypeChoices.REPLENISHMENT,
        comment="Тестовое пополнение",
    )


@pytest.fixture
def withdrawal_transaction(user_balance):
    """Создает транзакцию списания."""
    return Transaction.objects.create(
        balance=user_balance,
        amount_euro=Decimal("50.00"),
        amount_rub=Decimal("5000.00"),
        transaction_type=TransactionTypeChoices.EXPENSE,
        comment="Тестовое списание",
    )


@pytest.fixture
def refund_transaction(user_balance):
    """Создает транзакцию возврата."""
    return Transaction.objects.create(
        balance=user_balance,
        amount_euro=Decimal("25.00"),
        amount_rub=Decimal("2500.00"),
        transaction_type=TransactionTypeChoices.PAYBACK,
        comment="Тестовый возврат",
    )
