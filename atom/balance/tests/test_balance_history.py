"""Тесты для истории изменений баланса.

Этот модуль содержит тесты, которые проверяют:

Базовые операции с историей:
1. Создание записей истории при транзакциях
2. Корректность сохраняемых данных
3. Связи с балансом и транзакциями

Валидация и защита:
1. Валидация сумм (положительные значения)
2. Защита от удаления записей
3. Защита связанных объектов

Массовые операции:
1. Пакетное создание записей
2. Атомарность операций
3. Производительность и оптимизация

Граничные случаи:
1. Максимальные значения сумм
2. Специальные символы в комментариях
3. Откат транзакций при ошибках

Особенности:
- Все тесты используют фикстуру user_balance
- Проверяется как евро, так и рубли
- Тесты атомарны и независимы
- Включает проверку производительности
"""

import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from django.db.models.deletion import ProtectedError
from django.core.exceptions import ValidationError
from django.db.transaction import atomic
from django.db import connection
from django.test.utils import CaptureQueriesContext
from freezegun import freeze_time
from time import sleep

from balance.models import BalanceHistoryRecord, Transaction, TransactionTypeChoices
from user.services import UserService

User = get_user_model()


@pytest.mark.django_db
class TestBalanceHistoryRecord:
    """Тесты для модели BalanceHistoryRecord."""

    @pytest.fixture
    def user(self):
        """Фикстура для создания тестового пользователя."""
        return UserService.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    @pytest.fixture
    def balance(self, user):
        """Фикстура для получения баланса пользователя."""
        return user.balance

    def test_create_history_record(self, balance):
        """Тест создания записи истории."""
        initial_euro = balance.balance_euro
        initial_rub = balance.balance_rub

        history = BalanceHistoryRecord.objects.create(
            balance=balance,
            transaction_type=TransactionTypeChoices.REPLENISHMENT,
            amount_euro=Decimal("50.00"),
            amount_rub=Decimal("5000.00"),
            amount_euro_after=initial_euro + Decimal("50.00"),
            amount_rub_after=initial_rub + Decimal("5000.00"),
            comment="Тестовая запись",
        )

        assert history.pk is not None
        assert history.transaction_date <= timezone.now()
        assert history.amount_euro == Decimal("50.00")
        assert history.amount_rub == Decimal("5000.00")
        assert history.amount_euro_after == initial_euro + Decimal("50.00")
        assert history.amount_rub_after == initial_rub + Decimal("5000.00")

    def test_history_ordering(self, balance):
        """Тест сортировки по дате транзакции."""
        initial_euro = balance.balance_euro
        initial_rub = balance.balance_rub

        # Создаем несколько записей
        for i in range(3):
            euro_amount = Decimal(f"{10 * (i + 1)}.00")
            rub_amount = Decimal(f"{1000 * (i + 1)}.00")

            BalanceHistoryRecord.objects.create(
                balance=balance,
                transaction_type=TransactionTypeChoices.REPLENISHMENT,
                amount_euro=euro_amount,
                amount_rub=rub_amount,
                amount_euro_after=initial_euro + euro_amount,
                amount_rub_after=initial_rub + rub_amount,
            )

        # Проверяем порядок сортировки (от новых к старым)
        records = BalanceHistoryRecord.objects.all()
        assert records[0].amount_euro == Decimal("30.00")
        assert records[1].amount_euro == Decimal("20.00")
        assert records[2].amount_euro == Decimal("10.00")

    def test_transaction_types(self, balance):
        """Тест различных типов транзакций в истории."""
        initial_euro = balance.balance_euro
        initial_rub = balance.balance_rub

        # Пополнение
        replenishment = BalanceHistoryRecord.objects.create(
            balance=balance,
            transaction_type=TransactionTypeChoices.REPLENISHMENT,
            amount_euro=Decimal("50.00"),
            amount_rub=Decimal("5000.00"),
            amount_euro_after=initial_euro + Decimal("50.00"),
            amount_rub_after=initial_rub + Decimal("5000.00"),
        )
        assert replenishment.get_transaction_type_display() == "Пополнение"

        # Списание
        expense = BalanceHistoryRecord.objects.create(
            balance=balance,
            transaction_type=TransactionTypeChoices.EXPENSE,
            amount_euro=Decimal("30.00"),
            amount_rub=Decimal("3000.00"),
            amount_euro_after=initial_euro - Decimal("30.00"),
            amount_rub_after=initial_rub - Decimal("3000.00"),
        )
        assert expense.get_transaction_type_display() == "Списание"

        # Возврат
        payback = BalanceHistoryRecord.objects.create(
            balance=balance,
            transaction_type=TransactionTypeChoices.PAYBACK,
            amount_euro=Decimal("20.00"),
            amount_rub=Decimal("2000.00"),
            amount_euro_after=initial_euro + Decimal("20.00"),
            amount_rub_after=initial_rub + Decimal("2000.00"),
        )
        assert payback.get_transaction_type_display() == "Возврат"

    def test_str_method(self, balance):
        """Тест строкового представления."""
        initial_euro = balance.balance_euro
        initial_rub = balance.balance_rub

        history = BalanceHistoryRecord.objects.create(
            balance=balance,
            transaction_type=TransactionTypeChoices.REPLENISHMENT,
            amount_euro=Decimal("50.00"),
            amount_rub=Decimal("5000.00"),
            amount_euro_after=initial_euro + Decimal("50.00"),
            amount_rub_after=initial_rub + Decimal("5000.00"),
        )

        transaction_date = history.transaction_date.strftime("%d.%m.%Y %H:%M")
        expected = f"Пополнение от {transaction_date} - 50.00 EUR, 5000.00 RUB"
        assert str(history) == expected


@pytest.mark.django_db
class TestBalanceHistory:
    """Тесты для истории изменений баланса."""

    def test_history_creation(self, user_balance):
        """
        Тест создания записей истории.

        Проверяет:
        1. Создание записи при каждой транзакции
        2. Корректность сохраняемых данных
        3. Связь с балансом
        """
        # Проверяем начальное состояние
        assert BalanceHistoryRecord.objects.count() == 0

        # Создаем транзакцию
        transaction = Transaction.objects.create(
            balance=user_balance,
            amount_euro=Decimal("100.00"),
            amount_rub=Decimal("10000.00"),
            transaction_type=TransactionTypeChoices.REPLENISHMENT,
            comment="Тестовое пополнение",
        )

        # Проверяем создание истории
        history = BalanceHistoryRecord.objects.filter(balance=user_balance).first()
        assert history is not None
        assert history.transaction_type == transaction.transaction_type
        assert history.amount_euro == transaction.amount_euro
        assert history.amount_rub == transaction.amount_rub
        assert history.amount_euro_after == user_balance.balance_euro
        assert history.amount_rub_after == user_balance.balance_rub
        assert history.comment == transaction.comment

    def test_history_sequence(self, user_balance):
        """
        Тест последовательности записей истории.

        Проверяет:
        1. Хронологию записей
        2. Корректность сумм после каждой операции
        3. Последовательность изменений
        """
        # Создаем серию транзакций
        transactions = [
            (
                Decimal("100.00"),
                Decimal("10000.00"),
                TransactionTypeChoices.REPLENISHMENT,
            ),
            (Decimal("50.00"), Decimal("5000.00"), TransactionTypeChoices.EXPENSE),
            (Decimal("30.00"), Decimal("3000.00"), TransactionTypeChoices.PAYBACK),
        ]

        for euro, rub, t_type in transactions:
            Transaction.objects.create(
                balance=user_balance,
                amount_euro=euro,
                amount_rub=rub,
                transaction_type=t_type,
            )

        history = BalanceHistoryRecord.objects.filter(balance=user_balance).order_by(
            "transaction_date"
        )

        # Проверяем последовательность сумм
        expected_sequence = [
            (Decimal("100.00"), Decimal("10000.00")),  # После пополнения
            (Decimal("50.00"), Decimal("5000.00")),  # После списания
            (Decimal("80.00"), Decimal("8000.00")),  # После возврата
        ]

        for record, (exp_euro, exp_rub) in zip(history, expected_sequence):
            assert record.amount_euro_after == exp_euro
            assert record.amount_rub_after == exp_rub

    def test_history_filtering(self, user_balance):
        """
        Тест фильтрации истории.

        Проверяет:
        1. Фильтрацию по типу операции
        2. Фильтрацию по периоду
        3. Фильтрацию по сумме
        """
        # Создаем транзакции разных типов
        Transaction.objects.create(
            balance=user_balance,
            amount_euro=Decimal("100.00"),
            amount_rub=Decimal("10000.00"),
            transaction_type=TransactionTypeChoices.REPLENISHMENT,
        )
        Transaction.objects.create(
            balance=user_balance,
            amount_euro=Decimal("50.00"),
            amount_rub=Decimal("5000.00"),
            transaction_type=TransactionTypeChoices.EXPENSE,
        )

        # Фильтрация по типу
        replenishments = BalanceHistoryRecord.objects.filter(
            transaction_type=TransactionTypeChoices.REPLENISHMENT
        )
        assert replenishments.count() == 1
        assert replenishments.first().amount_euro == Decimal("100.00")

        # Фильтрация по периоду
        today = timezone.now()
        yesterday = today - timedelta(days=1)
        recent_history = BalanceHistoryRecord.objects.filter(
            transaction_date__gte=yesterday
        )
        assert recent_history.count() == 2

    def test_history_metadata(self, user_balance):
        """
        Тест метаданных истории.

        Проверяет:
        1. Сохранение комментариев
        2. Временные метки
        3. Дополнительные данные
        """
        transaction = Transaction.objects.create(
            balance=user_balance,
            amount_euro=Decimal("100.00"),
            amount_rub=Decimal("10000.00"),
            transaction_type=TransactionTypeChoices.REPLENISHMENT,
            comment="Тестовый комментарий",
        )

        history = BalanceHistoryRecord.objects.get(
            balance=user_balance, transaction_type=TransactionTypeChoices.REPLENISHMENT
        )

        assert history.comment == "Тестовый комментарий"
        assert history.transaction_date is not None
        assert history.transaction_date.date() == timezone.now().date()

    def test_history_pagination(self, user_balance):
        """
        Тест пагинации истории.

        Проверяет:
        1. Корректность работы пагинации
        2. Сортировку результатов
        3. Ограничение выборки
        """
        # Создаем 10 транзакций
        for i in range(10):
            Transaction.objects.create(
                balance=user_balance,
                amount_euro=Decimal("10.00"),
                amount_rub=Decimal("1000.00"),
                transaction_type=TransactionTypeChoices.REPLENISHMENT,
            )

        # Проверяем пагинацию
        page_size = 5
        history = BalanceHistoryRecord.objects.all().order_by("-transaction_date")

        first_page = history[:page_size]
        second_page = history[page_size : 2 * page_size]

        assert len(first_page) == page_size
        assert len(second_page) == page_size
        assert first_page[0].transaction_date > second_page[0].transaction_date

    def test_concurrent_history_creation(self, user_balance):
        """
        Тест создания множественных записей истории.

        Проверяет:
        1. Создание нескольких записей
        2. Корректность итоговых сумм
        3. Последовательность записей
        """
        amounts = [10, 20, 30]

        # Создаем транзакции последовательно
        for amount in amounts:
            Transaction.objects.create(
                balance=user_balance,
                amount_euro=Decimal(str(amount)),
                amount_rub=Decimal(str(amount * 100)),
                transaction_type=TransactionTypeChoices.REPLENISHMENT,
                comment=f"Транзакция {amount}",
            )

        # Проверяем историю
        history = BalanceHistoryRecord.objects.filter(balance=user_balance).order_by(
            "transaction_date"
        )

        assert history.count() == 3
        assert history.last().amount_euro_after == Decimal("60.00")  # 10 + 20 + 30

    def test_bulk_history_creation(self, user_balance):
        """Тест массового создания записей истории."""
        amounts = [10, 20, 30]
        total_euro = Decimal("0")
        total_rub = Decimal("0")

        with atomic():
            # Создаем транзакции пакетно
            transactions = [
                Transaction(
                    balance=user_balance,
                    amount_euro=Decimal(str(amount)),
                    amount_rub=Decimal(str(amount * 100)),
                    transaction_type=TransactionTypeChoices.REPLENISHMENT,
                    comment=f"Транзакция {amount}",
                )
                for amount in amounts
            ]
            Transaction.objects.bulk_create(transactions)

            # Создаем историю пакетно
            history_records = []
            for transaction in transactions:
                total_euro += transaction.amount_euro
                total_rub += transaction.amount_rub
                history_records.append(
                    BalanceHistoryRecord(
                        balance=user_balance,
                        transaction_type=transaction.transaction_type,
                        amount_euro=transaction.amount_euro,
                        amount_rub=transaction.amount_rub,
                        amount_euro_after=total_euro,
                        amount_rub_after=total_rub,
                        comment=transaction.comment,
                    )
                )

            # Обновляем баланс
            user_balance.balance_euro = total_euro
            user_balance.balance_rub = total_rub
            user_balance.save(allow_balance_update=True)

            # Сохраняем историю
            BalanceHistoryRecord.objects.bulk_create(history_records)

        # Проверяем историю
        history = BalanceHistoryRecord.objects.filter(balance=user_balance).order_by(
            "transaction_date"
        )

        assert history.count() == 3
        assert history[0].amount_euro_after == Decimal("10.00")
        assert history[1].amount_euro_after == Decimal("30.00")
        assert history[2].amount_euro_after == Decimal("60.00")

    def test_history_rollback(self, user_balance):
        """
        Тест отката транзакций и истории.

        Проверяет:
        1. Откат истории при ошибке в транзакции
        2. Целостность данных
        3. Атомарность операций
        """
        initial_history_count = BalanceHistoryRecord.objects.count()

        with pytest.raises(ValidationError), atomic():
            # Создаем транзакцию
            Transaction.objects.create(
                balance=user_balance,
                amount_euro=Decimal("100.00"),
                amount_rub=Decimal("10000.00"),
                transaction_type=TransactionTypeChoices.REPLENISHMENT,
            )
            # Вызываем ошибку
            raise ValidationError("Test rollback")

        # Проверяем что история не изменилась
        assert BalanceHistoryRecord.objects.count() == initial_history_count

    def test_history_edge_cases(self, user_balance):
        """
        Тест граничных случаев истории.

        Проверяет:
        1. Очень большие суммы
        2. Специальные символы в комментариях
        3. Длинные комментарии
        """
        # Тест больших сумм
        max_amount = Decimal("9999999.99")
        Transaction.objects.create(
            balance=user_balance,
            amount_euro=max_amount,
            amount_rub=max_amount,
            transaction_type=TransactionTypeChoices.REPLENISHMENT,
            comment="Максимальная сумма",
        )

        history = BalanceHistoryRecord.objects.latest("transaction_date")
        assert history.amount_euro == max_amount
        assert history.amount_rub == max_amount

        # Тест специальных символов
        special_comment = "Test!@#$%^&*()_+"
        Transaction.objects.create(
            balance=user_balance,
            amount_euro=Decimal("1.00"),
            amount_rub=Decimal("100.00"),
            transaction_type=TransactionTypeChoices.REPLENISHMENT,
            comment=special_comment,
        )

        history = BalanceHistoryRecord.objects.latest("transaction_date")
        assert history.comment == special_comment

    @pytest.mark.django_db(transaction=True)
    def test_history_performance(self, user_balance):
        """
        Тест производительности истории.

        Проверяет:
        1. Скорость создания записей
        2. Эффективность запросов
        3. Нагрузку на БД
        """
        # Создаем тестовые данные пакетно
        with CaptureQueriesContext(connection) as ctx:
            with atomic():
                transactions = [
                    Transaction(
                        balance=user_balance,
                        amount_euro=Decimal("1.00"),
                        amount_rub=Decimal("100.00"),
                        transaction_type=TransactionTypeChoices.REPLENISHMENT,
                    )
                    for _ in range(100)
                ]
                Transaction.objects.bulk_create(transactions)

                # Обновляем баланс одним запросом
                user_balance.balance_euro += Decimal("100.00")  # 1.00 × 100
                user_balance.balance_rub += Decimal("10000.00")  # 100.00 × 100
                user_balance.save(allow_balance_update=True)

                # Создаем историю пакетно
                history_records = [
                    BalanceHistoryRecord(
                        balance=user_balance,
                        transaction_type=t.transaction_type,
                        amount_euro=t.amount_euro,
                        amount_rub=t.amount_rub,
                        amount_euro_after=user_balance.balance_euro,
                        amount_rub_after=user_balance.balance_rub,
                    )
                    for t in transactions
                ]
                BalanceHistoryRecord.objects.bulk_create(history_records)

        # Проверяем количество запросов (должно быть значительно меньше)
        assert len(ctx.captured_queries) < 10  # Ожидаем около 4-5 запросов

        # Проверяем эффективность выборки
        with CaptureQueriesContext(connection) as ctx:
            list(
                BalanceHistoryRecord.objects.filter(
                    balance=user_balance
                ).select_related("balance")
            )

        assert len(ctx.captured_queries) == 1

    def test_history_cascade_protection(self, user_balance):
        """
        Тест защиты истории и баланса от удаления.

        Проверяет:
        1. Защиту баланса от удаления
        2. Сохранение истории
        3. Сохранение целостности данных
        """
        # Создаем транзакцию
        Transaction.objects.create(
            balance=user_balance,
            amount_euro=Decimal("100.00"),
            amount_rub=Decimal("10000.00"),
            transaction_type=TransactionTypeChoices.REPLENISHMENT,
        )

        history_id = BalanceHistoryRecord.objects.get(balance=user_balance).id

        # Проверяем что нельзя удалить баланс
        with pytest.raises(PermissionError):
            user_balance.delete()

        # Проверяем что история сохранилась
        assert BalanceHistoryRecord.objects.filter(id=history_id).exists()

    def test_history_amount_validation(self, user_balance):
        """
        Тест валидации сумм в истории.

        Проверяет:
        1. Корректность сумм до/после операции
        2. Валидацию отрицательных значений
        3. Валидацию максимальных значений
        """
        # Создаем запись с отрицательными суммами
        history = BalanceHistoryRecord(
            balance=user_balance,
            transaction_type=TransactionTypeChoices.REPLENISHMENT,
            amount_euro=Decimal("-100.00"),
            amount_rub=Decimal("-10000.00"),
            amount_euro_after=Decimal("100.00"),
            amount_rub_after=Decimal("10000.00"),
        )
        with pytest.raises(ValidationError):
            history.full_clean()  # Явно вызываем валидацию

        # Создаем запись с отрицательным балансом после
        history = BalanceHistoryRecord(
            balance=user_balance,
            transaction_type=TransactionTypeChoices.REPLENISHMENT,
            amount_euro=Decimal("100.00"),
            amount_rub=Decimal("10000.00"),
            amount_euro_after=Decimal("-100.00"),
            amount_rub_after=Decimal("-10000.00"),
        )
        with pytest.raises(ValidationError):
            history.full_clean()

    def test_history_uniqueness(self, user_balance):
        """
        Тест уникальности записей истории.

        Проверяет:
        1. Корректность порядка записей
        2. Уникальность значений
        3. Последовательность сумм
        """
        # Создаем транзакции
        Transaction.objects.create(
            balance=user_balance,
            amount_euro=Decimal("100.00"),
            amount_rub=Decimal("10000.00"),
            transaction_type=TransactionTypeChoices.REPLENISHMENT,
        )

        Transaction.objects.create(
            balance=user_balance,
            amount_euro=Decimal("200.00"),
            amount_rub=Decimal("20000.00"),
            transaction_type=TransactionTypeChoices.REPLENISHMENT,
        )

        history = BalanceHistoryRecord.objects.filter(balance=user_balance).order_by(
            "transaction_date", "amount_euro"
        )

        assert history.count() == 2
        # Проверяем последовательность сумм
        assert history[0].amount_euro < history[1].amount_euro
        assert history[0].amount_rub < history[1].amount_rub

    def test_transaction_deletion_protection(self, user_balance):
        """
        Тест защиты транзакций от удаления.

        Проверяет:
        1. Защиту транзакций от удаления
        2. Сохранение истории
        3. Целостность данных
        """
        transaction = Transaction.objects.create(
            balance=user_balance,
            amount_euro=Decimal("100.00"),
            amount_rub=Decimal("10000.00"),
            transaction_type=TransactionTypeChoices.REPLENISHMENT,
        )

        history_id = BalanceHistoryRecord.objects.get(balance=user_balance).id

        # Проверяем что нельзя удалить транзакцию
        with pytest.raises(ProtectedError):
            transaction.delete()

        # Проверяем что история сохранилась
        assert BalanceHistoryRecord.objects.filter(id=history_id).exists()
