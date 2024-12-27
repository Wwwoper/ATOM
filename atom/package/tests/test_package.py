import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError

from django.db import transaction

from package.models import Package
from user.models import User


@pytest.fixture
def user(db):
    """Фикстура для создания пользователя."""
    return User.objects.create(
        username="testuser",
        email="test@example.com",
        password="testpass123",
        first_name="Test",
        last_name="User",
    )


@pytest.fixture
def valid_package_data(user):
    """Фикстура с валидными данными для посылки."""
    return {
        "user": user,
        "number": "PKG-001",
        "shipping_cost_eur": Decimal("10.00"),
        "fee_cost_eur": Decimal("2.00"),
    }


@pytest.mark.django_db
class TestPackage:
    """Тесты для модели Package."""

    def test_create_package(self, valid_package_data):
        """Тест создания посылки с валидными данными."""
        package = Package.objects.create(**valid_package_data)

        assert package.number == valid_package_data["number"]
        assert package.shipping_cost_eur == valid_package_data["shipping_cost_eur"]
        assert package.fee_cost_eur == valid_package_data["fee_cost_eur"]
        assert package.user == valid_package_data["user"]

    def test_number_validation(self, valid_package_data):
        """Тест валидации номера посылки."""
        # Тест на пустой номер
        invalid_data = valid_package_data.copy()
        invalid_data["number"] = ""
        with pytest.raises(ValidationError):
            package = Package(**invalid_data)
            package.full_clean()

        # Тест на уникальность для пользователя
        Package.objects.create(**valid_package_data)

        # Пытаемся создать дубликат
        duplicate_data = valid_package_data.copy()
        duplicate_package = Package(**duplicate_data)
        with pytest.raises(ValidationError) as exc_info:
            duplicate_package.full_clean()
        error_dict = exc_info.value.message_dict
        assert (
            "Посылка с такими значениями полей Пользователь и Номер посылки в сервисе у посредника уже существует."
            in error_dict["__all__"][0]
        )

        # Тест на возможность использования того же номера другим пользователем
        another_user = User.objects.create(
            username="anotheruser",
            email="another@example.com",
            password="testpass123",
            first_name="Another",
            last_name="User",
        )
        valid_data = valid_package_data.copy()
        valid_data["user"] = another_user
        valid_data["number"] = "PKG-002"
        Package.objects.create(**valid_data)

    def test_cost_validation(self, valid_package_data):
        """Тест валидации стоимости."""
        # Тест на отрицательную стоимость доставки
        invalid_data = valid_package_data.copy()
        invalid_data["shipping_cost_eur"] = Decimal("-10.00")
        with pytest.raises(ValidationError):
            package = Package(**invalid_data)  # Создаем объект без сохранения
            package.full_clean()

        # Тест на отрицательную стоимость комиссии
        invalid_data = valid_package_data.copy()
        invalid_data["fee_cost_eur"] = Decimal("-2.00")
        with pytest.raises(ValidationError):
            package = Package(**invalid_data)  # Создаем объект без сохранения
            package.full_clean()

        # Тест на нулевую стоимость (должно быть разрешено)
        valid_data = valid_package_data.copy()
        valid_data["shipping_cost_eur"] = Decimal("0.00")
        valid_data["fee_cost_eur"] = Decimal("0.00")
        package = Package(**valid_data)  # Создаем объект без сохранения
        package.full_clean()  # Не должно вызывать ошибку
        package.save()  # Сохраняем после успешной валидации

    def test_total_cost_property(self, valid_package_data):
        """Тест расчета общей стоимости."""
        # Создаем посылку с известными значениями
        package = Package.objects.create(
            user=valid_package_data["user"],
            number="PKG-TEST",
            shipping_cost_eur=Decimal("10.50"),
            fee_cost_eur=Decimal("2.50"),
        )

        # Проверяем расчет общей стоимости
        assert package.total_cost_eur == Decimal("13.00")

        # Проверяем при нулевых значениях
        package.shipping_cost_eur = Decimal("0.00")
        package.fee_cost_eur = Decimal("0.00")
        package.save()

        assert package.total_cost_eur == Decimal("0.00")

    def test_package_with_delivery_deletion(self, valid_package_data):
        """Тест запрета удаления посылки с существую��ей доставкой."""
        from package.models import PackageDelivery, TransportCompany
        from status.models import Status, StatusGroup

        # Создаем посылку
        package = Package.objects.create(**valid_package_data)

        # Создаем транспортную компанию
        company = TransportCompany.objects.create(name="Test Company", is_active=True)

        # Получаем статус для доставки
        status_group = StatusGroup.objects.get(code="delivery_status")
        status = Status.objects.get(group=status_group, code="new")

        # Создаем доставку для посылки
        delivery = PackageDelivery.objects.create(
            package=package,
            transport_company=company,
            tracking_number="TRACK-001",
            shipping_cost_rub=Decimal("1000.00"),
            weight=Decimal("1.00"),
            price_rub_for_kg=Decimal("500.00"),
            status=status,
        )

        # Проверяем, что нельзя удалить посылку с доставкой
        with pytest.raises(ValidationError) as exc_info:
            package.delete()
        error_dict = exc_info.value.message_dict
        assert (
            "Невозможно удалить посылку с существующей доставкой"
            in error_dict["package"][0]
        )

        # Проверяем, что посылка не была удалена
        assert Package.objects.filter(id=package.id).exists()

        # Удаляем доставку
        delivery.delete()

        # Обновляем объект из базы
        package.refresh_from_db()

        # Теперь посылку можно удалить
        package.delete()
        assert not Package.objects.filter(id=package.id).exists()

    def test_str_method(self, valid_package_data):
        """Тест строкового представления."""
        package = Package.objects.create(**valid_package_data)
        expected = f"Посылка {package.number}"
        assert str(package) == expected
        assert str(package) == expected
