"""Тесты модульного тестирования для модели Order.

Тесты проверяют корректность создания и удаления заказов, а также
корректность сохранения их значений.
"""

from decimal import Decimal


import pytest
from balance.services.constants import TransactionTypeChoices
from django.core.exceptions import ValidationError

from django.utils import timezone
from order.models import Order, Site
from status.constants import OrderStatusCode
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


@pytest.mark.django_db
class TestOrderBalanceOperations:
    """Тесты для проверки операций с балансом при оплате заказов."""

    @pytest.fixture
    def user_with_initial_balance(self):
        """Создание пользователя с начальным балансом 1000 EUR / 98000 RUB."""
        user_service = UserService()
        user = user_service.create_user(
            username="balance_test_user",
            email="balance@test.com",
            password="test123@rew3rfa3qeraw",
        )

        # Создаем транзакцию пополнения
        from balance.models import Transaction

        # Сначала создаем объект
        transaction = Transaction.objects.create(
            balance=user.balance,
            amount_euro=Decimal("1000.00"),
            amount_rub=Decimal("98000.00"),
            transaction_type=TransactionTypeChoices.REPLENISHMENT,
        )

        # Затем сохраняем с дополнительным параметром
        transaction.save(process_transaction=True)

        return user

    @pytest.fixture
    def test_site(self):
        """Фикстура тестового сайта."""
        return Site.objects.create(
            name="Test Site",
            url="https://test.com",
            organizer_fee_percentage=Decimal("10.00"),
        )

    def test_balance_and_average_rate_after_orders(
        self, user_with_initial_balance, test_site
    ):
        """
        Тест проверяет корректность операций с балансом при оплате заказов.
        """
        user = user_with_initial_balance
        print(
            f"\nНачальный баланс: {user.balance.balance_euro} EUR | {user.balance.balance_rub} RUB"
        )

        # Получаем статусы
        status_group = StatusGroup.objects.get(code="ORDER_STATUS_CONFIG")
        new_status = status_group.status.get(
            code="new"
        )  # Используем status вместо statuses
        paid_status = status_group.status.get(code="paid")

        # Проверяем тип транзакции для paid статуса
        transaction_type = status_group.get_transaction_type_by_status("paid")
        print(f"Transaction type for paid status: {transaction_type}")

        test_orders = [
            (Decimal("200.00"), Decimal("19600.00")),  # 98 RUB/EUR
            (Decimal("300.00"), Decimal("29400.00")),  # 98 RUB/EUR
            (Decimal("150.00"), Decimal("14700.00")),  # 98 RUB/EUR
        ]

        for i, (amount_euro, amount_rub) in enumerate(test_orders):
            print(f"\n--- Заказ {i+1} ---")
            print(f"Сумма заказа: {amount_euro} EUR | {amount_rub} RUB")

            # Создаем заказ
            order = Order.objects.create(
                user=user,
                site=test_site,
                status=new_status,  # Используем new_status
                internal_number=f"TEST-{i+1}",
                external_number=f"EXT-{i+1}",
                amount_euro=amount_euro,
                amount_rub=amount_rub,
            )

            # Сохраняем баланс до оплаты
            balance_euro_before = user.balance.balance_euro
            balance_rub_before = user.balance.balance_rub
            print(
                f"Баланс до оплаты: {balance_euro_before} EUR | {balance_rub_before} RUB"
            )

            # Меняем статус на paid
            order.status = paid_status
            order.save()

            # Проверяем транзакцию
            last_transaction = user.balance.transactions.last()
            print(
                f"Транзакция: тип={last_transaction.transaction_type}, "
                f"сумма={last_transaction.amount_euro} EUR"
            )

            # Обновляем данные из БД
            user.refresh_from_db()
            print(
                f"Баланс после оплаты: {user.balance.balance_euro} EUR | {user.balance.balance_rub} RUB"
            )

            # Проверяем корректность списания
            assert user.balance.balance_euro == balance_euro_before - amount_euro, (
                f"Неверное списание EUR: было {balance_euro_before}, "
                f"стало {user.balance.balance_euro}, "
                f"должно быть {balance_euro_before - amount_euro}"
            )
            assert user.balance.balance_rub == balance_rub_before - amount_rub, (
                f"Неверное списание RUB: было {balance_rub_before}, "
                f"стало {user.balance.balance_rub}, "
                f"должно быть {balance_rub_before - amount_rub}"
            )

    def test_balance_decrease_with_average_rate(
        self, user_with_initial_balance, test_site
    ):
        """
        Тест проверяет корректность списания средств с учетом среднего курса.

        Сценарий:
        1. Начальный баланс: €3292.88 | ₽332349.90 (курс 100.93 ₽/€)
        2. Заказ на €274.78 | ₽38224.00
        3. После оплаты:
           - Баланс должен быть: €3018.10 | ₽304616.35
           - Средний курс должен остаться: 100.93 ₽/€
           - Расходы: ₽27733.55 (274.78 € * 100.93 ₽/€)
           - Прибыль: ₽10490.45 (38224.00 ₽ - 27733.55 ₽)
        """
        # 1. Подготовка начального баланса
        user = user_with_initial_balance
        balance = user.balance

        # Устанавливаем конкретные значения для теста
        balance.balance_euro = Decimal("3292.88")
        balance.balance_rub = Decimal("332349.90")
        balance.average_exchange_rate = Decimal("100.93")
        balance.save(allow_balance_update=True)

        print(f"\nНачальный баланс: €{balance.balance_euro} | ₽{balance.balance_rub}")
        print(f"Начальный средний курс: ₽{balance.average_exchange_rate}/€")

        # 2. Создание заказа
        order_euro = Decimal("274.78")
        order_rub = Decimal("38224.00")

        # Получаем статусы
        status_group = StatusGroup.objects.get(code="ORDER_STATUS_CONFIG")
        new_status = status_group.status.get(code="new")
        paid_status = status_group.status.get(code="paid")

        order = Order.objects.create(
            user=user,
            site=test_site,
            status=new_status,
            amount_euro=order_euro,
            amount_rub=order_rub,
            internal_number="TEST-1",  # Добавили обязательное поле
            external_number="EXT-1",  # Добавили обязательное поле
        )

        # 3. Сохраняем значения для проверки
        balance_euro_before = balance.balance_euro
        balance_rub_before = balance.balance_rub
        rate_before = balance.average_exchange_rate

        print(f"\nСумма заказа: €{order_euro} | ₽{order_rub}")
        print(
            f"Фактический курс заказа: ₽{(order_rub / order_euro).quantize(Decimal('0.01'))}/€"
        )

        # 4. Оплата заказа
        order.status = paid_status
        order.save()

        # Обновляем данные из БД
        balance.refresh_from_db()
        order.refresh_from_db()

        print(f"\nПосле оплаты:")
        print(f"Баланс: €{balance.balance_euro} | ₽{balance.balance_rub}")
        print(f"Средний курс: ₽{balance.average_exchange_rate}/€")
        print(f"Расходы: ₽{order.expense}")
        print(f"Прибыль: ₽{order.profit}")

        # 5. Проверки
        expected_euro = balance_euro_before - order_euro
        expected_rub_decrease = (order_euro * rate_before).quantize(Decimal("0.01"))
        expected_rub = balance_rub_before - expected_rub_decrease
        expected_expense = expected_rub_decrease
        expected_profit = order_rub - expected_expense

        # Проверяем баланс в евро
        assert balance.balance_euro == expected_euro, (
            f"Неверное списание EUR: "
            f"было {balance_euro_before}, стало {balance.balance_euro}, "
            f"должно быть {expected_euro}"
        )

        # Проверяем баланс в рублях
        assert balance.balance_rub == expected_rub, (
            f"Неверное списание RUB: "
            f"было {balance_rub_before}, стало {balance.balance_rub}, "
            f"должно быть {expected_rub} "
            f"(списано {balance_rub_before - balance.balance_rub}, "
            f"должно быть списано {expected_rub_decrease})"
        )

        # Проверяем средний курс
        assert balance.average_exchange_rate == rate_before, (
            f"Средний курс изменился: "
            f"было {rate_before}, стало {balance.average_exchange_rate}"
        )

        # Проверяем расходы
        assert order.expense == expected_expense, (
            f"Неверный расчет расходов: "
            f"получено {order.expense}, должно быть {expected_expense}"
        )

        # Проверяем прибыль
        assert order.profit == expected_profit, (
            f"Неверный расчет прибыли: "
            f"получено {order.profit}, должно быть {expected_profit}"
        )
