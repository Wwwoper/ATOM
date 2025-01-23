"""Тесты для сервисов работы со статусами."""

import pytest
from django.contrib.contenttypes.models import ContentType

from status.services.constants import (
    get_status_descriptions,
    get_status_names,
    get_status_codes,
    get_status_choices,
    get_default_status,
)
from order.models import Order
from status.models import Status, StatusGroup


@pytest.mark.django_db
class TestStatusServices:
    """Тесты для сервисов работы со статусами."""

    @pytest.fixture
    def order_content_type(self):
        """Фикстура для получения ContentType модели Order."""
        return ContentType.objects.get_for_model(Order)

    @pytest.fixture
    def setup_statuses(self, order_content_type):
        """Фикстура для создания тестовых статусов."""
        group = StatusGroup.objects.create(
            name="Тестовая группа",
            code="test_group",
            content_type=order_content_type,
            allowed_status_transitions={"new": ["paid"], "paid": ["refunded"]},
            transaction_type_by_status={"paid": "EXPENSE", "refunded": "PAYBACK"},
        )

        statuses = [
            Status.objects.create(
                name="Новый",
                code="new",
                group=group,
                order=1,
                is_default=True,
                description="Новый заказ",
            ),
            Status.objects.create(
                name="Оплачен",
                code="paid",
                group=group,
                order=2,
                description="Заказ оплачен",
            ),
            Status.objects.create(
                name="Возврат",
                code="refunded",
                group=group,
                order=3,
                description="Возврат средств",
            ),
        ]
        return group, statuses

    def test_get_status_descriptions(self, setup_statuses):
        """Тест получения описаний статусов."""
        group, statuses = setup_statuses
        descriptions = get_status_descriptions(Order)

        assert descriptions["new"] == "Новый заказ"
        assert descriptions["paid"] == "Заказ оплачен"

    def test_get_status_names(self, setup_statuses):
        """Тест получения названий статусов."""
        group, statuses = setup_statuses
        names = get_status_names(Order)

        assert names["new"] == "Новый"
        assert names["paid"] == "Оплачен"

    def test_get_status_codes(self, setup_statuses):
        """Тест получения кодов статусов."""
        group, statuses = setup_statuses
        codes = get_status_codes(Order)

        assert codes["new"] == "new"
        assert codes["paid"] == "paid"

    def test_get_status_choices(self, setup_statuses):
        """Тест получения списка статусов для выбора."""
        group, statuses = setup_statuses
        choices = get_status_choices(Order)

        # Проверяем, что choices содержит правильные статусы
        assert len(choices) == 3
        assert ("new", "Новый") in choices
        assert ("paid", "Оплачен") in choices
        assert ("refunded", "Возврат") in choices

    def test_get_default_status(self, setup_statuses):
        """Тест получения статуса по умолчанию."""
        group, statuses = setup_statuses
        default_status = get_default_status(Order)

        assert default_status == "new"
