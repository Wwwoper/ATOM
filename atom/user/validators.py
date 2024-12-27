"""Валидаторы для моделей пользователя."""

import re
from django.core.exceptions import ValidationError


class PhoneNumberValidator:
    """Валидатор для проверки формата номера телефона."""

    def __init__(self):
        """Инициализация валидатора."""
        # Разрешаем цифры, пробелы, скобки, дефисы и плюс в начале
        self.pattern = re.compile(r"^\+?[\d\s\(\)-]+$")

    def __call__(self, value):
        """
        Проверяет формат номера телефона.

        Args:
            value: Номер телефона для проверки

        Returns:
            str: Очищенный номер телефона

        Raises:
            ValidationError: Если номер не соответствует формату
        """
        if value is None or value == "":
            raise ValidationError("Неверный формат номера телефона")

        value = str(value).strip()  # Убираем пробелы по краям

        # Проверяем базовый формат
        if not self.pattern.match(value):
            raise ValidationError("Неверный формат номера телефона")

        # Очищаем номер от пробелов и других символов
        cleaned_number = re.sub(r"[\s\(\)-]", "", value)

        # Проверяем длину после очистки
        if not (10 <= len(cleaned_number) <= 12):
            raise ValidationError("Неверный формат номера телефона")

        # Проверяем, что после очистки остались только цифры и возможный плюс в начале
        if not re.match(r"^\+?\d+$", cleaned_number):
            raise ValidationError("Неверный формат номера телефона")

        return cleaned_number
