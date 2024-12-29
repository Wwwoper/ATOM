"""Тесты для модели User.

Этот модуль содержит тесты для проверки корректности работы модели User,
включая создание пользователей и проверку их данных.
"""

import pytest
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import IntegrityError

from user.services import UserService

User = get_user_model()


@pytest.mark.django_db
class TestUser:
    """Тесты для модели User."""

    @pytest.fixture
    def valid_user_data(self):
        """Фикстура с валидными данными пользователя."""
        return {
            "username": "testuser",
            "email": "test@example.com",
            "password": "securepass123",
            "company_name": "Test Company",
            "phone": "+79991234567",
            "address": "Test Address, 123",
        }

    def test_create_user(self, valid_user_data):
        """Тест создания пользователя с валидными данными."""
        user = UserService.create_user(**valid_user_data)

        assert user.pk is not None
        assert user.username == valid_user_data["username"]
        assert user.email == valid_user_data["email"]
        assert user.company_name == valid_user_data["company_name"]
        assert user.phone == valid_user_data["phone"]
        assert user.address == valid_user_data["address"]
        assert user.check_password(valid_user_data["password"])
        assert user.is_active
        assert not user.is_staff
        assert not user.is_superuser
        assert user.created_at <= timezone.now()

    def test_email_uniqueness(self, valid_user_data):
        """Тест уникальности email."""
        UserService.create_user(**valid_user_data)

        # Пытаемся создать второго пользователя с тем же email
        duplicate_data = valid_user_data.copy()
        duplicate_data["username"] = "another_user"

        with pytest.raises(IntegrityError):
            UserService.create_user(**duplicate_data)

    def test_phone_validation(self, valid_user_data):
        """Тест валидации телефона."""
        # Тест валидных номеров
        valid_phones = ["+79991234567", "89991234567", "+12345678901"]
        for i, phone in enumerate(valid_phones):
            user_data = valid_user_data.copy()
            user_data["username"] = f"testuser{i}"
            user_data["email"] = (
                f"test{i}@example.com"  # Уникальный email для каждого теста
            )
            user_data["phone"] = phone
            user = UserService.create_user(**user_data)
            assert user.phone == phone

        # Тест невалидных номеров
        invalid_phones = ["abc123", "+7999", "+7999123456789012345", "not-a-phone"]
        for i, phone in enumerate(invalid_phones):
            user_data = valid_user_data.copy()
            user_data["username"] = f"invaliduser{i}"
            user_data["email"] = (
                f"invalid{i}@example.com"  # Уникальный email для каждого теста
            )
            user_data["phone"] = phone
            with pytest.raises(ValidationError):
                UserService.create_user(**user_data)
