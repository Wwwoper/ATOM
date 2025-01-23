import pytest
from django.core.exceptions import ValidationError

from order.models import Order, Site
from package.models import Package, PackageOrder
from status.models import Status, StatusGroup


@pytest.fixture
def ORDER_STATUS_CONFIG_group(db):
    """Фикстура для создания группы статусов заказа."""
    return StatusGroup.objects.get(code="ORDER_STATUS_CONFIG")


@pytest.fixture
def paid_status(ORDER_STATUS_CONFIG_group):
    """Фикстура для получения статуса 'оплачен'."""
    return Status.objects.get(group=ORDER_STATUS_CONFIG_group, code="paid")


@pytest.fixture
def new_status(ORDER_STATUS_CONFIG_group):
    """Фикстура для получения статуса 'новый'."""
    return Status.objects.get(group=ORDER_STATUS_CONFIG_group, code="new")


@pytest.fixture
def test_site(db):
    """Фикстура для создания сайта."""
    return Site.objects.create(
        name="Test Site", url="http://test.com", organizer_fee_percentage=5.00
    )


@pytest.fixture
def valid_package_data(user):
    """Фикстура с валидными данными для посылки."""
    return {
        "user": user,
        "number": "TEST-001",
        "shipping_cost_eur": 10.00,
        "fee_cost_eur": 5.00,
        "comment": "Test package",
    }


@pytest.fixture
def order(db, user, paid_status, test_site):
    """Фикстура для создания оплаченного заказа."""
    return Order.objects.create(
        user=user,
        status=paid_status,
        site=test_site,
        internal_number="TEST-001",
        external_number="EXT-001",
        amount_euro=100.00,
        amount_rub=10000.00,
    )


@pytest.fixture
def unpaid_order(db, user, new_status, test_site):
    """Фикстура для создания неоплаченного заказа."""
    return Order.objects.create(
        user=user,
        status=new_status,
        site=test_site,
        internal_number="TEST-002",
        external_number="EXT-002",
        amount_euro=100.00,
        amount_rub=10000.00,
    )


@pytest.mark.django_db
class TestPackageOrder:
    """Тесты для модели PackageOrder."""

    def test_create_package_order(self, valid_package_data, order):
        """Тест создания связи заказа с посылкой."""
        package = Package.objects.create(**valid_package_data)
        package_order = PackageOrder.objects.create(package=package, order=order)

        assert package_order.package == package
        assert package_order.order == order
        assert package_order.created_at is not None

    def test_unpaid_order_validation(self, valid_package_data, unpaid_order):
        """Тест запрета добавления неоплаченного заказа."""
        package = Package.objects.create(**valid_package_data)

        with pytest.raises(ValidationError) as exc_info:
            PackageOrder.objects.create(package=package, order=unpaid_order)
        assert "Можно добавлять только оплаченные заказы" in str(exc_info.value)

    def test_unique_package_order(self, valid_package_data, order):
        """Тест уникальности связи заказа с посылкой."""
        package = Package.objects.create(**valid_package_data)

        # Создаем первую связь
        PackageOrder.objects.create(package=package, order=order)

        # Пытаемся создать дубликат
        with pytest.raises(ValidationError) as exc_info:
            package_order = PackageOrder(package=package, order=order)
            package_order.full_clean()

        error_dict = exc_info.value.message_dict
        assert (
            "Связь с заказами с такими значениями полей Посылка и Заказ уже существует."
            in error_dict["__all__"][0]
        )

    def test_str_method(self, valid_package_data, order):
        """Тест строкового представления."""
        package = Package.objects.create(**valid_package_data)
        package_order = PackageOrder.objects.create(package=package, order=order)
        expected = f"Связь с заказом {order.id}"
        assert str(package_order) == expected
