"""Тесты модульного тестирования для модели Balance."""

import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from balance.models import Balance
from user.services import UserService

User = get_user_model()


@pytest.mark.django_db
class TestBalance:
    """Тесты для модели Balance."""

    @pytest.fixture
    def user(self):
        """Фикстура для создания тестового пользователя."""
        return UserService.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_create_balance(self, user):
        """Тест создания баланса с валидными данными."""
        balance = user.balance  # Получаем уже созданный баланс
        balance.balance_euro = Decimal("50.00")
        balance.balance_rub = Decimal("5000.00")
        balance.save(allow_balance_update=True)

        balance.refresh_from_db()
        assert balance.pk is not None
        assert balance.balance_euro == Decimal("50.00")
        assert balance.balance_rub == Decimal("5000.00")
        assert balance.average_exchange_rate == Decimal("100.00")

    def test_balance_constraints(self, user):
        """Тест ограничений на неотрицательный баланс."""
        # Проверяем отрицательный баланс в евро
        balance = user.balance
        balance.balance_euro = Decimal("-10.00")
        balance.balance_rub = Decimal("1000.00")

        with pytest.raises(ValidationError):
            balance.full_clean()  # Проверяем валидацию до сохранения

        # Проверяем отрицательный баланс в рублях
        balance = user.balance
        balance.balance_euro = Decimal("10.00")
        balance.balance_rub = Decimal("-1000.00")

        with pytest.raises(ValidationError):
            balance.full_clean()  # Проверяем валидацию до сохранения

    def test_direct_balance_update(self, balance):
        """Тест запрета прямого изменения баланса."""
        # Попытка прямого изменения
        balance.balance_euro = Decimal("200.00")

        with pytest.raises(ValidationError):
            balance.save()

        # Проверка что разрешено с флагом
        balance.balance_euro = Decimal("200.00")
        balance.save(allow_balance_update=True)

        balance.refresh_from_db()
        assert balance.balance_euro == Decimal("200.00")

    def test_average_exchange_rate(self, user):
        """Тест расчета среднего курса обмена."""
        # Нормальный случай
        balance = user.balance
        balance.balance_euro = Decimal("100.00")
        balance.balance_rub = Decimal("10000.00")
        balance.save(allow_balance_update=True)

        balance.refresh_from_db()
        assert balance.average_exchange_rate == Decimal("100.0000")

        # Нулевой баланс евро
        balance.balance_euro = Decimal("0.00")
        balance.balance_rub = Decimal("1000.00")
        balance.save(allow_balance_update=True)

        balance.refresh_from_db()
        assert balance.average_exchange_rate == Decimal("0.00")

    def test_balance_deletion(self, balance):
        """Тест запрета удаления баланса."""
        with pytest.raises(PermissionError):
            balance.delete()

    def test_str_method(self, balance):
        """Тест строкового представления."""
        expected = f"Баланс {balance.user.username} - {balance.balance_euro} EUR, {balance.balance_rub} RUB"
        assert str(balance) == expected

    def test_user_immutability(self, user):
        """Тест невозможности изменения пользователя баланса."""
        # Получаем баланс пользователя
        balance = user.balance

        # Создаем нового пользователя
        new_user = UserService.create_user(
            username="newuser", email="newuser@example.com", password="testpass123"
        )

        # Пытаемся изменить пользователя
        balance.user = new_user

        # Проверяем, что возникает ошибка валидации
        with pytest.raises(ValidationError) as exc_info:
            balance.clean()

        assert "Невозможно изменить пользователя после создания баланса" in str(
            exc_info.value
        )

        # Проверяем, что пользователь не изменился в базе
        balance.refresh_from_db()
        assert balance.user == user
