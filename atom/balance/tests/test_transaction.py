import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone

from balance.models import Transaction
from balance.services.constants import TransactionTypeChoices
from balance.services.transaction_service import TransactionProcessor
from user.services import UserService

User = get_user_model()


@pytest.mark.django_db
class TestTransaction:
    """Тесты для модели Transaction."""

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

    def test_create_transaction(self, balance):
        """Тест создания транзакции с валидными данными."""
        transaction = Transaction.objects.create(
            balance=balance,
            transaction_type=TransactionTypeChoices.REPLENISHMENT,
            amount_euro=Decimal("50.00"),
            amount_rub=Decimal("5000.00"),
            comment="Тестовое пополнение",
        )

        assert transaction.pk is not None
        assert transaction.transaction_date <= timezone.now()
        assert transaction.amount_euro == Decimal("50.00")
        assert transaction.amount_rub == Decimal("5000.00")

    def test_amount_validation(self, balance):
        """Тест валидации сумм."""
        # Проверка отрицательных сумм
        with pytest.raises(ValidationError):
            Transaction.objects.create(
                balance=balance,
                transaction_type=TransactionTypeChoices.REPLENISHMENT,
                amount_euro=Decimal("-50.00"),
                amount_rub=Decimal("5000.00"),
            )

        with pytest.raises(ValidationError):
            Transaction.objects.create(
                balance=balance,
                transaction_type=TransactionTypeChoices.REPLENISHMENT,
                amount_euro=Decimal("50.00"),
                amount_rub=Decimal("-5000.00"),
            )

        # Проверка нулевых cумм
        with pytest.raises(ValidationError):
            Transaction.objects.create(
                balance=balance,
                transaction_type=TransactionTypeChoices.REPLENISHMENT,
                amount_euro=Decimal("0.00"),
                amount_rub=Decimal("5000.00"),
            )

    def test_transaction_processing(self, balance):
        """Тест обработки транзакции."""
        initial_balance_euro = Decimal("0.00")
        initial_balance_rub = Decimal("0.00")

        # Устанавливаем начальный баланс
        balance.balance_euro = initial_balance_euro
        balance.balance_rub = initial_balance_rub
        balance.save(allow_balance_update=True)

        # Создаем данные для транзакции
        transaction_data = {
            "balance": balance,
            "transaction_type": TransactionTypeChoices.REPLENISHMENT,
            "amount_euro": Decimal("50.00"),
            "amount_rub": Decimal("5000.00"),
            "comment": "Тестовое пополнение",
        }

        # Выполняем транзакцию через сервис
        transaction = TransactionProcessor.execute_transaction(transaction_data)

        balance.refresh_from_db()
        assert balance.balance_euro == initial_balance_euro + Decimal("50.00")
        assert balance.balance_rub == initial_balance_rub + Decimal("5000.00")

    def test_transaction_types(self, balance):
        """Тест различных типов транзакций."""
        # Пополнение
        replenishment = Transaction.objects.create(
            balance=balance,
            transaction_type=TransactionTypeChoices.REPLENISHMENT,
            amount_euro=Decimal("50.00"),
            amount_rub=Decimal("5000.00"),
        )
        assert replenishment.get_transaction_type_display() == "Пополнение"

        # Списание
        expense = Transaction.objects.create(
            balance=balance,
            transaction_type=TransactionTypeChoices.EXPENSE,
            amount_euro=Decimal("30.00"),
            amount_rub=Decimal("3000.00"),
        )
        assert expense.get_transaction_type_display() == "Списание"

        # Возврат
        payback = Transaction.objects.create(
            balance=balance,
            transaction_type=TransactionTypeChoices.PAYBACK,
            amount_euro=Decimal("20.00"),
            amount_rub=Decimal("2000.00"),
        )
        assert payback.get_transaction_type_display() == "Возврат"

        assert Transaction.objects.count() == 3

    def test_str_method(self, balance):
        """Тест строкового представления."""
        transaction = Transaction.objects.create(
            balance=balance,
            transaction_type=TransactionTypeChoices.REPLENISHMENT,
            amount_euro=Decimal("50.00"),
            amount_rub=Decimal("5000.00"),
        )

        expected = f"Пополнение от {transaction.transaction_date}"
        assert str(transaction) == expected
