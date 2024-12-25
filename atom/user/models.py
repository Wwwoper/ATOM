"""Модели для приложения user."""

from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models


class PhoneNumberValidator(RegexValidator):
    """Валидатор для номера телефона."""

    regex = r"^\+?1?\d{9,15}$"
    message = 'Номер телефона должен быть в формате: "+999999999". До 15 цифр.'


class User(AbstractUser):
    """Модель пользователя."""

    company_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Название компании",
        db_index=True,
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Телефон",
        validators=[PhoneNumberValidator()],
    )
    address = models.TextField(blank=True, null=True, verbose_name="Адрес")
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Дата регистрации"
    )
    groups = models.ManyToManyField(
        "auth.Group",
        related_name="custom_user_set",
        blank=True,
        verbose_name="Группы",
        help_text="Группы, к которым принадлежит пользователь.",
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        related_name="custom_user_set",
        blank=True,
        verbose_name="Права пользователя",
        help_text="Права пользователя.",
    )
    email = models.EmailField(
        "email address",
        unique=True,
        error_messages={
            "unique": "Пользователь с таким email уже существует.",
        },
    )

    class Meta:
        """Мета-класс для модели User."""

        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        """Строковое представление пользователя."""
        return self.username

    def save(self, *args, **kwargs):
        """Сохранение пользователя с защитой системных полей."""
        if self.pk:  # Если объект уже существует
            # Получаем оригинальный объект из базы
            orig = User.objects.get(pk=self.pk)
            # Восстанавливаем системные поля
            self.date_joined = orig.date_joined
            self.last_login = orig.last_login
        super().save(*args, **kwargs)
