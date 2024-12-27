"""Интеграционные тесты для полного цикла заказ-доставка."""

import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model


from balance.services.constants import TransactionTypeChoices
from balance.models import Transaction
from order.models import Order
from package.models import Package
from package.models import PackageDelivery
from package.models import PackageOrder


class TestOrderDeliveryFlow:
    """
    Тестирование полного цикла:
    заказ -> оплата заказа -> создание посылки -> создание доставки -> оплата доставки.
    """

    def test_create_order(
        self, user_with_balance, user_balance, zara_site, statuses, exchange_rate
    ):
        """
        Тест создания нового заказа.

        Шаги:
        1. Подготовка данных для заказа
        2. Создание заказа
        3. Проверк�� созданного заказа
        4. Проверка корректности дат
        5. Проверка корректности сумм
        6. Проверка уникальности номеров
        """
        # Подготовка данных
        amount_euro = Decimal("50.00")
        amount_rub = amount_euro * exchange_rate
        initial_balance_euro = user_balance.balance_euro
        initial_balance_rub = user_balance.balance_rub

        # Создание заказа
        order = Order.objects.create(
            user=user_with_balance,
            site=zara_site,
            status=statuses["order"]["new"],
            internal_number="TEST-001",
            external_number="ZARA-001",
            amount_euro=amount_euro,
            amount_rub=amount_rub,
            created_at=timezone.now(),
        )

        # Базовые проверки
        assert order.pk is not None
        assert order.user == user_with_balance
        assert order.site == zara_site
        assert order.status == statuses["order"]["new"]
        assert order.amount_euro == amount_euro
        assert order.amount_rub == amount_rub

        # Проверка корректности дат
        assert order.created_at is not None
        assert order.created_at <= timezone.now()
        assert order.paid_at is None

        # Проверка корректности расчета суммы в рублях
        calculated_amount_rub = (order.amount_euro * exchange_rate).quantize(
            Decimal("0.01")
        )
        assert order.amount_rub == calculated_amount_rub, (
            f"Сумма в рублях {order.amount_rub} не соответствует "
            f"расчетной {calculated_amount_rub}"
        )

        # Проверка номеров заказа
        assert order.internal_number == "TEST-001"
        assert order.external_number == "ZARA-001"
        assert (
            order.internal_number.strip() == order.internal_number
        ), "Номер содержит пробелы"
        assert (
            order.external_number.strip() == order.external_number
        ), "Номер содержит пробелы"

        # Проверка уникальности номеров в отдельных транзакциях
        from django.db import IntegrityError, transaction

        # Проверка уникальности internal_number
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Order.objects.create(
                    user=user_with_balance,
                    site=zara_site,
                    status=statuses["order"]["new"],
                    internal_number="TEST-001",  # Дублирующийся номер
                    external_number="ZARA-002",
                    amount_euro=amount_euro,
                    amount_rub=amount_rub,
                    created_at=timezone.now(),
                )

        # Проверка уникальности external_number
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Order.objects.create(
                    user=user_with_balance,
                    site=zara_site,
                    status=statuses["order"]["new"],
                    internal_number="TEST-002",
                    external_number="ZARA-001",  # Дублирующийся номер
                    amount_euro=amount_euro,
                    amount_rub=amount_rub,
                    created_at=timezone.now(),
                )

        # Проверка что баланс не изменился
        assert user_balance.balance_euro == initial_balance_euro
        assert user_balance.balance_rub == initial_balance_rub

        # Проверка расчета прибыли и расходов
        assert order.expense == Decimal("0.00")
        assert order.profit == Decimal("0.00")

    @pytest.mark.parametrize(
        "amount_euro,expected_error",
        [
            (Decimal("0.00"), "Цена в евро должна быть больше 0"),
            (Decimal("-10.00"), "Цена в евро должна быть больше 0"),
        ],
    )
    def test_create_order_with_invalid_amount(
        self,
        user_with_balance,
        zara_site,
        statuses,
        exchange_rate,
        amount_euro,
        expected_error,
    ):
        """Тест создания заказа с некорректной суммой."""
        from django.core.exceptions import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            Order.objects.create(
                user=user_with_balance,
                site=zara_site,
                status=statuses["order"]["new"],
                internal_number="TEST-002",
                external_number="ZARA-002",
                amount_euro=amount_euro,
                amount_rub=amount_euro * exchange_rate,
                created_at=timezone.now(),
            )

        assert expected_error in str(exc_info.value)

    def test_pay_order(
        self,
        user_with_balance,
        user_balance,
        zara_site,
        statuses,
        exchange_rate,
    ):
        """Тест оплаты заказа через смену статуса."""
        # Подготовка данных
        amount_euro = Decimal("50.00")
        amount_rub = amount_euro * exchange_rate
        initial_balance_euro = user_balance.balance_euro
        initial_balance_rub = user_balance.balance_rub

        # Создание заказа
        order = Order.objects.create(
            user=user_with_balance,
            site=zara_site,
            status=statuses["order"]["new"],
            internal_number="TEST-003",
            external_number="ZARA-003",
            amount_euro=amount_euro,
            amount_rub=amount_rub,
            created_at=timezone.now(),
        )

        # Сохраняем начальное состояние
        initial_transaction_count = Transaction.objects.count()

        # Оплата заказа через смену статуса
        order.status = statuses["order"]["paid"]
        order.save()

        # Обновляем объекты из базы
        order.refresh_from_db()
        user_balance.refresh_from_db()

        # Проверка статуса и даты оплаты
        assert order.status == statuses["order"]["paid"]
        assert order.paid_at is not None
        assert order.paid_at <= timezone.now()

        # Проверка изменения баланса и создания транзакции
        assert user_balance.balance_euro < initial_balance_euro
        assert user_balance.balance_rub < initial_balance_rub
        assert Transaction.objects.count() > initial_transaction_count

        # Сохраняем состояние после оплаты
        paid_amount_euro = order.amount_euro
        paid_amount_rub = order.amount_rub
        paid_status = order.status
        paid_at = order.paid_at

        # Попытка изменить суммы после оплаты
        with pytest.raises(ValidationError) as exc_info:
            order.amount_euro = Decimal("60.00")
            order.amount_rub = Decimal("6000.00")
            order.save()

        assert "Невозможно изменить сумму после оплаты" in str(exc_info.value)

        # Проверяем, что значения не изменились
        order.refresh_from_db()
        assert order.amount_euro == paid_amount_euro
        assert order.amount_rub == paid_amount_rub
        assert order.status == paid_status
        assert order.paid_at == paid_at

        # Попытка удалить оплаченный заказ
        with pytest.raises(ValidationError):
            order.delete()

    def test_create_package_for_paid_order(
        self,
        user_with_balance,
        user_balance,
        zara_site,
        statuses,
        exchange_rate,
    ):
        """
        Тест создания посылки для оплаченного заказа.

        Шаги:
        1. Создание неоплаченного заказа и проверка невозможности добавления в посылку
        2. Создание и оплата заказа
        3. Создание посылки и добавление оплаченного заказа
        4. Проверка расчета стоимости
        5. Проверка уникальности номера посылки
        """
        # Создаем неоплаченный заказ
        unpaid_order = Order.objects.create(
            user=user_with_balance,
            site=zara_site,
            status=statuses["order"]["new"],
            internal_number="TEST-003",
            external_number="ZARA-003",
            amount_euro=Decimal("50.00"),
            amount_rub=Decimal("50.00") * exchange_rate,
        )

        # Создаем посылку
        package = Package.objects.create(
            user=user_with_balance,
            number="PKG-001",
            shipping_cost_eur=Decimal("10.00"),
            fee_cost_eur=Decimal("5.00"),
        )

        # Проверяем что нельзя добавить неоплаченный заказ
        with pytest.raises(ValidationError) as exc_info:
            PackageOrder.objects.create(package=package, order=unpaid_order)
        assert "Можно добавлять только оплаченные заказы" in str(exc_info.value)

        # Создаем и оплачиваем заказ
        paid_order = Order.objects.create(
            user=user_with_balance,
            site=zara_site,
            status=statuses["order"]["new"],
            internal_number="TEST-004",
            external_number="ZARA-004",
            amount_euro=Decimal("50.00"),
            amount_rub=Decimal("50.00") * exchange_rate,
        )
        paid_order.status = statuses["order"]["paid"]
        paid_order.save()

        # Проверяем что можно добавить оплаченный заказ
        package_order = PackageOrder.objects.create(package=package, order=paid_order)

        # Проверяем связь
        assert paid_order in package.orders.all()
        assert package in paid_order.packages.all()

        # Проверяе�� расчет общей стоимости
        expected_total = Decimal("15.00")  # 10.00 + 5.00
        assert package.total_cost_eur == expected_total

        # Проверяем уникальность номера посылки для одного пользователя
        with pytest.raises(ValidationError) as exc_info:
            Package.objects.create(
                user=user_with_balance,  # тот же пользователь
                number="PKG-001",  # тот же номер
                shipping_cost_eur=Decimal("10.00"),
                fee_cost_eur=Decimal("5.00"),
            )

        error_dict = exc_info.value.message_dict
        assert "__all__" in error_dict
        assert (
            "Посылка с такими значениями полей Пользователь и Номер посылки в сервисе у посредника уже существует."
            in error_dict["__all__"][0]
        )

        # Проверяем что можно создать посылку с тем же номером для другого пользователя
        other_user = get_user_model().objects.create_user(
            username="other_user", password="testpass123"
        )
        other_package = Package.objects.create(
            user=other_user,  # другой пользователь
            number="PKG-001",  # тот же номер
            shipping_cost_eur=Decimal("10.00"),
            fee_cost_eur=Decimal("5.00"),
        )

        # Проверяем что данные не изменились
        package.refresh_from_db()
        assert package.number == "PKG-001"
        assert package.shipping_cost_eur == Decimal("10.00")
        assert package.fee_cost_eur == Decimal("5.00")
        assert package.total_cost_eur == expected_total

    def test_create_delivery_for_package(
        self,
        user_with_balance,
        user_balance,
        zara_site,
        statuses,
        exchange_rate,
        default_transport_company,
    ):
        """
        Тест создания доставки для посылки.

        Шаги:
        1. Создание и оплата заказа
        2. Создание посылки
        3. Создание доставки для посылки
        4. Проверка созданной доставки
        5. Проверка невозможности создания второй доставки
        6. Проверка валидации веса и трек-номера
        7. Проверка невозможности удаления посылки с существующей доставкой
        """
        # Создание и оплата заказа
        order = Order.objects.create(
            user=user_with_balance,
            site=zara_site,
            status=statuses["order"]["new"],
            internal_number="TEST-005",
            external_number="ZARA-005",
            amount_euro=Decimal("50.00"),
            amount_rub=Decimal("50.00") * exchange_rate,
        )
        order.status = statuses["order"]["paid"]
        order.save()

        # Создание посылки
        package = Package.objects.create(
            user=user_with_balance,
            number="PKG-002",
            shipping_cost_eur=Decimal("10.00"),
            fee_cost_eur=Decimal("5.00"),
        )
        PackageOrder.objects.create(package=package, order=order)

        # Создание первой доставки
        delivery = PackageDelivery.objects.create(
            package=package,
            transport_company=default_transport_company,
            status=statuses["delivery"]["new"],
            tracking_number="TRACK-001",
            weight=Decimal("2.5"),
            shipping_cost_rub=Decimal("1000.00"),
            price_rub_for_kg=Decimal("400.00"),
            delivery_address="Test Address, 123",
        )

        # Проверка базовых полей доставки
        assert delivery.pk is not None
        assert delivery.package == package
        assert delivery.transport_company == default_transport_company
        assert delivery.status == statuses["delivery"]["new"]
        assert delivery.tracking_number == "TRACK-001"
        assert delivery.weight == Decimal("2.5")
        assert delivery.shipping_cost_rub == Decimal("1000.00")
        assert delivery.price_rub_for_kg == Decimal("400.00")
        assert delivery.delivery_address == "Test Address, 123"

        # Проверка невозможности создания второй доставки для той же посылки
        with pytest.raises(ValidationError) as exc_info:
            PackageDelivery.objects.create(
                package=package,  # та же посылка
                transport_company=default_transport_company,
                status=statuses["delivery"]["new"],
                tracking_number="TRACK-002",
                weight=Decimal("3.0"),
                shipping_cost_rub=Decimal("1200.00"),
                price_rub_for_kg=Decimal("400.00"),
            )

        error_dict = exc_info.value.message_dict
        assert "package" in error_dict
        assert "Для этой посылки уже существует доставка" in error_dict["package"][0]

        # Создаем новую посылку для тестирования валидации
        new_package = Package.objects.create(
            user=user_with_balance,
            number="PKG-003",
            shipping_cost_eur=Decimal("10.00"),
            fee_cost_eur=Decimal("5.00"),
        )

        # Проверка валидации отрицательного вес��
        with pytest.raises(ValidationError) as exc_info:
            PackageDelivery.objects.create(
                package=new_package,
                transport_company=default_transport_company,
                status=statuses["delivery"]["new"],
                tracking_number="TRACK-003",
                weight=Decimal("-1.0"),  # Отрицательный вес
                shipping_cost_rub=Decimal("1000.00"),
                price_rub_for_kg=Decimal("400.00"),
            )
        assert "weight" in exc_info.value.message_dict
        assert (
            "Вес не может быть отрицательным"
            in exc_info.value.message_dict["weight"][0]
        )

        # Проверка валидации пустого трек-номера
        with pytest.raises(ValidationError) as exc_info:
            PackageDelivery.objects.create(
                package=new_package,
                transport_company=default_transport_company,
                status=statuses["delivery"]["new"],
                tracking_number="",  # Пустой трек-номер
                weight=Decimal("2.5"),
                shipping_cost_rub=Decimal("1000.00"),
                price_rub_for_kg=Decimal("400.00"),
            )
        assert "tracking_number" in exc_info.value.message_dict
        assert (
            "Это поле не может быть пустым."
            in exc_info.value.message_dict["tracking_number"][0]
        )

        # Проверка очистки пробелов в трек-номере
        delivery_with_spaces = PackageDelivery.objects.create(
            package=Package.objects.create(
                user=user_with_balance,
                number="PKG-004",
                shipping_cost_eur=Decimal("10.00"),
                fee_cost_eur=Decimal("5.00"),
            ),
            transport_company=default_transport_company,
            status=statuses["delivery"]["new"],
            tracking_number="  TRACK-005  ",  # Пробелы в начале и конце
            weight=Decimal("2.5"),
            shipping_cost_rub=Decimal("1000.00"),
            price_rub_for_kg=Decimal("400.00"),
        )
        assert (
            delivery_with_spaces.tracking_number == "TRACK-005"
        )  # Пробелы должны быть удалены

        # Проверка невозможности удаления посылки с существующей доставкой
        with pytest.raises(ValidationError) as exc_info:
            package.delete()

        error_dict = exc_info.value.message_dict
        assert "package" in error_dict
        assert (
            "Невозможно удалить посылку с существующей доставкой"
            in error_dict["package"][0]
        )

    def test_pay_delivery(
        self,
        user_with_balance,
        user_balance,
        zara_site,
        statuses,
        exchange_rate,
        default_transport_company,
    ):
        """
        Тест оплаты доставки через смену статуса.

        Шаги:
        1. Создание и оплата заказа
        2. Создание посылки
        3. Создание доставки
        4. Оплата доставки через смену статуса
        5. Проверка расчета стоимости
        6. Проверка создания транзакции
        7. Проверка изменения баланса
        8. Проверка невозможности удаления оплаченной доставки
        """
        # Создание и оплата заказа
        amount_euro = Decimal("50.00")
        amount_rub = amount_euro * exchange_rate

        order = Order.objects.create(
            user=user_with_balance,
            site=zara_site,
            status=statuses["order"]["new"],
            internal_number="TEST-006",
            external_number="ZARA-006",
            amount_euro=amount_euro,
            amount_rub=amount_rub,
            created_at=timezone.now(),
        )
        order.status = statuses["order"]["paid"]
        order.save()

        # Создание посылки
        package = Package.objects.create(
            user=user_with_balance,
            number="PKG-003",
            shipping_cost_eur=Decimal("10.00"),
            fee_cost_eur=Decimal("5.00"),
        )
        package.orders.add(order)

        # Создание доставки с установленной стоимостью
        delivery = PackageDelivery.objects.create(
            package=package,
            transport_company=default_transport_company,
            status=statuses["delivery"]["new"],
            tracking_number="TRACK-002",
            weight=Decimal("2.5"),
            shipping_cost_rub=Decimal("1500.00"),
            price_rub_for_kg=Decimal("600.00"),
            delivery_address="Test Address, 123",
        )

        # Сохраняем начальное состояние до оплаты
        initial_balance_euro = user_balance.balance_euro
        initial_balance_rub = user_balance.balance_rub
        initial_transaction_count = Transaction.objects.count()

        # Оплата доставки через смену статуса
        delivery.status = statuses["delivery"]["paid"]
        delivery.save()

        # Проверяем изменения после оплаты
        delivery.refresh_from_db()
        user_balance.refresh_from_db()

        # Проверка корректности даты оплаты
        assert delivery.paid_at is not None, "Дата оплаты не установлена"
        assert delivery.paid_at <= timezone.now(), "Дата оплаты в будущем"

        # Проверка изменения баланса и создания транзакции
        assert (
            user_balance.balance_euro < initial_balance_euro
        ), "Баланс в евро не уменьшился"
        assert (
            user_balance.balance_rub < initial_balance_rub
        ), "Баланс в рублях не уменьшился"
        assert (
            Transaction.objects.count() > initial_transaction_count
        ), "Транзакция не создана"

        # Сохраняем состояние после оплаты
        paid_balance_euro = user_balance.balance_euro
        paid_balance_rub = user_balance.balance_rub
        paid_transaction_count = Transaction.objects.count()
        paid_shipping_cost = delivery.shipping_cost_rub
        paid_price_per_kg = delivery.price_rub_for_kg
        paid_at = delivery.paid_at

        # Попытка изменить стоимость после оплаты
        delivery.shipping_cost_rub = Decimal("2000.00")
        delivery.price_rub_for_kg = Decimal("800.00")
        delivery.save()

        # Проверяем, что ничего не изменилось после попытки изменения
        delivery.refresh_from_db()
        user_balance.refresh_from_db()

        assert (
            delivery.shipping_cost_rub == paid_shipping_cost
        ), "Стоимость доставки изменилась после оплаты"
        assert (
            delivery.price_rub_for_kg == paid_price_per_kg
        ), "Стоимость за кг изменилась после оплаты"
        assert delivery.paid_at == paid_at, "Дата оплаты изменилась"
        assert user_balance.balance_euro == paid_balance_euro, "Баланс в евро изменился"
        assert user_balance.balance_rub == paid_balance_rub, "Баланс в рублях изменился"
        assert (
            Transaction.objects.count() == paid_transaction_count
        ), "Создана новая транзакция"

    def test_transaction_types(self, user_with_balance, user_balance):
        """Тест создания транзакций разных типов."""
        # Очищаем все транзакции перед тестом
        Transaction.objects.all().delete()

        # Создаем транзакции разных типов
        transactions = [
            Transaction.objects.create(
                balance=user_balance,
                transaction_type=TransactionTypeChoices.REPLENISHMENT,
                amount_euro=Decimal("100.00"),
                amount_rub=Decimal("10000.00"),
            ),
            Transaction.objects.create(
                balance=user_balance,
                transaction_type=TransactionTypeChoices.EXPENSE,
                amount_euro=Decimal("50.00"),
                amount_rub=Decimal("5000.00"),
            ),
            Transaction.objects.create(
                balance=user_balance,
                transaction_type=TransactionTypeChoices.PAYBACK,
                amount_euro=Decimal("30.00"),
                amount_rub=Decimal("3000.00"),
            ),
        ]

        # Проверяем количество транзакций
        assert Transaction.objects.count() == 3

        # Проверяем типы транзакций
        transaction_types = set(
            Transaction.objects.values_list("transaction_type", flat=True)
        )
        expected_types = {
            TransactionTypeChoices.REPLENISHMENT,
            TransactionTypeChoices.EXPENSE,
            TransactionTypeChoices.PAYBACK,
        }
        assert transaction_types == expected_types
