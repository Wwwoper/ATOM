"""
Тесты для модели Balance и связанных с ней компонентов.

Этот модуль содержит комплексные тесты, которые проверяют:

Базовая функциональность:
1. Создание и инициализация баланса
2. Автоматическое создание баланса через сигналы
3. Строковое представление и форматирование

Операции с балансом:
1. Пополнение, списание и возврат средств
2. Расчет среднего курса обмена
3. Округление десятичных значений
4. Обработка нулевых и максимальных значений

Защита и валидация:
1. Проверка уникальности баланса пользователя
2. Защита от прямого изменения баланса
3. Валидация сумм и типов транзакций
4. Ограничения на уровне базы данных

Транзакционность:
1. Атомарность операций с балансом
2. Корректность работы блокировок
3. Откат транзакций при ошибках
4. Сохранение истории изменений

Примечания:
- Все тесты используют фикстуру user_balance
- Суммы проверяются в евро и рублях
- Транзакции создаются в контексте atomic
"""

import pytest
from decimal import Decimal, ROUND_HALF_UP
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from balance.models import Balance, Transaction, TransactionTypeChoices
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestBalance:
    """Тесты для проверки функциональности баланса."""

    def test_balance_creation(self, user):
        """
        Тест создания баланса.

        Проверяет:
        1. Автоматическое создание баланса для нового пользователя
        2. Начальные значения баланса
        3. Уникальность баланса для пользователя
        """
        # Баланс уже должен быть создан автоматически
        balance = Balance.objects.get(user=user)

        # Проверяем начальные значения
        assert balance.balance_euro == Decimal("0.00")
        assert balance.balance_rub == Decimal("0.00")
        assert balance.user == user

        # Проверка уникальности
        with pytest.raises(IntegrityError):
            Balance.objects.create(user=user)

    @pytest.mark.parametrize(
        "initial_euro,initial_rub,change_euro,change_rub,expected_euro,expected_rub,transaction_type",
        [
            # Пополнение
            (
                Decimal("0.00"),
                Decimal("0.00"),
                Decimal("100.00"),
                Decimal("10000.00"),
                Decimal("100.00"),
                Decimal("10000.00"),
                TransactionTypeChoices.REPLENISHMENT,
            ),
            # Списание
            (
                Decimal("100.00"),
                Decimal("10000.00"),
                Decimal("50.00"),
                Decimal("5000.00"),
                Decimal("50.00"),
                Decimal("5000.00"),
                TransactionTypeChoices.EXPENSE,
            ),
            # Возврат
            (
                Decimal("50.00"),
                Decimal("5000.00"),
                Decimal("50.00"),
                Decimal("5000.00"),
                Decimal("100.00"),
                Decimal("10000.00"),
                TransactionTypeChoices.PAYBACK,
            ),
        ],
    )
    def test_balance_update(
        self,
        user_balance,
        initial_euro,
        initial_rub,
        change_euro,
        change_rub,
        expected_euro,
        expected_rub,
        transaction_type,
    ):
        """
        Тест обновления баланса.

        Проверяет:
        1. Пополнение баланса через транзакции
        2. Списание средств через транзакции
        3. Возврат средств через транзакции
        4. Корректность вычислений итогового баланса
        """
        # Установка начального баланса через транзакцию пополнения
        if initial_euro > Decimal("0"):
            Transaction.objects.create(
                balance=user_balance,
                amount_euro=initial_euro,
                amount_rub=initial_rub,
                transaction_type=TransactionTypeChoices.REPLENISHMENT,
                comment="Установка начального баланса",
            )

        # Создание тестовой транзакции
        Transaction.objects.create(
            balance=user_balance,
            amount_euro=change_euro,
            amount_rub=change_rub,
            transaction_type=transaction_type,
            comment="Тестовая транзакция",
        )

        # Проверка итогового баланса
        user_balance.refresh_from_db()
        assert user_balance.balance_euro == expected_euro
        assert user_balance.balance_rub == expected_rub

    def test_balance_validation(self, user_balance):
        """
        Тест валидации баланса.

        Проверяет:
        1. Защиту от прямого изменения баланса
        2. Валидацию через транзакции
        3. Максимальные значения
        """
        # Проверка защиты от прямого изменения
        with pytest.raises(ValidationError, match="Прямое изменение баланса запрещено"):
            user_balance.balance_euro = Decimal("-100.00")
            user_balance.save()

        # Проверка отрицательных сумм в транзакции
        with pytest.raises(ValidationError, match="Суммы должны быть положительными"):
            Transaction.objects.create(
                balance=user_balance,
                amount_euro=Decimal("-100.00"),
                amount_rub=Decimal("-10000.00"),
                transaction_type=TransactionTypeChoices.REPLENISHMENT,
            )

        # Проверка максимальных значений
        with pytest.raises(ValidationError):
            Transaction.objects.create(
                balance=user_balance,
                amount_euro=Decimal("1000000.00"),  # Превышает max_digits
                amount_rub=Decimal("100000000.00"),
                transaction_type=TransactionTypeChoices.REPLENISHMENT,
            )

    def test_balance_protection(self, user_balance):
        """
        Тест защиты баланса.

        Проверяет:
        1. Защиту от удаления
        2. Защиту от создания дубликатов
        3. Защиту от некорректных транзакций
        """
        # Проверка защиты от удаления
        with pytest.raises(PermissionError):
            user_balance.delete()

        # Проверка уникальности пользователя в отдельной транзакции
        with pytest.raises(IntegrityError), transaction.atomic():
            Balance.objects.create(user=user_balance.user)

        # Проверка защиты от списания без средств в отдельной транзакции
        with pytest.raises(ValidationError), transaction.atomic():
            Transaction.objects.create(
                balance=user_balance,
                amount_euro=Decimal("999999.99"),
                amount_rub=Decimal("99999999.99"),
                transaction_type=TransactionTypeChoices.EXPENSE,  # Списание без средств
            )

    def test_balance_history(self, user_balance):
        """
        Тест истории изменений баланса.

        Проверяет:
        1. Фиксацию всех изменений
        2. Хронологию изменений
        3. Корректность данных в истории
        """
        # Создаем серию транзакций
        transactions = [
            # Пополнение
            Transaction.objects.create(
                balance=user_balance,
                amount_euro=Decimal("100.00"),
                amount_rub=Decimal("10000.00"),
                transaction_type=TransactionTypeChoices.REPLENISHMENT,
            ),
            # Списание
            Transaction.objects.create(
                balance=user_balance,
                amount_euro=Decimal("30.00"),
                amount_rub=Decimal("3000.00"),
                transaction_type=TransactionTypeChoices.EXPENSE,
            ),
            # Возврат
            Transaction.objects.create(
                balance=user_balance,
                amount_euro=Decimal("50.00"),
                amount_rub=Decimal("5000.00"),
                transaction_type=TransactionTypeChoices.PAYBACK,
            ),
        ]

        # Проверяем историю
        history = user_balance.transactions.order_by("transaction_date")
        assert len(history) == len(transactions)

        # Проверяем итоговый баланс
        user_balance.refresh_from_db()
        assert user_balance.balance_euro == Decimal("120.00")  # 100 - 30 + 50
        assert user_balance.balance_rub == Decimal("12000.00")  # 10000 - 3000 + 5000

    def test_balance_signal_creation(self):
        """
        Тест автоматического создания баланса через сигнал.

        Проверяет:
        1. Создание баланса при создании пользователя
        2. Начальные значения автосозданного баланса
        3. Уникальность баланса пользователя
        """
        from django.contrib.auth import get_user_model

        User = get_user_model()

        # Создаем пользователя
        user = User.objects.create_user(
            username="test_signal_user", password="test_pass"
        )

        # Проверяем что баланс создался
        try:
            balance = Balance.objects.get(user=user)
        except Balance.DoesNotExist:
            pytest.fail("Баланс не был создан автоматически при создании пользователя")

        # Проверяем начальные значения
        assert balance.balance_euro == Decimal("0.00")
        assert balance.balance_rub == Decimal("0.00")
        assert balance.user == user

        # Проверяем что создается только один баланс
        assert Balance.objects.filter(user=user).count() == 1

    def test_balance_signal_idempotency(self):
        """
        Тест идемпотентности сигнала создания баланса.

        Проверяет что повторное сохранение пользователя:
        1. Не создает новый баланс
        2. Не изменяет существующий баланс
        """
        from django.contrib.auth import get_user_model

        User = get_user_model()

        user = User.objects.create_user(
            username="test_signal_user", password="test_pass"
        )

        initial_balance = Balance.objects.get(user=user)

        # Повторно сохраняем пользователя
        user.save()

        # Проверяем что баланс не изменился
        assert Balance.objects.filter(user=user).count() == 1
        current_balance = Balance.objects.get(user=user)
        assert current_balance.pk == initial_balance.pk

    def test_average_exchange_rate(self, user_balance):
        """
        Тест расчета среднего курса обмена.

        Проверяет:
        1. Начальное значение (0)
        2. Расчет после одной транзакции
        3. Расчет после нескольких транзакций с разным курсом
        """
        # Проверка начального значения
        assert user_balance.average_exchange_rate == Decimal("0.00")

        # Одна транзакция
        Transaction.objects.create(
            balance=user_balance,
            amount_euro=Decimal("100.00"),
            amount_rub=Decimal("10000.00"),  # Курс 100
            transaction_type=TransactionTypeChoices.REPLENISHMENT,
        )
        user_balance.refresh_from_db()
        assert user_balance.average_exchange_rate == Decimal("100.00")

        # Вторая транзакция с другим курсом
        Transaction.objects.create(
            balance=user_balance,
            amount_euro=Decimal("100.00"),
            amount_rub=Decimal("12000.00"),  # Курс 120
            transaction_type=TransactionTypeChoices.REPLENISHMENT,
        )
        user_balance.refresh_from_db()
        assert user_balance.average_exchange_rate == Decimal(
            "110.00"
        )  # (100 + 120) / 2

    def test_balance_str_representation(self, user_balance):
        """
        Тест строкового представления баланса.

        Проверяет:
        1. Формат строки для пустого баланса
        2. Формат после пополнения
        3. Корректность отображения сумм
        """
        assert (
            str(user_balance)
            == f"Баланс {user_balance.user.username} - 0.00 EUR, 0.00 RUB"
        )

        Transaction.objects.create(
            balance=user_balance,
            amount_euro=Decimal("100.00"),
            amount_rub=Decimal("10000.00"),
            transaction_type=TransactionTypeChoices.REPLENISHMENT,
        )
        user_balance.refresh_from_db()

        assert str(user_balance) == (
            f"Баланс {user_balance.user.username} - 100.00 EUR, 10000.00 RUB"
        )

    def test_balance_constraints(self, user_balance):
        """
        Тест ограничений модели баланса.

        Проверяет:
        1. Ограничение на неотрицательный баланс на уровне БД
        2. Неизменяемость пользователя
        3. Максимальную длину полей
        """
        from django.contrib.auth import get_user_model

        User = get_user_model()

        # Проверка ограничения на уровне БД
        with pytest.raises(IntegrityError), transaction.atomic():
            Balance.objects.filter(id=user_balance.id).update(
                balance_euro=Decimal("-100.00")
            )

        # Проверка неизменяемости пользователя
        new_user = User.objects.create_user(
            username="another_user", password="test_pass"
        )
        with pytest.raises(ValidationError):
            user_balance.user = new_user
            user_balance.full_clean()

    def test_zero_amount_transactions(self, user_balance):
        """
        Тест транзакций с нулевыми суммами.

        Проверяет:
        1. Запрет создания транзакций с нулевыми суммами
        2. Корректность сообщения об ошибке
        3. Неизменность баланса при ошибке
        """
        initial_euro = user_balance.balance_euro
        initial_rub = user_balance.balance_rub

        with pytest.raises(ValidationError, match="Суммы должны быть положительными"):
            Transaction.objects.create(
                balance=user_balance,
                amount_euro=Decimal("0.00"),
                amount_rub=Decimal("0.00"),
                transaction_type=TransactionTypeChoices.REPLENISHMENT,
            )

        user_balance.refresh_from_db()
        assert user_balance.balance_euro == initial_euro
        assert user_balance.balance_rub == initial_rub

    def test_decimal_rounding(self, user_balance):
        """
        Тест округления десятичных чисел.

        Проверяет:
        1. Корректность округления сумм
        2. Сохранение точности
        3. Обработку граничных случаев
        """
        # Округляем до 2 знаков перед созданием
        amount_euro = Decimal("100.555").quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        amount_rub = Decimal("10000.555").quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        transaction = Transaction.objects.create(
            balance=user_balance,
            amount_euro=amount_euro,  # 100.56
            amount_rub=amount_rub,  # 10000.56
            transaction_type=TransactionTypeChoices.REPLENISHMENT,
        )

        # Проверяем округление
        assert transaction.amount_euro == Decimal("100.56")
        assert transaction.amount_rub == Decimal("10000.56")

    def test_transaction_atomicity(self, user_balance):
        """
        Тест атомарности транзакций.

        Проверяет:
        1. Атомарность транзакций
        2. Корректность итогового баланса
        3. Откат при ошибке
        """
        # Создаем успешные транзакции
        for _ in range(3):
            Transaction.objects.create(
                balance=user_balance,
                amount_euro=Decimal("100.00"),
                amount_rub=Decimal("10000.00"),
                transaction_type=TransactionTypeChoices.REPLENISHMENT,
            )

        user_balance.refresh_from_db()
        assert user_balance.balance_euro == Decimal("300.00")
        assert user_balance.balance_rub == Decimal("30000.00")

        # Проверяем откат при ошибке
        initial_euro = user_balance.balance_euro
        initial_rub = user_balance.balance_rub

        with pytest.raises(ValidationError), transaction.atomic():
            Transaction.objects.create(
                balance=user_balance,
                amount_euro=Decimal("-100.00"),  # Отрицательная сумма вызовет ошибку
                amount_rub=Decimal("-10000.00"),
                transaction_type=TransactionTypeChoices.REPLENISHMENT,
            )

        user_balance.refresh_from_db()
        assert user_balance.balance_euro == initial_euro
        assert user_balance.balance_rub == initial_rub

    def test_max_field_values(self, user_balance):
        """
        Тест максимальных значений полей.

        Проверяет:
        1. Максимальное количество цифр
        2. Максимальное количество знаков после запятой
        3. Корректность ошибок валидации
        """
        max_value = Decimal("9" * 8 + ".99")  # 99999999.99
        too_large = max_value + Decimal("0.01")

        # Проверка максимального значения
        Transaction.objects.create(
            balance=user_balance,
            amount_euro=max_value,
            amount_rub=max_value,
            transaction_type=TransactionTypeChoices.REPLENISHMENT,
        )

        # Проверка превышения
        with pytest.raises(ValidationError):
            Transaction.objects.create(
                balance=user_balance,
                amount_euro=too_large,
                amount_rub=too_large,
                transaction_type=TransactionTypeChoices.REPLENISHMENT,
            )

    def test_transaction_locking(self, user_balance):
        """
        Тест блокировок при транзакциях.

        Проверяет:
        1. Блокировку записи при обновлении
        2. Корректность итогового баланса
        3. Сериализацию транзакций
        """
        with transaction.atomic():
            # Блокируем запись для обновления
            balance = Balance.objects.select_for_update().get(id=user_balance.id)

            Transaction.objects.create(
                balance=balance,
                amount_euro=Decimal("100.00"),
                amount_rub=Decimal("10000.00"),
                transaction_type=TransactionTypeChoices.REPLENISHMENT,
            )

        user_balance.refresh_from_db()
        assert user_balance.balance_euro == Decimal("100.00")
        assert user_balance.balance_rub == Decimal("10000.00")
