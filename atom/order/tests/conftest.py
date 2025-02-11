"""Фикстуры для тестов заказов."""

import pytest
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from order.models import Site, Order
from status.models import StatusGroup, Status


@pytest.fixture
def user(db):
    """Создает тестового пользователя."""
    User = get_user_model()
    return User.objects.create_user(
        username="test_user", email="test@example.com", password="test_password"
    )


@pytest.fixture
def site(db):
    """Создает тестовый сайт."""
    return Site.objects.create(
        name="Test Site",
        url="https://test.com",
        organizer_fee_percentage=Decimal("10.00"),
    )


@pytest.fixture
def status_group(db):
    """Создает группу статусов для заказов."""
    order_content_type = ContentType.objects.get_for_model(Order)
    group, _ = StatusGroup.objects.get_or_create(
        code="ORDER_STATUS_CONFIG",
        content_type=order_content_type,
        defaults={
            "name": "Статусы заказа",
            "allowed_status_transitions": {
                "new": ["paid"],
                "paid": ["refunded"],
            },
        },
    )
    return group


@pytest.fixture
def status(db, status_group):
    """Создает статус для заказов."""
    status, _ = Status.objects.get_or_create(
        code="new",
        group=status_group,
        defaults={
            "name": "Новый",
            "is_default": True,
        },
    )
    return status


@pytest.fixture
def paid_status(db, status_group):
    """Создает статус 'оплачен' для заказов."""
    status, _ = Status.objects.get_or_create(
        code="paid",
        group=status_group,
        defaults={
            "name": "Оплачен",
            "is_default": False,
        },
    )
    return status


@pytest.fixture
def user_with_balance(user):
    """Создает пользователя с балансом."""
    from balance.models import Balance, Transaction
    from balance.services.constants import TransactionTypeChoices

    # Создаем баланс для пользователя, если его нет
    balance, _ = Balance.objects.get_or_create(user=user)

    # Пополняем баланс пользователя
    Transaction.objects.create(
        balance=balance,
        amount_euro=Decimal("1000.00"),
        amount_rub=Decimal("100000.00"),
        transaction_type=TransactionTypeChoices.REPLENISHMENT,
    ).save(process_transaction=True)

    # Обновляем баланс из базы
    balance.refresh_from_db()
    return user


@pytest.fixture
def status_factory():
    """
    Фикстура для создания статусов в тестах.

    Returns:
        callable: Функция для создания статуса с заданным кодом
    """

    def _create_status(code: str) -> Status:
        # Получаем content type для модели Order
        content_type = ContentType.objects.get_for_model(Order)

        # Создаем или получаем группу статусов
        status_group, _ = StatusGroup.objects.get_or_create(
            code="ORDER_STATUS_CONFIG",
            defaults={
                "name": "Статусы заказа",
                "content_type": content_type,
                "allowed_status_transitions": {
                    "new": ["paid"],
                    "paid": ["refunded"],
                    "refunded": ["new"],
                },
            },
        )

        # Создаем или получаем статус
        status, _ = Status.objects.get_or_create(
            code=code,
            group=status_group,
            defaults={
                "name": code.capitalize(),
                "is_default": code == "new",
                "order": 10,
            },
        )

        return status

    return _create_status
