"""Тесты для массовых операций с заказами."""

import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone

from order.models import Order
from status.constants import OrderStatusCode


@pytest.mark.django_db
class TestOrderBulkOperations:
    """Тесты для массовых операций с заказами."""

    def test_bulk_status_update(self, user_with_balance, site, status, paid_status):
        """Тест массового обновления статуса заказов."""
        # Создаем несколько заказов
        orders = []
        for i in range(3):
            order = Order.objects.create(
                user=user_with_balance,
                site=site,
                status=status,
                internal_number=f"TEST-{i}",
                external_number=f"EXT-{i}",
                amount_euro=Decimal("100.00"),
                amount_rub=Decimal("10000.00"),
                created_at=timezone.now().date(),
            )
            orders.append(order)

        # Массовое обновление статуса
        Order.objects.filter(status=status).bulk_update_status(
            paid_status, comment="Массовая оплата"
        )

        # Проверяем что все заказы обновились
        updated_orders = Order.objects.filter(id__in=[o.id for o in orders])
        for order in updated_orders:
            assert order.status == paid_status
            assert order.comment == "Массовая оплата"

    def test_bulk_status_update_validation(
        self, user_with_balance, site, status_factory
    ):
        """Тест валидации при массовом обновлении статуса."""
        # Создаем заказ в статусе "new"
        new_order = Order.objects.create(
            user=user_with_balance,
            site=site,
            status=status_factory(code=OrderStatusCode.NEW),
            internal_number="TEST-NEW",
            external_number="EXT-NEW",
            amount_euro=Decimal("100.00"),
            amount_rub=Decimal("10000.00"),
            created_at=timezone.now().date(),
        )

        # Создаем заказ в статусе "paid"
        paid_order = Order.objects.create(
            user=user_with_balance,
            site=site,
            status=status_factory(code=OrderStatusCode.PAID),
            internal_number="TEST-PAID",
            external_number="EXT-PAID",
            amount_euro=Decimal("100.00"),
            amount_rub=Decimal("10000.00"),
            created_at=timezone.now().date(),
        )

        # Пытаемся обновить все заказы
        with pytest.raises(ValidationError) as exc_info:
            Order.objects.all().bulk_update_status(
                status_factory(code=OrderStatusCode.PAID)
            )

        # Проверяем сообщение об ошибке
        error_message = str(exc_info.value)
        assert "Невозможно обновить статусы" in error_message
        assert "Заказ TEST-PAID уже оплачен" in error_message

        # Проверяем что статусы не изменились
        new_order.refresh_from_db()
        paid_order.refresh_from_db()
        assert new_order.status.code == OrderStatusCode.NEW
        assert paid_order.status.code == OrderStatusCode.PAID

    def test_bulk_status_update_atomic(
        self, user_with_balance, site, status, paid_status
    ):
        """Тест атомарности массового обновления."""
        # Создаем заказы
        orders = []
        for i in range(3):
            order = Order.objects.create(
                user=user_with_balance,
                site=site,
                status=status,
                internal_number=f"TEST-{i}",
                external_number=f"EXT-{i}",
                amount_euro=Decimal("100.00"),
                amount_rub=Decimal("10000.00"),
                created_at=timezone.now().date(),
            )
            orders.append(order)

        # Добавляем заказ, который вызовет ошибку
        paid_order = Order.objects.create(
            user=user_with_balance,
            site=site,
            status=paid_status,
            internal_number="TEST-PAID",
            external_number="EXT-PAID",
            amount_euro=Decimal("100.00"),
            amount_rub=Decimal("10000.00"),
            created_at=timezone.now().date(),
        )

        # Пытаемся обновить все заказы
        with pytest.raises(ValidationError):
            Order.objects.all().bulk_update_status(paid_status)

        # Проверяем что ни один заказ не обновился
        for order in orders:
            order.refresh_from_db()
            assert order.status == status

    def test_bulk_status_update_invalid_status(self, user_with_balance, site, status):
        """Тест обработки некорректного статуса."""
        # Создаем заказ
        order = Order.objects.create(
            user=user_with_balance,
            site=site,
            status=status,
            internal_number="TEST-001",
            external_number="EXT-001",
            amount_euro=Decimal("100.00"),
            amount_rub=Decimal("10000.00"),
            created_at=timezone.now().date(),
        )

        # Проверяем различные некорректные статусы
        with pytest.raises(ValueError) as exc_info:
            Order.objects.all().bulk_update_status(None)
        assert "Не указан новый статус" in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            Order.objects.all().bulk_update_status("invalid")
        assert "Некорректный тип статуса" in str(exc_info.value)

    def test_bulk_status_update_empty_queryset(self, paid_status):
        """Тест обновления пустого queryset."""
        # Пытаемся обновить пустой queryset
        result = Order.objects.none().bulk_update_status(paid_status)
        assert result == 0

    def test_bulk_status_update_invalid_transition(
        self, user_with_balance, site, status, paid_status
    ):
        """Тест недопустимого перехода между статусами."""
        # Создаем заказ
        order = Order.objects.create(
            user=user_with_balance,
            site=site,
            status=status,
            internal_number="TEST-001",
            external_number="EXT-001",
            amount_euro=Decimal("100.00"),
            amount_rub=Decimal("10000.00"),
            created_at=timezone.now().date(),
        )

        # Создаем статус с недопустимым переходом
        from status.models import Status

        invalid_status = Status.objects.create(
            code="invalid",
            name="Invalid",
            group=status.group,
            is_default=False,
        )

        # Пытаемся выполнить недопустимый переход
        with pytest.raises(ValidationError) as exc_info:
            Order.objects.all().bulk_update_status(invalid_status)

        error_message = str(exc_info.value)
        assert "Недопустимый переход" in error_message
        assert order.internal_number in error_message

    def test_bulk_status_update_with_comment_none(
        self, user_with_balance, site, status, paid_status
    ):
        """Тест обновления статуса без комментария."""
        # Создаем заказ с комментарием
        order = Order.objects.create(
            user=user_with_balance,
            site=site,
            status=status,
            internal_number="TEST-001",
            external_number="EXT-001",
            amount_euro=Decimal("100.00"),
            amount_rub=Decimal("10000.00"),
            created_at=timezone.now().date(),
            comment="Старый комментарий",
        )

        # Обновляем статус без указания комментария
        Order.objects.all().bulk_update_status(paid_status)

        # Проверяем что комментарий не изменился
        order.refresh_from_db()
        assert order.status == paid_status
        assert order.comment == "Старый комментарий"

    def test_bulk_status_update_concurrent(
        self, user_with_balance, site, status, paid_status
    ):
        """Тест конкурентного обновления статусов."""
        from django.db import transaction, connection
        from django.db.utils import OperationalError

        # Создаем заказы
        orders = []
        for i in range(3):
            order = Order.objects.create(
                user=user_with_balance,
                site=site,
                status=status,
                internal_number=f"TEST-{i}",
                external_number=f"EXT-{i}",
                amount_euro=Decimal("100.00"),
                amount_rub=Decimal("10000.00"),
                created_at=timezone.now().date(),
            )
            orders.append(order)

        # Для PostgreSQL проверяем блокировку через nowait
        if connection.vendor == "postgresql":
            # Начинаем внешнюю транзакцию
            with transaction.atomic():
                # Блокируем заказы
                Order.objects.select_for_update().filter(
                    id__in=[o.id for o in orders]
                ).exists()

                # Пытаемся получить блокировку в другой транзакции
                with pytest.raises(OperationalError):
                    with transaction.atomic():
                        Order.objects.filter(
                            id__in=[o.id for o in orders]
                        ).select_for_update(nowait=True).exists()

        # Для SQLite проверяем базовую сериализацию транзакций
        else:
            # Первая транзакция
            with transaction.atomic():
                # Блокируем и читаем заказы
                orders_qs = Order.objects.select_for_update().filter(
                    id__in=[o.id for o in orders]
                )
                assert orders_qs.count() == len(orders)

                # Вторая транзакция должна ждать завершения первой
                with transaction.atomic():
                    # Пытаемся прочитать те же заказы
                    assert Order.objects.select_for_update().filter(
                        id__in=[o.id for o in orders]
                    ).count() == len(orders)

        # Проверяем что статусы не изменились
        for order in orders:
            order.refresh_from_db()
            assert order.status == status
