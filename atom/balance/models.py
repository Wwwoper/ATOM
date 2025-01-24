from decimal import ROUND_HALF_UP, Decimal, DivisionByZero, InvalidOperation

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db.models.deletion import ProtectedError
from django.db import models
from django.utils import timezone


from .services.constants import TransactionTypeChoices
from .services.balance_processor import BalanceProcessor
from .services.validators import TransactionValidator


class Balance(models.Model):
    """Модель для хранения информации о балансе пользователя."""

    user = models.OneToOneField(
        "user.User",
        on_delete=models.PROTECT,
        related_name="balance",
        verbose_name="Пользователь",
        db_index=True,
    )
    balance_euro = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Баланс в евро",
        validators=[MinValueValidator(Decimal("0.00"))],
        editable=False,
    )
    balance_rub = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Баланс в рублях",
        validators=[MinValueValidator(Decimal("0.00"))],
        editable=False,
    )
    average_exchange_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Средний курс обмена",
    )

    class Meta:
        """Метаданные модели."""

        verbose_name = "Баланс"
        verbose_name_plural = "Баланс"
        constraints = [
            models.CheckConstraint(
                check=models.Q(balance_euro__gte=0) & models.Q(balance_rub__gte=0),
                name="non_negative_balance",
            )
        ]
        permissions = [
            ("can_change_balance", "Can change balance through transactions"),
        ]

    def delete(self, *args, **kwargs):
        """Запрещает удаление баланса."""
        raise PermissionError("Удаление баланса запрещено")

    def save(self, *args, **kwargs):
        """
        Сохраняет баланс и вычисляет средний курс обмена.

        Args:
            *args: Позиционные аргументы
            **kwargs: Именованные аргументы, включая:
                allow_balance_update (bool): Флаг разрешения изменения полей баланса.
                    True - разрешает изменение (используется в сервисах)
                    False - запрещает прямое изменение (по умолчанию)

        Raises:
            ValidationError: Если происходит попытка прямого изменения полей баланса
                без флага allow_balance_update=True

        Example:
            # Через сервис (разрешено):
            balance.save(allow_balance_update=True)

            # Напрямую (запрещено):
            balance.balance_euro = 100
            balance.save()  # Вызовет ValidationError
        """
        if not kwargs.pop("allow_balance_update", False):
            if self.pk:
                old_instance = Balance.objects.get(pk=self.pk)
                if (
                    old_instance.balance_euro != self.balance_euro
                    or old_instance.balance_rub != self.balance_rub
                ):
                    raise ValidationError(
                        "Прямое изменение баланса запрещено. Используйте транзакции."
                    )

        self.average_exchange_rate = self._calculate_average_rate()
        super().save(*args, **kwargs)

    def __str__(self):
        """Возвращает строку, описывающую баланс пользователя."""
        return f"Баланс {self.user.username} - {self.balance_euro} EUR, {self.balance_rub} RUB"

    def _calculate_average_rate(self) -> Decimal:
        """Расчет среднего курса обмена."""
        try:
            if self.balance_euro == 0:
                return Decimal("0.00")
            return (self.balance_rub / self.balance_euro).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_UP
            )
        except (DivisionByZero, InvalidOperation):
            return Decimal("0.00")

    def clean(self):
        """Валидация модели."""
        if self.pk:
            old_balance = Balance.objects.get(pk=self.pk)
            if self.user != old_balance.user:
                raise ValidationError(
                    {"user": "Невозможно изменить пользователя после создания баланса"}
                )


class Transaction(models.Model):
    """Модель для хранения финансовых транзакций."""

    balance = models.ForeignKey(
        "Balance",
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name="Баланс",
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionTypeChoices.choices,
        verbose_name="Тип транзакции",
    )
    amount_euro = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Сумма в евро",
    )
    amount_rub = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Сумма в рублях",
    )
    transaction_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата транзакции",
    )
    comment = models.TextField(
        blank=True,
        verbose_name="Комментарий",
    )

    def clean(self):
        """Валидация транзакции."""
        super().clean()

        # Проверяем наличие сумм перед округлением
        if self.amount_euro is not None:
            self.amount_euro = self.amount_euro.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        if self.amount_rub is not None:
            self.amount_rub = self.amount_rub.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

        # Валидация сумм
        TransactionValidator.validate_amounts(self.amount_euro, self.amount_rub)

        # Валидация баланса для списания
        if self.transaction_type == TransactionTypeChoices.EXPENSE:
            TransactionValidator.validate_balance_for_expense(
                self.balance.balance_euro,
                self.balance.balance_rub,
                self.amount_euro,
                self.amount_rub,
            )

    def save(self, *args, **kwargs):
        """Сохранение транзакции с валидацией."""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        """Возвращает строковое представление транзакции."""
        return f"{self.get_transaction_type_display()} от {self.transaction_date}"

    def delete(self, *args, **kwargs):
        """
        Запрещает удаление транзакции.

        Raises:
            ProtectedError: При любой попытке удаления транзакции
        """
        raise ProtectedError(
            "Cannot delete transaction because it is protected", [self]
        )


class BalanceHistoryRecord(models.Model):
    """Модель для хранения истории изменений баланса."""

    balance = models.ForeignKey(
        Balance,
        on_delete=models.PROTECT,
        verbose_name="Баланс счета",
        related_name="balance_history",
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionTypeChoices.choices,
        verbose_name="Тип транзакции",
    )
    amount_euro = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Количество евро",
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    amount_rub = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Количество рублей",
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    amount_euro_after = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Количество евро после операции",
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    amount_rub_after = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Количество рублей после операции",
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    transaction_date = models.DateTimeField(
        default=timezone.now, verbose_name="Дата транзакции"
    )
    comment = models.TextField(null=True, blank=True, verbose_name="Комменрий")

    class Meta:
        """Метаданные модели."""

        verbose_name = "История баланса"
        verbose_name_plural = "История баланса"
        ordering = ["-transaction_date"]

    def __str__(self):
        """Возвращает строковое представление объекта BalanceHistory."""
        transaction_date = self.transaction_date.strftime("%d.%m.%Y %H:%M")
        return (
            f"{self.get_transaction_type_display()} от {transaction_date} - "
            f"{self.amount_euro:.2f} EUR, {self.amount_rub:.2f} RUB"
        )


"""
Модели для приложения balance.

Этот модуль содержит модели для работы с балансами пользователей:
1. Balance - баланс пользователя
2. Transaction - транзакции по балансу

Особенности:
- Баланс создается автоматически при создании пользователя через сигнал
- Баланс защищен от прямого изменения
- Все изменения происходят через транзакции
"""
