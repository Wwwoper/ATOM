import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.utils import timezone

from balance.models import Transaction, BalanceHistoryRecord
from balance.services.constants import TransactionTypeChoices
from balance.services.transaction_service import TransactionProcessor
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
