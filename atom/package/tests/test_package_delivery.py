import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone

from package.models import Package, PackageDelivery, TransportCompany
from status.models import Status, StatusGroup
from balance.services.constants import TransactionTypeChoices
from balance.models import Transaction


@pytest.fixture
def delivery_status_group(db):
    """Фикстура для создания группы статусов доставки."""
    return StatusGroup.objects.get(code="delivery_status")


@pytest.fixture
def new_status(delivery_status_group):
    """Фикстура для получения статуса 'новый'."""
    return Status.objects.get(group=delivery_status_group, code="new")


@pytest.fixture
def paid_status(delivery_status_group):
    """Фикстура для получения статуса 'оплачен'."""
    return Status.objects.get(group=delivery_status_group, code="paid")


@pytest.fixture
def transport_company(db):
    """Фикстура для создания транспортной компании."""
    return TransportCompany.objects.create(name="Test Company", is_active=True)


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
def transaction(user):
    """Фикстура для создания тестовой транзакции."""
    transaction = Transaction.objects.create(
        balance=user.balance,
        amount_euro=Decimal("1000.00"),
        amount_rub=Decimal("100000.00"),
        transaction_type=TransactionTypeChoices.REPLENISHMENT,
    )
    # Сохраняем без обработки транзакции
    transaction.save(process_transaction=False)
    return transaction


@pytest.fixture
def valid_delivery_data(valid_package_data, transport_company, new_status, transaction):
    """Фикстура с валидными данными для доставки."""
    package = Package.objects.create(**valid_package_data)
    return {
        "package": package,
        "transport_company": transport_company,
        "tracking_number": "TRACK-001",
        "shipping_cost_rub": Decimal("1000.00"),
        "weight": Decimal("1.00"),
        "price_rub_for_kg": Decimal("500.00"),
        "status": new_status,
    }


@pytest.mark.django_db
class TestPackageDelivery:
    """Тесты для модели PackageDelivery."""

    def test_create_delivery(self, valid_delivery_data):
        """Тест создания доставки с валидными данными."""
        delivery = PackageDelivery.objects.create(**valid_delivery_data)

        assert delivery.package == valid_delivery_data["package"]
        assert delivery.transport_company == valid_delivery_data["transport_company"]
        assert delivery.tracking_number == valid_delivery_data["tracking_number"]
        assert delivery.shipping_cost_rub == valid_delivery_data["shipping_cost_rub"]
        assert delivery.weight == valid_delivery_data["weight"]
        assert delivery.price_rub_for_kg == valid_delivery_data["price_rub_for_kg"]
        assert delivery.status == valid_delivery_data["status"]
        assert delivery.created_at is not None

    def test_cost_validation(self, valid_delivery_data):
        """Тест валидации стоимости."""
        # Тест на отрицательную стоимость доставки
        invalid_data = valid_delivery_data.copy()
        invalid_data["shipping_cost_rub"] = Decimal("-1000.00")
        with pytest.raises(ValidationError):
            delivery = PackageDelivery(**invalid_data)
            delivery.full_clean()

        # Тест на отрицательную стоимость за кг
        invalid_data = valid_delivery_data.copy()
        invalid_data["price_rub_for_kg"] = Decimal("-500.00")
        with pytest.raises(ValidationError):
            delivery = PackageDelivery(**invalid_data)
            delivery.full_clean()

        # Тест на отрицательный вес
        invalid_data = valid_delivery_data.copy()
        invalid_data["weight"] = Decimal("-1.00")
        with pytest.raises(ValidationError):
            delivery = PackageDelivery(**invalid_data)
            delivery.full_clean()

    def test_tracking_number_validation(self, valid_delivery_data):
        """Тест валидации номера отслеживания."""
        # Тест на пустой номер
        invalid_data = valid_delivery_data.copy()
        invalid_data["tracking_number"] = ""
        with pytest.raises(ValidationError):
            delivery = PackageDelivery(**invalid_data)
            delivery.full_clean()

        # Тест на очистку пробелов
        valid_data = valid_delivery_data.copy()
        valid_data["tracking_number"] = " TRACK-001 "
        delivery = PackageDelivery.objects.create(**valid_data)
        assert delivery.tracking_number == "TRACK-001"

    def test_paid_delivery_deletion(self, valid_delivery_data, paid_status):
        """Тест запрета удаления оплаченной доставки."""
        delivery = PackageDelivery.objects.create(**valid_delivery_data)

        # Меняем статус на оплачен
        delivery.status = paid_status
        delivery.save()

        # Проверяем, что нельзя удалить оплаченную доставку
        with pytest.raises(ValidationError) as exc_info:
            delivery.delete()
        assert "Невозможно удалить доставку с оплаченным статусом" in str(
            exc_info.value
        )

    def test_paid_delivery_cost_update(self, valid_delivery_data, paid_status):
        """Тест запрета изменения стоимости оплаченной доставки."""
        delivery = PackageDelivery.objects.create(**valid_delivery_data)

        # Меняем статус на оплачен, пропуская обработку статуса
        delivery.status = paid_status
        delivery.paid_at = timezone.now()
        delivery.save(skip_status_processing=True)

        # Пытаемся изменить стоимость
        delivery.shipping_cost_rub = Decimal("2000.00")
        delivery.save()

        # Проверяем, что стоимость не изменилась
        delivery.refresh_from_db()
        assert delivery.shipping_cost_rub == valid_delivery_data["shipping_cost_rub"]

    def test_str_method(self, valid_delivery_data):
        """Тест строкового представления."""
        delivery = PackageDelivery.objects.create(**valid_delivery_data)
        expected = f"Доставка посылки {delivery.package.number}"
        assert str(delivery) == expected

    def test_delivery_address(self, valid_delivery_data):
        """Тест поля адреса доставки."""
        # Тест с пустым адресом (должно быть разрешено)
        delivery = PackageDelivery.objects.create(**valid_delivery_data)
        assert delivery.delivery_address == ""

        # Тест с заполненным адресом
        delivery.delivery_address = "Test Address, 123"
        delivery.save()
        delivery.refresh_from_db()
        assert delivery.delivery_address == "Test Address, 123"

    def test_paid_at_field(self, valid_delivery_data, paid_status):
        """Тест поля даты оплаты."""
        delivery = PackageDelivery.objects.create(**valid_delivery_data)
        assert delivery.paid_at is None

        # Устанавливаем статус оплачен
        current_time = timezone.now()
        delivery.status = paid_status
        delivery.paid_at = current_time
        delivery.save()

        delivery.refresh_from_db()
        assert delivery.paid_at == current_time

    def test_unique_package_delivery(self, valid_delivery_data):
        """Тест уникальности доставки для посылки."""
        # Создаем первую доставку
        PackageDelivery.objects.create(**valid_delivery_data)

        # Пытаемся создать вторую доставку для той же посылки
        with pytest.raises(ValidationError) as exc_info:
            delivery = PackageDelivery(**valid_delivery_data)
            delivery.full_clean()

        error_dict = exc_info.value.message_dict
        assert "Для этой посылки уже существует доставка" in error_dict["package"]

    def test_paid_delivery_status_change(
        self, valid_delivery_data, paid_status, new_status
    ):
        """Тест запрета изменения статуса оплаченной доставки."""
        delivery = PackageDelivery.objects.create(**valid_delivery_data)

        # Меняем статус на оплачен, пропуская обработку статуса
        delivery.status = paid_status
        delivery.paid_at = timezone.now()
        delivery.save(skip_status_processing=True)

        # Пытаемся изменить статус обратно на новый
        delivery.status = new_status
        with pytest.raises(ValidationError) as exc_info:
            delivery.full_clean()  # Проверяем валидацию до сохранения

        assert "Невозможно изменить статус оплаченной доставки" in str(exc_info.value)
