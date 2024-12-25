"""Тесты пользователя."""

from django.db.models.deletion import ProtectedError
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.contrib.auth import authenticate
import pytest

from user.models import User
from user.services import UserService


@pytest.mark.django_db
class TestUserCreation:
    """Тесты создания пользователя."""

    def test_create_user_with_valid_data(self):
        """Тест создания пользователя с валидными данными."""
        user = UserService.create_user(
            username="testuser", email="test@example.com", password="strongpass123"
        )
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.check_password("strongpass123")
        assert user.balance is not None  # Проверка автосоздания баланса

    def test_create_user_minimal_data(self):
        """Тест создания пользователя только с обязательными полями."""
        user = UserService.create_user(
            username="minimal", email="minimal@test.com", password="minpass123"
        )
        assert user.pk is not None

    def test_create_user_invalid_email(self):
        """Тест создания пользователя с некорректным email."""
        with pytest.raises(ValidationError):
            UserService.create_user(
                username="invalid", email="invalid-email", password="pass123"
            )

    def test_create_user_duplicate_username(self, user):
        """Тест создания пользователя с существующим username."""
        with pytest.raises(IntegrityError):
            UserService.create_user(
                username=user.username,
                email="another@example.com",
                password="pass123454545",
            )

    def test_create_user_duplicate_email(self, user):
        """Тест создания пользователя с существующим email."""
        with pytest.raises(IntegrityError):
            UserService.create_user(
                username="another", email=user.email, password="pass123324уц"
            )

    def test_create_user_short_password(self):
        """Тест создания пользователя с коротким паролем."""
        with pytest.raises(ValidationError):
            UserService.create_user(
                username="shortpass", email="short@test.com", password="pas24уц"
            )

    def test_create_user_without_required_fields(self):
        """Тест создания пользователя без обязательных полей."""
        with pytest.raises(ValidationError):
            UserService.create_user(username="", email="", password="pass123324уц")


@pytest.mark.django_db
class TestUserRead:
    """Тесты чтения пользователя."""

    def test_get_user_by_id(self, user):
        """Тест получения пользователя по ID."""
        retrieved_user = User.objects.get(id=user.id)
        assert retrieved_user == user

    def test_get_user_by_username(self, user):
        """Тест получения пользователя по username."""
        retrieved_user = User.objects.get(username=user.username)
        assert retrieved_user == user

    def test_get_user_by_email(self, user):
        """Тест получения пользователя по email."""
        retrieved_user = User.objects.get(email=user.email)
        assert retrieved_user == user

    def test_get_nonexistent_user(self):
        """Тест получения несуществующего пользователя."""
        with pytest.raises(User.DoesNotExist):
            User.objects.get(username="nonexistent")

    def test_get_all_users(self, user):
        """Тест получения списка всех пользователей."""
        users = User.objects.all()
        assert user in users

    def test_get_user_with_balance(self, user):
        """Тест получения пользователя с балансом."""
        user_with_balance = User.objects.select_related("balance").get(id=user.id)
        assert user_with_balance.balance is not None

    def test_filter_users_by_date(self, user):
        """Тест фильтрации пользователей по дате регистрации."""
        filtered_users = User.objects.filter(date_joined__date=user.date_joined.date())
        assert user in filtered_users

    def test_search_users(self, user):
        """Тест поиска пользователей по частичному совпадению."""
        search_result = User.objects.filter(username__contains=user.username[:3])
        assert user in search_result


@pytest.mark.django_db
class TestUserUpdate:
    """Тесты обновления пользователя."""

    def test_update_username(self, user):
        """Тест обновления username."""
        new_username = "updated_username"
        user.username = new_username
        user.save()
        user.refresh_from_db()
        assert user.username == new_username

    def test_update_email(self, user):
        """Тест обновления email."""
        new_email = "updated@example.com"
        user.email = new_email
        user.save()
        user.refresh_from_db()
        assert user.email == new_email

    def test_update_password(self, user):
        """Тест обновления пароля."""
        new_password = "newpass123"
        user.set_password(new_password)
        user.save()
        assert user.check_password(new_password)

    def test_update_to_existing_username(self, user):
        """Тест обновления на существующий username."""
        existing_user = UserService.create_user(
            username="existing",
            email="existing@test.com",
            password="StrongPass123!",  # Более сложный пароль
        )
        with pytest.raises(IntegrityError):
            user.username = existing_user.username
            user.save()

    def test_update_system_fields(self, user):
        """Тест попытки обновления системных полей."""
        original_date = user.date_joined
        try_date = original_date.replace(year=1999)
        user.date_joined = try_date
        user.save()
        user.refresh_from_db()
        # Проверяем, что дата не изменилась
        assert user.date_joined == original_date
        assert user.date_joined != try_date


@pytest.mark.django_db
class TestUserDelete:
    """Тесты удаления пользователя."""

    def test_delete_user_with_balance(self, user):
        """Тест удаления пользователя с балансом."""
        with pytest.raises(ProtectedError):
            user.delete()

    def test_delete_nonexistent_user(self):
        """Тест удаления несуществующего пользователя."""
        with pytest.raises(User.DoesNotExist):
            User.objects.get(username="nonexistent").delete()


@pytest.mark.django_db
class TestUserAuthentication:
    """Тесты аутентификации пользователя."""

    def test_authenticate_valid_credentials(self, user):
        """Тест аутентификации с правильными данными."""
        authenticated_user = authenticate(
            username=user.username, password="test_password"  # пароль из фикстуры
        )
        assert authenticated_user is not None
        assert authenticated_user == user

    def test_authenticate_invalid_password(self, user):
        """Тест аутентификации с неверным паролем."""
        authenticated_user = authenticate(
            username=user.username, password="wrong_password"
        )
        assert authenticated_user is None

    def test_authenticate_nonexistent_user(self):
        """Тест аутентификации несуществующего пользователя."""
        authenticated_user = authenticate(username="nonexistent", password="somepass")
        assert authenticated_user is None

    def test_password_hashing(self, user):
        """Тест хеширования пароля."""
        assert user.password.startswith("pbkdf2_sha256$")
        assert (
            not user.password == "test_password"
        )  # пароль не хранится в открытом виде
