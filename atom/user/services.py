"""
Сервисы для приложения user.

Этот модуль содержит бизнес-логику для работы с пользователями,
включая создание новых пользователей, управление их данными и балансом.

Основные компоненты:
    - UserService: Сервис для работы с пользователями
    - create_user: Метод создания нового пользователя с балансом

Процесс создания пользователя:
    1. Валидация пароля через django password validators
    2. Проверка обязательных полей (username, email)
    3. Создание пользователя в транзакции
    4. Создание связанного баланса
    5. Возврат созданного пользователя

Правила валидации:
    - Пароль должен соответствовать настройкам Django
    - Username обязателен и должен быть уникальным
    - Email обязателен и должен быть валидным
    - Все поля проходят полную очистку (full_clean)

Примеры использования:
    # Создание нового пользователя
    user = UserService.create_user(
        username="john_doe",
        email="john@example.com",
        password="secure_password",
        first_name="John",
        last_name="Doe"
    )

Примечания:
    - Все операции выполняются в транзакции
    - При ошибке валидации вызывается ValidationError
    - Баланс создается автоматически через сигнал post_save
    - Поддерживает дополнительные поля через **extra_fields
"""

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
        """
        Создает нового пользователя с балансом.

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
            # Баланс создастся автоматически через сигнал
            return user
        except ValueError as e:
            raise ValidationError(str(e))
