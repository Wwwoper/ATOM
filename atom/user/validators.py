"""
Валидаторы для моделей пользователя.

Этот модуль содержит валидаторы для проверки данных пользователя,
включая проверку формата номера телефона и других пользовательских данных.

Основные компоненты:
    - PhoneNumberValidator: Валидатор для проверки формата номера телефона
    - __call__: Метод валидации номера телефона

Процесс валидации номера:
    1. Проверка на пустое значение
    2. Очистка номера от пробелов по краям
    3. Проверка базового формата через регулярное выражение
    4. Очистка от специальных символов
    5. Проверка длины и формата очищенного номера

Правила валидации:
    - Допустимые символы: цифры, пробелы, скобки, дефисы и плюс в начале
    - Длина номера: от 10 до 12 цифр
    - Обязательное наличие значения
    - После очистки должны остаться только цифры и возможный плюс в начале

Примеры использования:
    validator = PhoneNumberValidator()

    # Валидация номера
    cleaned_number = validator('+7 (999) 123-45-67')

    # Использование в модели
    phone = models.CharField(validators=[PhoneNumberValidator()])

Примечания:
    - Валидатор может использоваться как в моделях, так и в формах
    - Возвращает очищенный номер телефона
    - Вызывает ValidationError при некорректном формате
    - Поддерживает международный формат номеров
"""

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

        # Проверяем, что после очистк�� остались только цифры и возможный плюс в начале
        if not re.match(r"^\+?\d+$", cleaned_number):
            raise ValidationError("Неверный формат номера телефона")

        return cleaned_number
