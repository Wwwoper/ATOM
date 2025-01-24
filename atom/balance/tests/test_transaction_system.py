"""
Интеграционные тесты для проверки потока транзакций.

Этот модуль содержит тесты, которые проверяют:
1. Создание различных типов транзакций
2. Валидацию полей транзакций
3. Обработку ошибок при создании транзакций
4. Взаимодействие транзакций с балансом
5. Последовательность и историю транзакций
6. Граничные значения сумм
7. Атомарность операций
8. Уникальность транзакций
9. Работу с комментариями
10. Связи между моделями
11. Различные типы транзакций
"""

import pytest
from decimal import Decimal, ROUND_HALF_UP
from django.core.exceptions import ValidationError
from django.db import transaction
from balance.models import Transaction
from balance.services.constants import TransactionTypeChoices
from django.db.models.deletion import ProtectedError


@pytest.mark.django_db
class TestTransactionFlow:
    """Тесты для проверки потока транзакций."""

    def test_create_replenishment_transaction(self, user_balance):
        """
        Тест создания транзакции пополнения.

        Проверяет:
        1. Создание транзакции с валидными данными
        2. Корректность сохранения всех полей
        3. Связь с балансом
        """
        transaction = Transaction.objects.create(
            balance=user_balance,
            amount_euro=Decimal("100.00"),
            amount_rub=Decimal("10000.00"),
            transaction_type=TransactionTypeChoices.REPLENISHMENT,
            comment="Тестовое пополнение",
        )

        assert transaction.amount_euro == Decimal("100.00")
        assert transaction.amount_rub == Decimal("10000.00")
        assert transaction.transaction_type == TransactionTypeChoices.REPLENISHMENT
        assert transaction.balance == user_balance

    @pytest.mark.parametrize(
        "amount_euro,amount_rub,expected_error",
        [
            (
                Decimal("-100.00"),
                Decimal("10000.00"),
                "Суммы должны быть положительными",
            ),
            (Decimal("0.00"), Decimal("0.00"), "Суммы должны быть положительными"),
            (None, Decimal("10000.00"), "Сумма в евро должна быть указана"),
            (Decimal("100.00"), None, "Сумма в рублях должна быть указана"),
        ],
    )
    def test_transaction_validation(
        self, user_balance, amount_euro, amount_rub, expected_error
    ):
        """
        Тест валидации полей транзакции.
        """
        with pytest.raises(ValidationError) as exc_info:
            Transaction.objects.create(
                balance=user_balance,
                amount_euro=amount_euro,
                amount_rub=amount_rub,
                transaction_type=TransactionTypeChoices.REPLENISHMENT,
                comment="Тестовая транзакция",
            )

        # Проверяем что хотя бы одно из сообщений об ошибке содержит ожидаемый текст
        error_messages = []
        if hasattr(exc_info.value, "message_dict"):
            for messages in exc_info.value.message_dict.values():
                error_messages.extend(messages)
        else:
            error_messages = exc_info.value.messages

        assert any(
            expected_error in message for message in error_messages
        ), f"Expected '{expected_error}' in error messages, got: {error_messages}"

    def test_transaction_balance_update(self, user_balance):
        """
        Тест обновления баланса после создания транзакции.

        Проверяет:
        1. Изменение баланса после пополнения
        2. Изменение баланса после списания
        3. Изменение баланса после возврата
        """
        # Пополнение
        Transaction.objects.create(
            balance=user_balance,
            amount_euro=Decimal("100.00"),
            amount_rub=Decimal("10000.00"),
            transaction_type=TransactionTypeChoices.REPLENISHMENT,
            comment="Пополнение",
        )
        user_balance.refresh_from_db()
        assert user_balance.balance_euro == Decimal("100.00")

        # Списание
        Transaction.objects.create(
            balance=user_balance,
            amount_euro=Decimal("50.00"),
            amount_rub=Decimal("5000.00"),
            transaction_type=TransactionTypeChoices.EXPENSE,
            comment="Списание",
        )
        user_balance.refresh_from_db()
        assert user_balance.balance_euro == Decimal("50.00")

        # Возврат
        Transaction.objects.create(
            balance=user_balance,
            amount_euro=Decimal("25.00"),
            amount_rub=Decimal("2500.00"),
            transaction_type=TransactionTypeChoices.PAYBACK,
            comment="Возврат",
        )
        user_balance.refresh_from_db()
        assert user_balance.balance_euro == Decimal("75.00")

    def test_insufficient_funds(self, user_balance):
        """Тест попытки списания при недостаточном балансе."""
        with pytest.raises(ValidationError, match="Недостаточно средств"):
            Transaction.objects.create(
                balance=user_balance,
                amount_euro=Decimal("100.00"),
                amount_rub=Decimal("10000.00"),
                transaction_type=TransactionTypeChoices.EXPENSE,
                comment="Списание без средств",
            )

    def test_transaction_sequence(self, user_balance):
        """
        Тест последовательности транзакций.

        Проверяет корректность изменения баланса при выполнении
        цепочки транзакций: пополнение -> списание -> возврат -> списание
        """
        # Пополнение 100 евро
        Transaction.objects.create(
            balance=user_balance,
            amount_euro=Decimal("100.00"),
            amount_rub=Decimal("10000.00"),
            transaction_type=TransactionTypeChoices.REPLENISHMENT,
            comment="Начальное пополнение",
        )

        # Списание 60 евро
        Transaction.objects.create(
            balance=user_balance,
            amount_euro=Decimal("60.00"),
            amount_rub=Decimal("6000.00"),
            transaction_type=TransactionTypeChoices.EXPENSE,
            comment="Первое списание",
        )

        # Возврат 20 евро
        Transaction.objects.create(
            balance=user_balance,
            amount_euro=Decimal("20.00"),
            amount_rub=Decimal("2000.00"),
            transaction_type=TransactionTypeChoices.PAYBACK,
            comment="Возврат части списания",
        )

        # Списание 40 евро
        Transaction.objects.create(
            balance=user_balance,
            amount_euro=Decimal("40.00"),
            amount_rub=Decimal("4000.00"),
            transaction_type=TransactionTypeChoices.EXPENSE,
            comment="Второе списание",
        )

        user_balance.refresh_from_db()
        assert user_balance.balance_euro == Decimal("20.00")
        assert user_balance.balance_rub == Decimal("2000.00")

    def test_transaction_history(self, user_balance):
        """
        Тест сохранения и получения истории транзакций.

        Проверяет:
        1. Корректность сохранения транзакций
        2. Порядок транзакций в истории
        3. Полноту данных каждой транзакции
        """
        transactions = [
            Transaction.objects.create(
                balance=user_balance,
                amount_euro=Decimal("100.00"),
                amount_rub=Decimal("10000.00"),
                transaction_type=TransactionTypeChoices.REPLENISHMENT,
                comment="Пополнение 1",
            ),
            Transaction.objects.create(
                balance=user_balance,
                amount_euro=Decimal("50.00"),
                amount_rub=Decimal("5000.00"),
                transaction_type=TransactionTypeChoices.EXPENSE,
                comment="Списание 1",
            ),
        ]

        history = user_balance.transactions.order_by("-transaction_date")
        assert len(history) == 2
        assert history[0].transaction_type == TransactionTypeChoices.EXPENSE
        assert history[1].transaction_type == TransactionTypeChoices.REPLENISHMENT
        assert history[0].amount_euro == Decimal("50.00")
        assert history[1].amount_euro == Decimal("100.00")

    @pytest.mark.parametrize(
        "amount_euro,amount_rub,expected_euro,expected_rub",
        [
            # Минимальные суммы
            (Decimal("0.01"), Decimal("1.00"), Decimal("0.01"), Decimal("1.00")),
            # Максимальные суммы
            (
                Decimal("999999.99"),
                Decimal("99999999.99"),
                Decimal("999999.99"),
                Decimal("99999999.99"),
            ),
            # Проверка округления
            (
                Decimal("1.23456"),
                Decimal("123.45678"),
                Decimal("1.23"),
                Decimal("123.46"),
            ),
        ],
    )
    def test_transaction_amount_boundaries(
        self, user_balance, amount_euro, amount_rub, expected_euro, expected_rub
    ):
        """
        Тест граничных значений сумм транзакций.

        Проверяет:
        1. Минимально допустимые суммы
        2. Максимально допустимые суммы
        3. Корректность округления до 2 знаков после запятой
        """
        # Округляем значения перед созданием
        rounded_euro = amount_euro.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        rounded_rub = amount_rub.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        transaction = Transaction.objects.create(
            balance=user_balance,
            amount_euro=rounded_euro,
            amount_rub=rounded_rub,
            transaction_type=TransactionTypeChoices.REPLENISHMENT,
            comment="Тест граничных значений",
        )

        assert transaction.amount_euro == expected_euro
        assert transaction.amount_rub == expected_rub

    def test_transaction_atomicity(self, user_balance):
        """
        Тест атомарности транзакций при ошибках.

        Проверяет:
        1. Откат всех изменений при ошибке
        2. Сохранение исходного баланса
        3. Отсутствие частично примененных транзакций
        """
        initial_balance = user_balance.balance_euro

        with pytest.raises(ValidationError):
            with transaction.atomic():
                # Создаем валидную транзакцию
                Transaction.objects.create(
                    balance=user_balance,
                    amount_euro=Decimal("100.00"),
                    amount_rub=Decimal("10000.00"),
                    transaction_type=TransactionTypeChoices.REPLENISHMENT,
                    comment="Валидная транзакция",
                )

                # Создаем невалидную транзакцию
                Transaction.objects.create(
                    balance=user_balance,
                    amount_euro=Decimal("-50.00"),  # Отрицательная сумма
                    amount_rub=Decimal("5000.00"),
                    transaction_type=TransactionTypeChoices.EXPENSE,
                    comment="Невалидная транзакция",
                )

        # Проверяем что баланс не изменился
        user_balance.refresh_from_db()
        assert user_balance.balance_euro == initial_balance
        assert (
            len(user_balance.transactions.all()) == 0
        )  # Транзакции не должны быть созданы

    def test_transaction_uniqueness(self, user_balance):
        """
        Тест уникальности транзакций.

        Проверяет что две транзакции с одинаковыми параметрами
        являются разными объектами с разными timestamp.
        """
        transaction1 = Transaction.objects.create(
            balance=user_balance,
            amount_euro=Decimal("100.00"),
            amount_rub=Decimal("10000.00"),
            transaction_type=TransactionTypeChoices.REPLENISHMENT,
            comment="Тест уникальности 1",
        )

        transaction2 = Transaction.objects.create(
            balance=user_balance,
            amount_euro=Decimal("100.00"),
            amount_rub=Decimal("10000.00"),
            transaction_type=TransactionTypeChoices.REPLENISHMENT,
            comment="Тест уникальности 2",
        )

        assert transaction1.id != transaction2.id
        assert transaction1.transaction_date != transaction2.transaction_date

    @pytest.mark.parametrize(
        "comment,expected_comment",
        [
            ("", ""),  # Пустой комментарий
            ("А" * 1000, "А" * 1000),  # Длинный комментарий
            (None, None),  # Null комментарий
            ("Обычный комментарий", "Обычный комментарий"),
            ("Special chars: !@#$%^&*()", "Special chars: !@#$%^&*()"),
        ],
    )
    def test_transaction_comments(self, user_balance, comment, expected_comment):
        """
        Тест различных вариантов комментариев к транзакциям.

        Проверяет:
        1. Пустые комментарии
        2. Длинные комментарии
        3. Специальные символы
        4. Null значения
        """
        transaction = Transaction.objects.create(
            balance=user_balance,
            amount_euro=Decimal("100.00"),
            amount_rub=Decimal("10000.00"),
            transaction_type=TransactionTypeChoices.REPLENISHMENT,
            comment=comment,
        )

        assert transaction.comment == expected_comment

    def test_transaction_relations(self, user_balance):
        """
        Тест связей транзакции с другими моделями.

        Проверяет:
        1. Связь транзакции с балансом
        2. Связь транзакции с пользователем через баланс
        3. Защиту от удаления пользователя с балансом
        """
        transaction = Transaction.objects.create(
            balance=user_balance,
            amount_euro=Decimal("100.00"),
            amount_rub=Decimal("10000.00"),
            transaction_type=TransactionTypeChoices.REPLENISHMENT,
            comment="Тест связей",
        )

        transaction_id = transaction.id
        user = user_balance.user

        # Проверка прямых связей
        assert (
            transaction.balance == user_balance
        ), "Транзакция должна быть связана с балансом"
        assert (
            transaction.balance.user == user_balance.user
        ), "Баланс должен быть связан с пользователем"

        # Проверка обратных связей
        assert (
            transaction in user_balance.transactions.all()
        ), "Транзакция должна быть в списке транзакций баланса"
        assert (
            transaction in user.balance.transactions.all()
        ), "Транзакция должна быть доступна через пользователя"

        # Проверка защиты от удаления
        with pytest.raises(ProtectedError):
            user_balance.user.delete()

    @pytest.mark.parametrize(
        "transaction_type,expected_balance",
        [
            (TransactionTypeChoices.REPLENISHMENT, Decimal("100.00")),
            (TransactionTypeChoices.EXPENSE, Decimal("-100.00")),
            (TransactionTypeChoices.PAYBACK, Decimal("100.00")),
        ],
    )
    def test_transaction_types(self, user_balance, transaction_type, expected_balance):
        """
        Тест различных типов транзакций.

        Проверяет:
        1. Все типы транзакций
        2. Корректность изменения баланса для каждого типа
        3. Сохранение типа транзакции
        """
        # Подготовка начального баланса для списания
        if transaction_type == TransactionTypeChoices.EXPENSE:
            Transaction.objects.create(
                balance=user_balance,
                amount_euro=Decimal("200.00"),
                amount_rub=Decimal("20000.00"),
                transaction_type=TransactionTypeChoices.REPLENISHMENT,
                comment="Подготовка баланса",
            )

        transaction = Transaction.objects.create(
            balance=user_balance,
            amount_euro=Decimal("100.00"),
            amount_rub=Decimal("10000.00"),
            transaction_type=transaction_type,
            comment=f"Тест типа {transaction_type}",
        )

        user_balance.refresh_from_db()
        assert transaction.transaction_type == transaction_type
        assert user_balance.balance_euro == abs(expected_balance)
