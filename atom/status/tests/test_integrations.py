"""Интеграционные тесты для статусов."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.apps import apps
from django.contrib.contenttypes.models import ContentType

from status.models import Status, StatusGroup
from balance.services.constants import TransactionTypeChoices
from status.services.constants import (
    get_status_descriptions,
    get_status_names,
    get_status_codes,
    get_status_choices,
    get_default_status,
)


@pytest.mark.django_db(transaction=True)
class TestStatusGroupCreation:
    """Тесты создания группы статусов."""

    def test_create_status_group_with_valid_data(self, content_type_model):
        """Тест создания группы статусов с валидными данными."""
        group = StatusGroup.objects.create(
            name="Тестовая группа",
            code="test_group",
            content_type=content_type_model,
        )
        assert group.pk is not None
        assert group.name == "Тестовая группа"
        assert group.code == "test_group"

    def test_create_duplicate_status_group(self, status_group):
        """Тест создания дублирующей группы статусов."""
        with pytest.raises(IntegrityError):
            StatusGroup.objects.create(
                name="Дубликат",
                code=status_group.code,
                content_type=status_group.content_type,
            )

    def test_status_group_str(self, status_group):
        """Тест строкового представления группы статусов."""
        assert str(status_group) == status_group.name


@pytest.mark.django_db(transaction=True)
class TestStatusCreation:
    """Тесты создания статусов."""

    def test_create_status_with_valid_data(self, status_group):
        """Тест создания статуса с валидными данными."""
        status = Status.objects.create(
            group=status_group,
            code="test",
            name="Тест",
            description="Тестовый статус",
            order=1,
        )
        assert status.pk is not None
        assert status.code == "test"
        assert status.name == "Тест"

    def test_create_duplicate_status_in_group(self, status):
        """Тест создания дублирующего статуса в группе."""
        with pytest.raises(IntegrityError):
            Status.objects.create(
                group=status.group,
                code=status.code,
                name="Дубликат",
            )

    def test_status_str(self, status):
        """Тест строкового представления статуса."""
        assert str(status) == status.name


@pytest.mark.django_db(transaction=True)
class TestStatusTransitions:
    """Тесты переходов между статусами."""

    def test_allowed_transition(self, status_group):
        """Тест разрешенного перехода между статусами."""
        assert status_group.is_transition_allowed("new", "paid") is True

    def test_disallowed_transition(self, status_group):
        """Тест запрещенного перехода между статусами."""
        assert status_group.is_transition_allowed("new", "refunded") is False

    def test_nonexistent_status_transition(self, status_group):
        """Тест перехода с несуществующим статусом."""
        assert status_group.is_transition_allowed("nonexistent", "new") is False


@pytest.mark.django_db(transaction=True)
class TestStatusServices:
    """Тесты сервисов для работы со статусами."""

    def test_get_status_descriptions(self, status):
        """Тест получения описаний статусов."""
        Order = apps.get_model("order", "Order")
        descriptions = get_status_descriptions(Order)
        assert descriptions[status.code] == status.description

    def test_get_status_names(self, status):
        """Тест получения названий статусов."""
        Order = apps.get_model("order", "Order")
        names = get_status_names(Order)
        assert names[status.code] == status.name

    def test_get_status_codes(self, status):
        """Тест получения кодов статусов."""
        Order = apps.get_model("order", "Order")
        codes = get_status_codes(Order)
        assert codes[status.code] == status.code

    def test_get_status_choices(self, status):
        """Тест получения списка статусов для выбора."""
        Order = apps.get_model("order", "Order")
        choices = get_status_choices(Order)
        assert (status.code, status.name) in choices

    def test_get_default_status(self, status):
        """Тест получения статуса по умолчанию."""
        Order = apps.get_model("order", "Order")
        default_status = get_default_status(Order)
        assert default_status == status.code


@pytest.mark.django_db(transaction=True)
class TestStatusSignals:
    """Тесты сигналов для создания статусов."""

    def test_default_statuses_created(self):
        """Тест создания статусов по умолчанию."""
        Order = apps.get_model("order", "Order")
        status_group = StatusGroup.objects.get(code="order_status")
        assert status_group.content_type == ContentType.objects.get_for_model(Order)
        assert status_group.status.count() > 0

    def test_default_status_transitions(self):
        """Тест создания переходов между статусами по умолчанию."""
        status_group = StatusGroup.objects.get(code="order_status")
        assert status_group.allowed_status_transitions.get("new") == ["paid"]
        assert status_group.allowed_status_transitions.get("paid") == ["refunded"]

    def test_default_transaction_types(self):
        """Тест создания типов транзакций для статусов по умолчанию."""
        status_group = StatusGroup.objects.get(code="order_status")
        assert (
            status_group.transaction_type_by_status.get("paid")
            == TransactionTypeChoices.EXPENSE.value
        )
        assert (
            status_group.transaction_type_by_status.get("refunded")
            == TransactionTypeChoices.PAYBACK.value
        )
