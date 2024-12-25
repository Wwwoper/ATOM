"""Сервисы для приложения user."""

from balance.models import Balance
from django.db import transaction
from user.models import User
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password


class UserService:
    """Сервис для работы с пользователями."""

    @staticmethod
    @transaction.atomic
    def create_user(username: str, email: str, password: str, **extra_fields) -> User:
        """Создает нового пользователя с балансом.

        Args:
            username: Имя пользователя
            email: Email пользователя
            password: Пароль пользователя
            **extra_fields: Дополнительные поля пользователя

        Returns:
            User: Созданный пользователь

        Raises:
            ValidationError: Если данные пользователя не прошли валидацию
        """
        try:
            validate_password(password)
        except ValidationError as e:
            raise ValidationError({"password": e.messages})

        # Проверяем обязательные поля
        if not username:
            raise ValidationError({"username": "Имя пользователя обязательно"})
        if not email:
            raise ValidationError({"email": "Email обязателен"})

        extra_fields["email"] = email

        try:
            user = User.objects.create_user(
                username=username, password=password, **extra_fields
            )
            user.full_clean()
            Balance.objects.create(user=user)
            return user
        except ValueError as e:
            raise ValidationError(str(e))
