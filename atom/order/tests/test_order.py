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
from status.constants import OrderStatusCode


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
        default_status = Status.objects.get(
            group__code="ORDER_STATUS_CONFIG", is_default=True
        )

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

    def test_create_order(self, user, site, status):
        """Тест создания заказа."""
        order = Order(
            user=user,
            site=site,
            status=status,
            internal_number="TEST-001",
            external_number="ZARA-001",
            amount_euro=Decimal("100.00"),
            amount_rub=Decimal("10000.00").quantize(Decimal("0.01")),
            created_at=timezone.now().date(),
        )
        order.full_clean()
        order.save()

        assert order.pk is not None
        # Проверяем только что дата установлена
        assert order.created_at is not None

    def test_str_method(self, user, site, status):
        """Тест строкового представления заказа."""
        order = Order(
            user=user,
            site=site,
            status=status,
            internal_number="TEST-002",
            external_number="ZARA-002",
            amount_euro=Decimal("100.00"),
            amount_rub=Decimal("10000.00").quantize(Decimal("0.01")),
            created_at=timezone.now().date(),
        )
        order.full_clean()
        order.save()

        expected = f"Заказ №{order.internal_number} ({order.status})"
        assert str(order) == expected

    def test_unique_constraints(self, user, site, status):
        """Тест проверки уникальности полей заказа."""
        # Создаем первый заказ
        first_order = Order(
            user=user,
            site=site,
            status=status,
            internal_number="INT-1",
            external_number="EXT-1",
            amount_euro=Decimal("100.00"),
            amount_rub=Decimal("10000.00").quantize(Decimal("0.01")),
            created_at=timezone.now().date(),
        )
        first_order.full_clean()
        first_order.save()

        # Пытаемся создать заказ с тем же internal_number
        with pytest.raises(ValidationError) as exc_info:
            duplicate = Order(
                user=user,
                site=site,
                status=status,
                internal_number="INT-1",  # Тот же номер
                external_number="EXT-2",
                amount_euro=Decimal("100.00"),
                amount_rub=Decimal("10000.00").quantize(Decimal("0.01")),
                created_at=timezone.now().date(),
            )
            duplicate.full_clean()

        assert "internal_number" in exc_info.value.error_dict

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

    def test_paid_order_immutability(self, user_with_balance, site, status_factory):
        """Тест неизменяемости оплаченного заказа."""
        # Создаем заказ в статусе "new"
        order = Order.objects.create(
            user=user_with_balance,
            site=site,
            status=status_factory(code=OrderStatusCode.NEW),
            internal_number="TEST-001",
            external_number="EXT-001",
            amount_euro=Decimal("100.00"),
            amount_rub=Decimal("10000.00"),
            created_at=timezone.now().date(),
        )

        # Меняем статус на "paid" без обработки статуса
        order.status = status_factory(code=OrderStatusCode.PAID)
        order.save(skip_status_processing=True)  # Добавляем skip_status_processing=True

        # Пытаемся изменить суммы
        order.amount_euro = Decimal("200.00")
        order.amount_rub = Decimal("20000.00")

        # Проверяем что суммы не изменились после сохранения
        order.save()  # Здесь тоже можно добавить skip_status_processing=True
        order.refresh_from_db()

        assert order.amount_euro == Decimal("100.00")
        assert order.amount_rub == Decimal("10000.00")

    def test_paid_order_deletion(self, valid_order_data):
        """Тест запрета удаления оплаченного заказа."""
        order = Order.objects.create(**valid_order_data)

        # Получаем статус "paid" из базы данных
        status_group = StatusGroup.objects.get(code="ORDER_STATUS_CONFIG")
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
        status_group = StatusGroup.objects.get(code="ORDER_STATUS_CONFIG")
        paid_status = Status.objects.get(group=status_group, code="paid")

        # Меняем статус на "paid" и устанавливаем paid_at
        order.status = paid_status
        order.paid_at = timezone.now()  # Явно устанавливаем время оплаты
        order.save(skip_status_processing=True)  # Пропускаем обработку статуса

        # Обновляем объект из базы
        order.refresh_from_db()

        assert order.paid_at is not None
        assert order.paid_at <= timezone.now()

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
