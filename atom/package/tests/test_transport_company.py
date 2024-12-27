import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from package.models import TransportCompany


@pytest.fixture
def valid_company_data():
    """Фикстура с валидными данными для транспортной компании."""
    return {
        "name": "Test Transport Company",
        "is_active": True,
        "description": "Test description",
        "is_default": False,
    }


@pytest.mark.django_db
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
        default_data = valid_company_data.copy()
        default_data["is_default"] = True
        TransportCompany.objects.create(**default_data)

        # Пытаемся создать вторую компанию по умолчанию
        second_default_data = valid_company_data.copy()
        second_default_data["name"] = "Second Default Company"
        second_default_data["is_default"] = True

        with pytest.raises(IntegrityError):
            TransportCompany.objects.create(**second_default_data)

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
