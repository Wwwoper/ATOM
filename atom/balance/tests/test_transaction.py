import pytest
from decimal import Decimal
from django.db import transaction as db_transaction
from balance.models import Transaction, Balance
from balance.services.constants import TransactionTypeChoices
from django.db.models.deletion import ProtectedError


@pytest.mark.django_db
class TestTransaction:
    """Тесты для модели Transaction."""

    @pytest.fixture(autouse=True)
    def setup(self, django_db_setup):
        """Очистка транзакций перед каждым тестом."""
        Transaction.objects.all().delete()

    def test_transaction_types(self, user, balance):
        """
        Тест создания транзакций разных типов.

        Проверяем:
        1. Создание транзакций каждого типа
        2. Корректность сохранения типов
        3. Точное количество транзакций
        """
        # Создаем транзакции разных типов
        with db_transaction.atomic():
            transactions = [
                Transaction.objects.create(
                    balance=balance,
                    transaction_type=TransactionTypeChoices.REPLENISHMENT,
                    amount_euro=Decimal("100.00"),
                    amount_rub=Decimal("10000.00"),
                ),
                Transaction.objects.create(
                    balance=balance,
                    transaction_type=TransactionTypeChoices.EXPENSE,
                    amount_euro=Decimal("50.00"),
                    amount_rub=Decimal("5000.00"),
                ),
                Transaction.objects.create(
                    balance=balance,
                    transaction_type=TransactionTypeChoices.PAYBACK,
                    amount_euro=Decimal("30.00"),
                    amount_rub=Decimal("3000.00"),
                ),
            ]

        # Проверяем количество транзакций
        assert (
            Transaction.objects.count() == 3
        ), f"Ожидалось 3 транзакции, получено {Transaction.objects.count()}"

        # Проверяем типы транзакций
        transaction_types = set(
            Transaction.objects.values_list("transaction_type", flat=True)
        )
        expected_types = {
            TransactionTypeChoices.REPLENISHMENT,
            TransactionTypeChoices.EXPENSE,
            TransactionTypeChoices.PAYBACK,
        }
        assert transaction_types == expected_types, (
            f"Ожидаемые типы: {expected_types}, "
            f"полученные типы: {transaction_types}"
        )

        # Проверяем суммы транзакций
        for trans in transactions:
            db_transaction_obj = Transaction.objects.get(pk=trans.pk)
            assert db_transaction_obj.amount_euro == trans.amount_euro
            assert db_transaction_obj.amount_rub == trans.amount_rub

    def test_transaction_deletion_protection(self, user, balance):
        """Тест запрета удаления транзакции при существующем балансе."""
        # Создаем транзакцию
        transaction = Transaction.objects.create(
            balance=balance,
            transaction_type=TransactionTypeChoices.REPLENISHMENT,
            amount_euro=Decimal("100.00"),
            amount_rub=Decimal("10000.00"),
        )

        # Проверяем, что транзакция создана
        assert Transaction.objects.filter(pk=transaction.pk).exists()

        # Пытаемся удалить транзакцию
        with pytest.raises(ProtectedError) as exc_info:
            transaction.delete()

        # Проверяем сообщение об ошибке
        assert "Cannot delete transaction" in str(exc_info.value)

        # Проверяем, что транзакция все еще существует
        assert Transaction.objects.filter(pk=transaction.pk).exists()

        # Проверяем, что связанный баланс также ��уществует
        assert Balance.objects.filter(pk=balance.pk).exists()
