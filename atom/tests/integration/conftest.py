"""
Фикстуры для интеграционных тестов.

Содержит фикстуры для:
- Создания тестовых пользователей и балансов
- Создания тестовых сайтов и транспортных компаний
- Настройки статусов и групп статусов
- Установки начальных балансов и курсов обмена
"""

import pytest
from decimal import Decimal
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command

from status.models import StatusGroup, Status
from package.models import TransportCompany, PackageDelivery
from user.services import UserService
from order.models import Order, Site as OrderSite
from balance.models import Transaction
from balance.services.transaction_service import TransactionProcessor
from balance.services.constants import TransactionTypeChoices


@pytest.fixture(scope="function", autouse=True)
def clean_tables(django_db_setup, db):
    """
    Очистка таблиц перед каждым тестом.

    Удаляет данные из всех связанных таблиц в правильном порядке,
    чтобы избежать проблем с внешними ключами.
    """
    from order.models import Order
    from package.models import Package, PackageDelivery, PackageOrder
    from balance.models import Transaction

    # Проверяем начальное состояние
    print(f"Orders before cleanup: {Order.objects.count()}")

    # Очищаем все связанные таблицы в правильном порядке
    PackageDelivery.objects.all().delete()
    PackageOrder.objects.all().delete()
    Package.objects.all().delete()
    Transaction.objects.all().delete()
    Order.objects.all().delete()

    # Проверяем что очистка сработала
    print(f"Orders after cleanup: {Order.objects.count()}")


@pytest.fixture
def user_with_balance(db):
    """Создает пользователя с начальным балансом через UserService."""
    print("\nCreating user_with_balance")
    user_service = UserService()
    user = user_service.create_user(
        username="test_user", email="test@example.com", password="test_password"
    )
    return user


@pytest.fixture
def zara_site(db):
    """
    Создает тестовый сайт Zara.

    Returns:
        OrderSite: Сайт для заказов с настроенной комиссией
    """
    print("\nCreating zara_site")
    return OrderSite.objects.create(
        name="Zara",
        url="https://www.zara.com",
        organizer_fee_percentage=Decimal("10.00"),
        description="Test Zara site",
    )


@pytest.fixture
def default_transport_company(db):
    """
    Создает транспортную компанию по умолчанию.

    Returns:
        TransportCompany: Транспортная компания
    """
    return TransportCompany.objects.create(
        name="Test Transport",
        is_active=True,
        is_default=True,
        description="Test transport company",
    )


@pytest.fixture
def status_groups(db):
    """Создает группы статусов для заказов и доставок."""
    # Получаем ContentType для моделей
    order_content_type = ContentType.objects.get_for_model(Order)
    delivery_content_type = ContentType.objects.get_for_model(PackageDelivery)

    # Создаем группу статусов для заказов
    order_group, _ = StatusGroup.objects.get_or_create(
        code="ORDER_STATUS_CONFIG",
        content_type=order_content_type,
        defaults={
            "name": "Статусы заказа",
            "allowed_status_transitions": {
                "new": ["paid"],
                "paid": ["refunded"],
                "refunded": ["new"],
            },
            "transaction_type_by_status": {
                "paid": TransactionTypeChoices.EXPENSE.value,
                "refunded": TransactionTypeChoices.PAYBACK.value,
            },
        },
    )

    # Создаем группу статусов для доставок
    delivery_group, _ = StatusGroup.objects.get_or_create(
        code="DELIVERY_STATUS_CONFIG",
        content_type=delivery_content_type,
        defaults={
            "name": "Статусы доставки",
            "allowed_status_transitions": {
                "new": ["paid"],
                "paid": ["cancelled"],
                "cancelled": ["new"],
            },
            "transaction_type_by_status": {
                "paid": TransactionTypeChoices.EXPENSE.value,
                "cancelled": TransactionTypeChoices.PAYBACK.value,
            },
        },
    )

    return order_group, delivery_group


@pytest.fixture
def statuses(status_groups):
    """
    Создает все необходимые статусы для заказов и доставок.

    Args:
        status_groups: Фикстура с группами статусов

    Returns:
        dict: Словарь со всеми созданными статусами
    """
    order_group, delivery_group = status_groups

    # Создаем статусы заказов
    ORDER_STATUS_CONFIGes = {
        "new": Status.objects.get_or_create(
            group=order_group,
            code="new",
            defaults={
                "name": "Новый",
                "description": "Новый заказ",
                "is_default": True,
                "order": 10,
            },
        )[0],
        "paid": Status.objects.get_or_create(
            group=order_group,
            code="paid",
            defaults={"name": "Оплачен", "description": "Заказ оплачен", "order": 20},
        )[0],
        "refunded": Status.objects.get_or_create(
            group=order_group,
            code="refunded",
            defaults={
                "name": "Возврат",
                "description": "Возврат средств по заказу",
                "order": 30,
            },
        )[0],
    }

    # Создаем статусы доставок
    DELIVERY_STATUS_CONFIGes = {
        "new": Status.objects.get_or_create(
            group=delivery_group,
            code="new",
            defaults={
                "name": "Новая",
                "description": "Новая доставка",
                "is_default": True,
                "order": 10,
            },
        )[0],
        "paid": Status.objects.get_or_create(
            group=delivery_group,
            code="paid",
            defaults={
                "name": "Оплачена",
                "description": "Доставка оплачена",
                "order": 20,
            },
        )[0],
        "reexport": Status.objects.get_or_create(
            group=delivery_group,
            code="reexport",
            defaults={
                "name": "Реэкспорт",
                "description": "Доставка отправлена на реэкспорт",
                "order": 40,
            },
        )[0],
        "cancelled": Status.objects.get_or_create(
            group=delivery_group,
            code="cancelled",
            defaults={
                "name": "Отменена",
                "description": "Доставка отменена",
                "order": 90,
            },
        )[0],
    }

    return {
        "order": ORDER_STATUS_CONFIGes,
        "delivery": DELIVERY_STATUS_CONFIGes,  # Используем DELIVERY_STATUS_CONFIGes для посылок
    }


@pytest.fixture
def initial_balance_rub():
    """Возвращает начальный баланс в рублях."""
    return Decimal("10000.00")


@pytest.fixture
def initial_balance_euro():
    """Возвращает начальный баланс в евро."""
    return Decimal("100.00")


@pytest.fixture
def exchange_rate():
    """Возвращает курс обмена."""
    return Decimal("100.00")  # 1 EUR = 100 RUB


@pytest.fixture
def user_balance(user_with_balance, initial_balance_rub, initial_balance_euro):
    """
    Пополняет баланс пользователя начальной суммой.

    Args:
        user_with_balance: Фикстура с пользователем
        initial_balance_rub: Фикстура с начальной суммой в рублях
        initial_balance_euro: Фикстура с начальной суммой в евро

    Returns:
        Balance: Баланс пользователя с установленной суммой
    """
    # Получаем существующий баланс пользователя
    balance = user_with_balance.balance

    # Создаем транзакцию пополнения
    transaction = Transaction.objects.create(
        balance=balance,
        transaction_type=TransactionTypeChoices.REPLENISHMENT.value,
        amount_euro=initial_balance_euro,  # 100 EUR
        amount_rub=initial_balance_rub,  # 10000 RUB
        comment="Начальное пополнение баланса для тестов",
    )

    # Обрабатываем транзакцию
    TransactionProcessor.execute_transaction(transaction)

    # Обновляем баланс из базы
    balance.refresh_from_db()

    return balance
