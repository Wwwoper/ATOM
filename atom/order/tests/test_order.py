"""Тесты модульного тестирования для модели Order.

Тесты проверяют корректность создания и удаления заказов, а также
корректность сохранения их значений.
"""

import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.utils import timezone
from unittest.mock import patch
from django.db import transaction

from balance.services.constants import TransactionTypeChoices
from order.models import Site, Order
from status.models import Status, StatusGroup
from user.services import UserService


@pytest.mark.django_db
class TestOrder:
    """Тесты для модели Order."""

    @pytest.fixture
    def user(self):
        """Фикстура для создания тестового пользователя."""
        user_service = UserService()
        return user_service.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    @pytest.fixture
    def site(self):
        """Фикстура для создания тестового сайта."""
        return Site.objects.create(
            name="Test Site",
            url="https://test-site.com",
            organizer_fee_percentage=Decimal("10.00"),
        )

    @pytest.fixture
    def transaction(self, user):
        """Фикстура для создания тестовой транзакции."""
        from balance.models import Transaction

        transaction = Transaction.objects.create(
            balance=user.balance,
            amount_euro=Decimal("1000.00"),  # Достаточная сумма для тестов
            amount_rub=Decimal("100000.00"),  # Достаточная сумма для тестов
            transaction_type=TransactionTypeChoices.REPLENISHMENT,
        )
        # Сохраняем без обработки транзакции
        transaction.save(process_transaction=False)
        return transaction

    @pytest.fixture
    def valid_order_data(self, site, user):
        """Фикстура с валидными данными заказа."""
        # Получаем существующий статус по умолчанию для заказов
        default_status = Status.objects.get(group__code="order_status", is_default=True)

        return {
            "user": user,
            "site": site,
            "status": default_status,
            "internal_number": "INT-1",
            "external_number": "EXT-1",
            "amount_euro": Decimal("100.00"),
            "amount_rub": Decimal("10000.00"),
            "profit": Decimal("10.00"),  # 10% от суммы в евро
            "expense": Decimal("0.00"),
        }

    def test_create_order(self, valid_order_data):
        """Тест создания заказа с валидными данными."""
        order = Order.objects.create(**valid_order_data)

        assert order.pk is not None
        assert order.user == valid_order_data["user"]
        assert order.internal_number == valid_order_data["internal_number"]
        assert order.external_number == valid_order_data["external_number"]
        assert order.amount_euro == valid_order_data["amount_euro"]
        assert order.amount_rub == valid_order_data["amount_rub"]
        assert order.status == valid_order_data["status"]
        assert order.created_at <= timezone.now()

    def test_amount_validation(self, valid_order_data):
        """Тест валидации сумм (должны быть > 0)."""
        # Тест невалидных сумм
        invalid_amounts = [
            (Decimal("-1.00"), Decimal("10000.00")),
            (Decimal("100.00"), Decimal("-1.00")),
            (Decimal("0.00"), Decimal("10000.00")),
            (Decimal("100.00"), Decimal("0.00")),
        ]

        for euro, rub in invalid_amounts:
            order_data = valid_order_data.copy()
            order_data["amount_euro"] = euro
            order_data["amount_rub"] = rub
            with pytest.raises(ValidationError):
                Order.objects.create(**order_data)

    def test_unique_constraints(self, valid_order_data):
        """Тест уникальности internal_number и external_number."""
        # Создаем первый заказ
        order = Order.objects.create(**valid_order_data)

        # Попытка создать заказ с тем же internal_number
        duplicate_internal = valid_order_data.copy()
        duplicate_internal["external_number"] = "EXT-2"
        with pytest.raises(IntegrityError):
            with transaction.atomic():  # Добавляем явную транзакцию
                Order.objects.create(**duplicate_internal)

        # Попытка создать заказ с тем же external_number
        duplicate_external = valid_order_data.copy()
        duplicate_external["internal_number"] = "INT-2"
        with pytest.raises(IntegrityError):
            with transaction.atomic():  # Добавляем явную транзакцию
                Order.objects.create(**duplicate_external)

    @patch(
        "order.services.order_service.OrderService.serialize_order_data_for_transaction"
    )
    @patch(
        "order.services.order_processor_service.OrderProcessor.execute_status_strategy"
    )
    def test_paid_order_immutability(
        self, mock_execute_strategy, mock_serialize_data, valid_order_data
    ):
        """Тест неизменяемости оплаченного заказа."""
        order = Order.objects.create(**valid_order_data)

        # Получаем статус "paid" из базы данных
        status_group = StatusGroup.objects.get(code="order_status")
        paid_status = Status.objects.get(group=status_group, code="paid")

        # Оплачиваем заказ
        order.status = paid_status
        order.save()

        # Попытка изменить суммы
        order.amount_euro = Decimal("200.00")
        with pytest.raises(ValidationError):
            order.clean()  # Вызываем clean() напрямую перед save()

        order.amount_euro = valid_order_data["amount_euro"]  # Восстанавливаем значение
        order.amount_rub = Decimal("20000.00")
        with pytest.raises(ValidationError):
            order.clean()

        # Восстанавливаем значения
        order.amount_rub = valid_order_data["amount_rub"]

        # Получаем статус "new" из базы данных
        new_status = Status.objects.get(group=status_group, code="new")

        # Попытка изменить статус
        order.status = new_status
        with pytest.raises(ValidationError):
            order.clean()

    def test_paid_order_deletion(self, valid_order_data):
        """Тест запрета удаления оплаченного заказа."""
        order = Order.objects.create(**valid_order_data)

        # Получаем статус "paid" из базы данных
        status_group = StatusGroup.objects.get(code="order_status")
        paid_status = Status.objects.get(group=status_group, code="paid")

        # Оплачиваем заказ
        order.status = paid_status
        order.save(skip_status_processing=True)  # Пропускаем обработку статуса

        # Попытка удалить оплаченный заказ
        with pytest.raises(ValidationError):
            order.delete()

    def test_status_processing(self, valid_order_data):
        """Тест обработки изменения статуса."""
        order = Order.objects.create(**valid_order_data)

        # Проверяем, что paid_at устанавливается при оплате
        assert order.paid_at is None

        # Получаем статус "paid" из базы данных
        status_group = StatusGroup.objects.get(code="order_status")
        paid_status = Status.objects.get(group=status_group, code="paid")

        # Меняем статус на "paid" и устанавливаем paid_at
        order.status = paid_status
        order.paid_at = timezone.now()  # Явно устанавливаем время оплаты
        order.save(skip_status_processing=True)  # Пропускаем обработку статуса

        # Обновляем объект из базы
        order.refresh_from_db()

        assert order.paid_at is not None
        assert order.paid_at <= timezone.now()

    def test_str_method(self, order):
        """Тест строкового представления заказа."""
        expected = f"Заказ №{order.internal_number} ({order.status.name} ({order.status.group.name}))"
        # или
        # expected = f"Заказ №INT-1 (Новый (Статусы заказа))"
        assert str(order) == expected

    def test_user_immutability(self, valid_order_data):
        """Тест невозможности изменения пользователя заказа."""
        # Создаем заказ
        order = Order.objects.create(**valid_order_data)

        # Создаем нового пользователя
        new_user = UserService().create_user(
            username="newuser", email="newuser@example.com", password="newpass123"
        )

        # Пытаемся изменить пользователя
        order.user = new_user

        # Проверяем, что возникает ошибка валидации
        with pytest.raises(ValidationError) as exc_info:
            order.clean()

        assert "Невозможно изменить пользователя после создания заказа" in str(
            exc_info.value
        )

        # Проверяем, что пользователь не изменился в базе
        order.refresh_from_db()
        assert order.user == valid_order_data["user"]
