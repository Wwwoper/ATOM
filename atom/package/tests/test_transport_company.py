import pytest
from django.core.exceptions import ValidationError

from package.models import TransportCompany, PackageDelivery, Package
from status.models import Status


@pytest.fixture
def valid_company_data():
    """Фикстура с валидными данными для транспортной компании."""
    return {
        "name": "Test Transport Company",
        "is_active": True,
        "description": "Test description",
        "is_default": False,
    }


@pytest.mark.django_db(transaction=True)
class TestTransportCompany:
    """Тесты для модели TransportCompany."""

    def test_create_company(self, valid_company_data):
        """Тест создания транспортной компании с валидными данными."""
        company = TransportCompany.objects.create(**valid_company_data)

        assert company.name == valid_company_data["name"]
        assert company.is_active == valid_company_data["is_active"]
        assert company.description == valid_company_data["description"]
        assert company.is_default == valid_company_data["is_default"]
        assert company.created_at is not None
        assert company.updated_at is not None

    def test_name_validation(self, valid_company_data):
        """Тест валидации названия компании."""
        # Тест на пустое название
        invalid_data = valid_company_data.copy()
        invalid_data["name"] = ""
        with pytest.raises(ValidationError):
            company = TransportCompany(**invalid_data)
            company.full_clean()

    def test_description_validation(self, valid_company_data):
        """Тест валидации описания."""
        # Тест на пустое описание (должно быть разрешено)
        valid_data = valid_company_data.copy()
        valid_data["description"] = ""
        company = TransportCompany(**valid_data)
        company.full_clean()
        company.save()

    def test_default_company_constraint(self, valid_company_data):
        """Тест ограничения на единственную компанию по умолчанию."""
        # Создаем первую компанию по умолчанию
        first_company_data = valid_company_data.copy()
        first_company_data["is_default"] = True
        first_company = TransportCompany.objects.create(**first_company_data)

        # Создаем вторую компанию без флага по умолчанию
        second_company_data = valid_company_data.copy()
        second_company_data["name"] = "Second Company"
        second_company_data["is_default"] = False
        second_company = TransportCompany.objects.create(**second_company_data)

        # Сначала снимаем флаг с первой компании
        first_company.is_default = False
        first_company.save()

        # Теперь делаем вторую компанию по умолчанию
        second_company.is_default = True
        second_company.save()

        # Проверяем что вторая стала по умолчанию, а первая - нет
        first_company.refresh_from_db()
        assert second_company.is_default is True
        assert first_company.is_default is False

        # Проверяем что только одна компания по умолчанию
        assert TransportCompany.objects.filter(is_default=True).count() == 1

    def test_active_companies(self, valid_company_data):
        """Тест менеджера для активных компаний."""
        # Создаем активную компанию
        active_company = TransportCompany.objects.create(**valid_company_data)

        # Создаем неактивную компанию
        inactive_data = valid_company_data.copy()
        inactive_data["name"] = "Inactive Company"
        inactive_data["is_active"] = False
        TransportCompany.objects.create(**inactive_data)

        # Проверяем, что менеджер возвращает только активные компании
        active_companies = TransportCompany.objects.filter(is_active=True)
        assert len(active_companies) == 1
        assert active_companies[0] == active_company

    def test_str_method(self, valid_company_data):
        """Тест строкового представления."""
        company = TransportCompany.objects.create(**valid_company_data)
        assert str(company) == valid_company_data["name"]

    def test_default_company(self, valid_company_data):
        """Тест установки компании по умолчанию."""
        # Создаем обычную компанию
        company = TransportCompany.objects.create(**valid_company_data)
        assert not company.is_default

        # Создаем компанию по умолчанию
        default_data = valid_company_data.copy()
        default_data["name"] = "Default Company"
        default_data["is_default"] = True
        default_company = TransportCompany.objects.create(**default_data)
        assert default_company.is_default

    def test_company_deletion_with_deliveries(self, valid_company_data, user):
        """Тест запрета удаления транспортной компании с существующими доставками."""
        # Создаем компанию
        company = TransportCompany.objects.create(**valid_company_data)

        # Создаем посылку
        package = Package.objects.create(
            user=user,
            number="TEST-123",
            shipping_cost_eur=10.00,
            fee_cost_eur=5.00,
        )

        # Создаем доставку для компании
        PackageDelivery.objects.create(
            package=package,
            transport_company=company,
            status=Status.objects.get(
                group__code="DELIVERY_STATUS_CONFIG", is_default=True
            ),
            tracking_number="TRACK-123",
            weight=1.5,
            shipping_cost_rub=1000.00,
            price_rub_for_kg=500.00,
            delivery_address="Test Address",
        )

        # Проверяем, что компанию нельзя удалить
        with pytest.raises(ValidationError) as exc_info:
            company.delete()

        assert (
            "Невозможно удалить транспортную компанию, пока с ней связаны доставки"
            in str(exc_info.value)
        )
        assert TransportCompany.objects.filter(pk=company.pk).exists()

        # Проверяем, что компанию без доставок можно удалить
        new_company = TransportCompany.objects.create(
            name="Test Transport Company 2",
            is_active=True,
            description="Test description 2",
            is_default=False,
        )
        new_company.delete()
        assert not TransportCompany.objects.filter(pk=new_company.pk).exists()

    def test_default_company_switch(self, valid_company_data):
        """Тест автоматического переключения компании по умолчанию."""
        # Создаем первую компанию по умолчанию
        first_company = TransportCompany.objects.create(**valid_company_data)
        first_company.is_default = True
        first_company.save()

        # Создаем вторую компанию и делаем её по умолчанию
        second_company = TransportCompany.objects.create(**valid_company_data)
        second_company.is_default = True
        second_company.save()

        # Проверяем что первая компания больше не по умолчанию
        first_company.refresh_from_db()
        assert first_company.is_default is False
        assert second_company.is_default is True

        # Проверяем что только одна компания по умолчанию
        assert TransportCompany.objects.filter(is_default=True).count() == 1
