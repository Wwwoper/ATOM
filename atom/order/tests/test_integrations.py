"""Интеграционные тесты для заказов."""

import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone

from order.models import Order, Site
from status.models import Status
from balance.models import Balance


@pytest.mark.django_db(transaction=True)
class TestSiteModel:
    """Тесты модели Site."""

    def test_create_site_with_valid_data(self):
        """Тест создания сайта с валидными данными."""
        site = Site.objects.create(
            name="Test Site",
            url="https://test.com",
            organizer_fee_percentage=Decimal("10.00"),
        )
        assert site.pk is not None
        assert site.name == "Test Site"
        assert site.organizer_fee_percentage == Decimal("10.00")

    def test_create_site_with_invalid_fee(self):
        """Тест создания сайта с невалидной комиссией."""
        with pytest.raises(ValidationError):
            Site.objects.create(
                name="Test Site",
                url="https://test.com",
                organizer_fee_percentage=Decimal("101.00"),
            )

    def test_site_total_orders(self, site, order):
        """Тест подсчета общего количества заказов."""
        assert site.total_orders == 1

    def test_site_total_profit(self, site, paid_order):
        """Тест подсчета общей прибыли."""
        assert site.total_profit > 0


@pytest.mark.django_db(transaction=True)
class TestOrderModel:
    """Тесты модели Order."""

    def test_create_order_with_valid_data(self, user, site, status):
        """Тест создания заказа с валидными данными."""
        order = Order.objects.create(
            user=user,
            site=site,
            status=status,
            internal_number="TEST001",
            external_number="EXT001",
            amount_euro=Decimal("100.00"),
            amount_rub=Decimal("10000.00"),
        )
        assert order.pk is not None
        assert order.internal_number == "TEST001"
        assert order.amount_euro == Decimal("100.00")

    def test_create_order_with_invalid_amount(self, user, site, status):
        """Тест создания заказа с невалидной суммой."""
        with pytest.raises(ValidationError):
            Order.objects.create(
                user=user,
                site=site,
                status=status,
                internal_number="TEST002",
                amount_euro=Decimal("-100.00"),
                amount_rub=Decimal("10000.00"),
            )

    def test_order_status_change(self, order, balance):
        """Тест изменения статуса заказа."""
        from order.services.order_service import OrderService

        # Обновляем курс обмена и баланс
        Balance.objects.filter(id=balance.id).update(
            average_exchange_rate=Decimal("100.00"),
            balance_euro=Decimal("1000.00"),
            balance_rub=Decimal("100000.00"),
        )
        balance.refresh_from_db()
        order.user.refresh_from_db()
        order.user.balance.refresh_from_db()

        # Сначала рассчитываем расходы и прибыль
        service = OrderService()
        service.calculate_expenses_and_profit(order)
        order.refresh_from_db()

        # Проверяем, что расходы рассчитаны
        assert order.expense > 0
        assert order.profit > 0

        # Затем меняем статус
        paid_status = Status.objects.get(code="paid", group__code="order_status")
        order.status = paid_status
        order.save()

        assert order.paid_at is not None

    def test_order_invalid_status_change(self, order):
        """Тест недопустимого изменения статуса."""
        refunded_status = Status.objects.get(
            code="refunded", group__code="order_status"
        )
        order.status = refunded_status
        with pytest.raises(ValidationError):
            order.save()


@pytest.mark.django_db(transaction=True)
class TestOrderService:
    """Тесты сервисов для работы с заказами."""

    def test_calculate_expenses_and_profit(self, order, balance):
        """Тест расчета расходов и прибыли."""
        from order.services.order_service import OrderService
        from status.models import Status

        service = OrderService()

        # Обновляем курс обмена напрямую в базе
        Balance.objects.filter(id=balance.id).update(
            average_exchange_rate=Decimal("100.00"),
            balance_euro=Decimal("1000.00"),  # Добавляем средства на баланс
            balance_rub=Decimal("100000.00"),  # Добавляем средства на баланс
        )
        balance.refresh_from_db()

        # Обновляем пользователя и его баланс
        order.user.refresh_from_db()
        order.user.balance.refresh_from_db()

        # Проверяем курс обмена
        assert balance.average_exchange_rate == Decimal("100.00")
        assert order.user.balance.average_exchange_rate == Decimal("100.00")

        # Рассчитываем расходы и прибыль
        service.calculate_expenses_and_profit(order)

        # Перезагружаем заказ из базы данных
        order.refresh_from_db()

        # Проверяем результаты
        expected_expense = (order.amount_euro * balance.average_exchange_rate).quantize(
            Decimal("0.00")
        )
        expected_profit = (order.amount_rub - expected_expense).quantize(
            Decimal("0.00")
        )

        assert order.expense == expected_expense
        assert order.profit == expected_profit
        assert order.expense == Decimal("10000.00")  # 100 EUR * 100 RUB
        assert order.profit == Decimal("5000.00")  # 15000 RUB - 10000 RUB

        # Меняем статус
        paid_status = Status.objects.get(code="paid", group__code="order_status")
        order.status = paid_status
        order.save()

        assert order.paid_at is not None

    def test_reset_profit_expense(self, paid_order):
        """Тест сброса расчетных полей."""
        from order.services.order_service import OrderService

        service = OrderService()
        service.reset_profit_expense_paid_at(paid_order)
        assert paid_order.expense == Decimal("0.00")
        assert paid_order.profit == Decimal("0.00")
        assert paid_order.paid_at is None

    def test_serialize_order_data(self, paid_order):
        """Тест сериализации данных заказа."""
        from order.services.order_service import OrderService
        from balance.services.constants import TransactionTypeChoices

        service = OrderService()
        data = service.serialize_order_data_for_transaction(paid_order)

        # Проверяем структуру данных
        assert data is not None
        assert isinstance(data, dict)
        assert "balance" in data
        assert "transaction_type" in data
        assert "amount_euro" in data
        assert "amount_rub" in data

        # Проверяем значения
        assert data["transaction_type"] == TransactionTypeChoices.EXPENSE.value
        assert data["amount_euro"] == paid_order.amount_euro
        assert (
            data["amount_rub"]
            == paid_order.amount_euro * paid_order.user.balance.average_exchange_rate
        )

    def test_serialize_order_data_new_order(self, order):
        """Тест сериализации данных для нового заказа."""
        from order.services.order_service import OrderService

        service = OrderService()
        data = service.serialize_order_data_for_transaction(order)
        assert data is None
