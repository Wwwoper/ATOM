import pytest
from django.core.exceptions import ValidationError

from user.validators import PhoneNumberValidator


class TestPhoneNumberValidator:
    """Тесты для валидатора номера телефона."""

    @pytest.fixture
    def validator(self):
        """Фикстура для создания валидатора."""
        return PhoneNumberValidator()

    def test_valid_phone_numbers(self, validator):
        """Тест валидных номеров телефона."""
        valid_phones = [
            "+79991234567",  # Стандартный российский номер с +7
            "89991234567",  # Стандартный российский номер с 8
            "+12345678901",  # Международный номер
            "12345678901",  # Номер без +
        ]

        for phone in valid_phones:
            try:
                cleaned = validator(phone)
                assert len(cleaned) >= 11  # Проверяем длину очищенного номера
            except ValidationError:
                pytest.fail(f"Валидатор не должен вызывать ошибку для номера {phone}")

    def test_invalid_phone_numbers(self, validator):
        """Тест невалидных номеров."""
        invalid_phones = [
            "abc123",  # Буквы в номере
            "+7999",  # Слишком короткий
            "+7999123456789012345",  # Слишком длинный
            "not-a-phone",  # Неправильный формат
            "",  # Пустая строка
            None,  # None
            "+7abc1234567",  # Смесь цифр и букв
            "++79991234567",  # Двойной плюс
            "8+9991234567",  # Плюс в середине
        ]

        for phone in invalid_phones:
            with pytest.raises(ValidationError) as exc_info:
                validator(phone)
            assert "Неверный формат номера телефона" in str(exc_info.value)

    def test_phone_number_cleaning(self, validator):
        """Тест очистки номера от пробелов и других символов."""
        phones_with_spaces = [
            " +79991234567 ",  # Пробелы по краям
            "+7 999 123 45 67",  # Пробелы между цифрами
            "+7-999-123-45-67",  # Дефисы
            "+7(999)1234567",  # Скобки
            "+7 (999) 123-45-67",  # Смесь разных разделителей
        ]

        expected = "+79991234567"
        for phone in phones_with_spaces:
            try:
                cleaned = validator(phone)
                assert cleaned == expected
            except ValidationError:
                pytest.fail(f"Валидатор не должен вызывать ошибку для номера {phone}")
