import pytest
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError
from django.db import transaction

from status.models import StatusGroup, Status
from order.models import Order
from package.models import Package


@pytest.mark.django_db
class TestStatusGroup:
    """Тесты для модели StatusGroup."""

    @pytest.fixture
    def valid_status_group_data(self):
        """Фикстура с валидными данными для группы статусов."""
        return {
            "name": "Тестовая группа",
            "code": "test_group",
            "allowed_status_transitions": {
                "new": ["paid", "cancelled"],
                "paid": ["refunded"],
                "cancelled": ["new"],
                "refunded": ["new"],
            },
            "transaction_type_by_status": {"paid": "EXPENSE", "refunded": "PAYBACK"},
        }

    @pytest.fixture
    def order_content_type(self):
        """Фикстура для получения ContentType модели Order."""
        return ContentType.objects.get_for_model(Order)

    def test_create_status_group(self, valid_status_group_data, order_content_type):
        """Тест создания группы статусов с валидными данными."""
        valid_status_group_data["content_type"] = order_content_type
        status_group = StatusGroup.objects.create(**valid_status_group_data)

        assert status_group.pk is not None
        assert status_group.name == valid_status_group_data["name"]
        assert status_group.code == valid_status_group_data["code"]
        assert (
            status_group.allowed_status_transitions
            == valid_status_group_data["allowed_status_transitions"]
        )
        assert (
            status_group.transaction_type_by_status
            == valid_status_group_data["transaction_type_by_status"]
        )

    def test_unique_constraints(self, valid_status_group_data, order_content_type):
        """Тест уникальности code и code+content_type."""
        # Добавляем content_type в данные
        valid_status_group_data["content_type"] = order_content_type

        # Создаем первую группу
        StatusGroup.objects.create(**valid_status_group_data)

        # Проверяем уникальность code
        duplicate = StatusGroup(**valid_status_group_data)
        with pytest.raises(ValidationError) as exc_info:
            duplicate.full_clean()
        assert "code" in exc_info.value.message_dict

        # Создаем новую группу с тем же кодом, но для другого content_type
        package_content_type = ContentType.objects.get_for_model(Package)

        # Создаем новый объект с другим content_type и другим кодом
        new_group_data = valid_status_group_data.copy()
        new_group_data["content_type"] = package_content_type
        new_group_data["code"] = "test_group_package"  # Меняем код для уникальности
        new_group = StatusGroup.objects.create(**new_group_data)

        # Пытаемся создать дубликат для того же content_type
        with pytest.raises(ValidationError) as exc_info:
            duplicate = StatusGroup(**new_group_data)
            duplicate.full_clean()
        assert "code" in exc_info.value.message_dict

    def test_status_transitions(self, valid_status_group_data, order_content_type):
        """Тест переходов между статусами."""
        # Добавляем content_type в данные
        valid_status_group_data["content_type"] = order_content_type
        status_group = StatusGroup.objects.create(**valid_status_group_data)

        # Проверяем разрешенные переходы
        assert status_group.is_transition_allowed("new", "paid")
        assert status_group.is_transition_allowed("paid", "refunded")

        # Проверяем запрещенные переходы
        assert not status_group.is_transition_allowed("new", "refunded")
        assert not status_group.is_transition_allowed("cancelled", "paid")

        # Проверяем несуществующие статусы
        assert not status_group.is_transition_allowed("new", "non_existent")
        assert not status_group.is_transition_allowed("non_existent", "paid")

    def test_transaction_types(self, valid_status_group_data, order_content_type):
        """Тест получения типов транзакций."""
        # Добавляем content_type в данные
        valid_status_group_data["content_type"] = order_content_type
        status_group = StatusGroup.objects.create(**valid_status_group_data)

        # Проверяем статусы с транзакциями
        assert status_group.transaction_type_by_status.get("paid") == "EXPENSE"
        assert status_group.transaction_type_by_status.get("refunded") == "PAYBACK"

        # Проверяем статусы без транзакций
        assert status_group.transaction_type_by_status.get("new") is None
        assert status_group.transaction_type_by_status.get("cancelled") is None

        # Проверяем несуществующие статусы
        assert status_group.transaction_type_by_status.get("non_existent") is None

    def test_str_method(self, valid_status_group_data, order_content_type):
        """Тест строкового представления."""
        # Добавляем content_type в данные
        valid_status_group_data["content_type"] = order_content_type
        status_group = StatusGroup.objects.create(**valid_status_group_data)

        expected = status_group.name
        assert str(status_group) == expected
