import os
import django
import pytest
from django.conf import settings
from decimal import Decimal

from django.apps import apps


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "atom.settings")
django.setup()


@pytest.fixture(scope="session")
def django_db_setup():
    """Настройка базы данных для тестов."""
    settings.DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        # "NAME": "file::memory:?cache=shared",
        "NAME": "test_db.sqlite3",  # Используем файловую БД
        "OPTIONS": {
            "timeout": 60,
            "isolation_level": None,
        },
    }


# Импортируем модели после настройки Django
from balance.models import Balance
from user.services import UserService
from django.contrib.auth import get_user_model
from status.models import Status, StatusGroup
from balance.services.constants import TransactionTypeChoices
from django.contrib.contenttypes.models import ContentType
from status.services.initial_data import (
    ORDER_STATUS_CONFIG,
    DELIVERY_STATUS_CONFIG,
)

User = get_user_model()


@pytest.fixture
def user(db):
    """Создание пользователя для тестов."""
    import uuid

    unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    return UserService.create_user(
        username=f"test_user_{uuid.uuid4().hex[:8]}",
        email=unique_email,
        password="test_password",
    )


@pytest.fixture
def new_user(db):
    """Создание пользователя для тестов."""
    return User.objects.create(
        username="test_user2", email="test2@example.com", password="test_password"
    )


@pytest.fixture
def balance(db, user):
    """Создание баланса для тестов."""
    balance = Balance.objects.get(user=user)
    # Устанавливаем курс обмена
    Balance.objects.filter(id=balance.id).update(
        average_exchange_rate=Decimal("100.00")
    )
    balance.refresh_from_db()
    return balance


@pytest.fixture
def balance_with_money(db, balance):
    """Создание баланса с начальными средствами для тестов."""
    balance.balance_euro = Decimal("1000.00")  # Увеличиваем начальный баланс
    balance.balance_rub = Decimal("100000.00")  # Увеличиваем начальный баланс
    balance.save(allow_balance_update=True)
    return balance


"""Фикстуры для тестов статусов."""


@pytest.fixture
def content_type_model():
    """Фикстура для получения ContentType тестовой модели."""
    Order = apps.get_model("order", "Order")
    return ContentType.objects.get_for_model(Order)


@pytest.fixture
def status_group(db, content_type_model):
    """Фикстура для создания группы статусов."""
    return StatusGroup.objects.create(
        name="Тестовая группа",
        code="test_group",
        content_type=content_type_model,
        allowed_status_transitions={
            "new": ["paid"],
            "paid": ["refunded"],
            "refunded": ["new"],
        },
        transaction_type_by_status={
            "paid": TransactionTypeChoices.EXPENSE.value,
            "refunded": TransactionTypeChoices.PAYBACK.value,
        },
    )


@pytest.fixture
def status(db, status_group):
    """Фикстура для создания статуса."""
    return Status.objects.create(
        group=status_group,
        code="new",
        name="Новый",
        description="Тестовый статус",
        is_default=True,
        order=10,
    )


@pytest.fixture
def site(db):
    """Создание сайта для тестов."""
    import uuid
    from order.models import Site
    from decimal import Decimal

    unique_url = f"https://test-{uuid.uuid4().hex[:8]}.com"
    return Site.objects.create(
        name="Test Site",
        url=unique_url,  # Используем уникальный URL
        organizer_fee_percentage=Decimal("10.00"),
    )


@pytest.fixture
def order(db, user, site, status, balance):
    """Фикстура для создания тестового заказа."""
    from order.models import Order

    return Order.objects.create(
        user=user,
        site=site,
        status=status,
        internal_number="TEST001",
        external_number="EXT001",
        amount_euro=Decimal("100.00"),
        amount_rub=Decimal("15000.00"),
        expense=Decimal("0.00"),
        profit=Decimal("0.00"),
    )


@pytest.fixture
def paid_order(db, user, site, balance):
    """Фикстура ля создания оплаченного заказа."""
    from order.models import Order
    from status.models import Status

    paid_status = Status.objects.get(code="paid", group__code="ORDER_STATUS_CONFIG")
    return Order.objects.create(
        user=user,
        site=site,
        status=paid_status,
        internal_number="TEST002",
        external_number="EXT002",
        amount_euro=Decimal("100.00"),
        amount_rub=Decimal("10000.00"),
        expense=Decimal("90.00"),
        profit=Decimal("10.00"),
    )


@pytest.fixture
def order_status_group(db, content_type_model):
    """Фикстура для создания группы статусов заказа."""
    from status.models import StatusGroup

    config = ORDER_STATUS_CONFIG["ORDER_STATUS_CONFIG"]

    status_group, _ = StatusGroup.objects.get_or_create(
        code="ORDER_STATUS_CONFIG",
        content_type=content_type_model,
        defaults={
            "name": config["name"],
            "allowed_status_transitions": config["allowed_status_transitions"],
            "transaction_type_by_status": config["transaction_type_by_status"],
        },
    )
    return status_group


@pytest.fixture
def statuses(db, ORDER_STATUS_CONFIG_group):
    """Фикстура для создания всех статусов заказа."""
    from status.models import Status

    statuses = {"order": {}}
    config = ORDER_STATUS_CONFIG["ORDER_STATUS_CONFIG"]["status"]

    # Создаем статусы из конфигурации
    for status_config in config:
        status, _ = Status.objects.get_or_create(
            code=status_config["code"],
            group=ORDER_STATUS_CONFIG_group,
            defaults={
                "name": status_config["name"],
                "description": status_config["description"],
                "is_default": status_config.get("is_default", False),
                "order": status_config["order"],
            },
        )
        statuses["order"][status_config["code"]] = status

    return statuses


@pytest.fixture
def delivery_status_group(db, content_type_model):
    """Фикстура для создания статуса доставки."""
    from status.models import Status, StatusGroup
    from balance.services.constants import TransactionTypeChoices
    from package.models import PackageDelivery
    from django.contrib.contenttypes.models import ContentType

    # Получаем правильный ContentType для модели PackageDelivery
    content_type = ContentType.objects.get_for_model(PackageDelivery)

    status_group, _ = StatusGroup.objects.get_or_create(
        code="DELIVERY_STATUS_CONFIG",
        content_type=content_type,  # Используем ContentType для PackageDelivery
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

    status, _ = Status.objects.get_or_create(
        code="new",
        group=status_group,
        defaults={
            "name": "Новая",
            "description": "Новая доставка",
            "is_default": True,
            "order": 10,
        },
    )
    return status


@pytest.fixture
def paid_delivery_status(db, delivery_status_group):
    """Фикстура для создания статуса оплаченной доставки."""
    from status.models import Status

    status, _ = Status.objects.get_or_create(
        code="paid",
        group=delivery_status_group,
        defaults={
            "name": "Оплачена",
            "description": "Доставка оплачена",
            "is_default": False,
            "order": 20,
        },
    )
    return status


@pytest.fixture
def cancelled_delivery_status(db, delivery_status_group):
    """Фикстура для создания статуса отмененной доставки."""
    from status.models import Status

    status, _ = Status.objects.get_or_create(
        code="cancelled",
        group=delivery_status_group,
        defaults={
            "name": "Отменена",
            "description": "Доставка отменена",
            "is_default": False,
            "order": 90,
        },
    )
    return status


@pytest.fixture
def reexport_delivery_status(db, delivery_status_group):
    """Фикстура для создания статуса реэкспорта доставки."""
    from status.models import Status

    status, _ = Status.objects.get_or_create(
        code="reexport",
        group=delivery_status_group,
        defaults={
            "name": "Реэкспорт",
            "description": "Доставка отправлена на реэкспорт",
            "is_default": False,
            "order": 40,
        },
    )
    return status
