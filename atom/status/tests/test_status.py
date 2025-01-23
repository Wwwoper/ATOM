"""Тесты для модели Status."""

import pytest
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType

from status.models import Status, StatusGroup
from order.models import Order


@pytest.mark.django_db
class TestStatus:
    """Тесты для модели Status."""

    @pytest.fixture
    def order_content_type(self):
        """Фикстура для получения ContentType модели Order."""
        return ContentType.objects.get_for_model(Order)

    @pytest.fixture
    def status_group(self, order_content_type):
        """Фикстура для создания группы статусов."""
        return StatusGroup.objects.create(
            name="Тестовая группа",
            code="test_group",
            content_type=order_content_type,
            allowed_status_transitions={
                "new": ["paid", "cancelled"],
                "paid": ["refunded"],
            },
            transaction_type_by_status={"paid": "EXPENSE", "refunded": "PAYBACK"},
        )

    @pytest.fixture
    def valid_status_data(self, status_group):
        """Фикстура с валидными данными для статуса."""
        return {
            "name": "Новый",
            "code": "new",
            "group": status_group,
            "order": 1,
            "is_default": True,
            "description": "Описание статуса",
        }

    def test_create_status(self, valid_status_data):
        """Тест создания статуса с валидными данными."""
        status = Status.objects.create(**valid_status_data)

        assert status.pk is not None
        assert status.name == valid_status_data["name"]
        assert status.code == valid_status_data["code"]
        assert status.group == valid_status_data["group"]
        assert status.order == valid_status_data["order"]
        assert status.is_default == valid_status_data["is_default"]

    def test_unique_constraints(
        self, valid_status_data, status_group, order_content_type
    ):
        """Тест уникальности code в пределах группы."""
        Status.objects.create(**valid_status_data)

        # Пытаемся создать статус с тем же кодом в той же группе
        with pytest.raises(ValidationError):
            duplicate = Status(**valid_status_data)
            duplicate.full_clean()

        # Создаем новую группу и проверяем, что можно создать статус с тем же кодом
        new_group = StatusGroup.objects.create(
            name="Другая группа", code="other_group", content_type=order_content_type
        )
        valid_status_data["group"] = new_group
        Status.objects.create(**valid_status_data)

    def test_default_status(self, valid_status_data, status_group):
        """Тест флага is_default."""
        # Создаем первый статус по умолчанию
        status1 = Status.objects.create(**valid_status_data)
        assert status1.is_default

        # Создаем второй статус по умолчанию
        valid_status_data["code"] = "paid"
        valid_status_data["name"] = "Оплачен"
        status2 = Status.objects.create(**valid_status_data)

        # Проверяем, что флаг у первого статуса снялся
        status1.refresh_from_db()  # Обновляем объект из базы данных
        assert not status1.is_default
        assert status2.is_default

    def test_ordering(self, valid_status_data, status_group):
        """Тест сортировки."""
        # Создаем несколько статусов
        status1 = Status.objects.create(**valid_status_data)

        valid_status_data["code"] = "paid"
        valid_status_data["name"] = "Оплачен"
        valid_status_data["order"] = 2
        valid_status_data["is_default"] = False
        status2 = Status.objects.create(**valid_status_data)

        valid_status_data["code"] = "cancelled"
        valid_status_data["name"] = "Отменен"
        valid_status_data["order"] = 3
        status3 = Status.objects.create(**valid_status_data)

        # Проверяем порядок
        statuses = Status.objects.filter(group=status_group)
        assert list(statuses) == [status1, status2, status3]

    def test_str_method(self, valid_status_data):
        """Тест строкового представления."""
        status = Status.objects.create(**valid_status_data)
        expected = f"{status.name} ({status.group.name})"
        assert str(status) == expected
