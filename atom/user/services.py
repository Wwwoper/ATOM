"""Сервисы для приложения user."""

from balance.models import Balance
from django.db import transaction
from user.models import User


class UserService:
    """Сервис для работы с пользователями."""

    @staticmethod
    @transaction.atomic
    def create_user(username, password, **extra_fields):
        """Создает нового пользователя с балансом.

        Args:
            username: Имя пользователя
            password: Пароль пользователя
            **extra_fields: Дополнительные поля пользователя

        Returns:
            User: Созданный пользователь

        Raises:
            ValidationError: Если данные пользователя не прошли валидацию
        """
        user = User.objects.create_user(
            username=username, password=password, **extra_fields
        )
        user.full_clean()
        Balance.objects.create(user=user)
        return user
