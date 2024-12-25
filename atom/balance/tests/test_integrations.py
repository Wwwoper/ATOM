"""Тест жизненного цикла баланса."""

from decimal import Decimal
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError


from balance.models import Balance
from django.db.models.deletion import ProtectedError


@pytest.mark.django_db
class TestBalanceCreation:
    """Тесты создания баланса."""

    def test_create_balance_with_valid_values(self, new_user):
        """Проверяет создание баланса с валидными значениями."""
        balance = Balance.objects.create(user=new_user)

        # Обновляем значения баланса
        balance.balance_euro = Decimal("100.00")
        balance.balance_rub = Decimal("10000.00")
        balance.save(allow_balance_update=True)

        # Проверяем значения
        balance.refresh_from_db()
        assert balance.balance_euro == Decimal("100.00")
        assert balance.balance_rub == Decimal("10000.00")

    def test_create_balance_with_zero_values(self, new_user):
        """Проверяет создание баланса с нулевыми значениями."""
        balance = Balance.objects.create(
            user=new_user,
            balance_euro=Decimal("0.00"),
            balance_rub=Decimal("0.00"),
        )
        assert balance.balance_euro == Decimal("0.00")
        assert balance.balance_rub == Decimal("0.00")

    def test_create_balance_with_negative_values(self, new_user):
        """Проверяет создание баланса с отрицательными значениями."""
        with pytest.raises(IntegrityError):
            Balance.objects.create(
                user=new_user,
                balance_euro=Decimal("-100.00"),
                balance_rub=Decimal("-10000.00"),
            )

    def test_create_duplicate_balance(self, balance):
        """Проверяет попытку создания дубликата баланса для одного пользователя."""
        with pytest.raises(IntegrityError):
            Balance.objects.create(
                user=balance.user,
                balance_euro=Decimal("100.00"),
                balance_rub=Decimal("10000.00"),
            )

    def test_create_balance_without_user(self):
        """Проверяет попытку создания баланса без указания пользователя."""
        with pytest.raises(IntegrityError):
            Balance.objects.create(
                balance_euro=Decimal("100.00"),
                balance_rub=Decimal("10000.00"),
            )


@pytest.mark.django_db
class TestBalanceRead:
    """Тесты чтения баланса."""

    def test_get_balance_by_id(self, balance):
        """Проверяет получение баланса по ID."""
        retrieved_balance = Balance.objects.get(id=balance.id)
        assert retrieved_balance == balance

    def test_get_balance_by_user(self, balance):
        """Проверяет получение баланса по пользователю."""
        retrieved_balance = Balance.objects.get(user=balance.user)
        assert retrieved_balance == balance

    def test_get_nonexistent_balance(self):
        """Проверяет получение несуществующего баланса."""
        with pytest.raises(Balance.DoesNotExist):
            Balance.objects.get(id=999999)

    def test_get_all_balances(self, balance):
        """Проверяет получение списка всех балансов."""
        balances = Balance.objects.all()
        assert len(balances) > 0
        assert balance in balances


@pytest.mark.django_db
class TestBalanceUpdate:
    """Тесты обновления баланса."""

    def test_direct_balance_update(self, balance):
        """Проверяет невозможность прямого изменения баланса."""
        balance.balance_euro = Decimal("200.00")
        with pytest.raises(ValidationError):
            balance.save()

    def test_update_with_negative_values(self, balance_with_money):
        """Проверяет попытку обновления баланса отрицательными значениями."""
        balance_with_money.balance_euro = Decimal("-100.00")
        with pytest.raises(IntegrityError):
            balance_with_money.save(allow_balance_update=True)


@pytest.mark.django_db
class TestBalanceDelete:
    """Тесты удаления баланса."""

    def test_delete_balance(self, balance):
        """Проверяет попытку удаления баланса."""
        with pytest.raises(PermissionError):
            balance.delete()

    def test_delete_user_with_balance(self, user, balance):
        """Проверяет удаление пользователя с балансом."""
        with pytest.raises(ProtectedError):
            user.delete()
