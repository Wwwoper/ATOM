"""Модели приложения orders."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.utils import timezone
from status.services.constants import get_status_codes

from .services.order_status_service import OrderStatusService


class Site(models.Model):
    """Модель сайта."""

    name = models.CharField(max_length=100, unique=True, verbose_name="Название сайта")
    url = models.URLField(unique=True, verbose_name="URL сайта")
    organizer_fee_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, verbose_name="Ставка организатора (%)"
    )
    description = models.TextField(blank=True, null=True, verbose_name="Описание сайта")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата оздания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        """Метаданные модели."""

        verbose_name = "Сайт"
        verbose_name_plural = "Сайты"
        ordering = ["name"]
        indexes = [models.Index(fields=["name"]), models.Index(fields=["url"])]

    @property
    def total_orders(self):
        """Получение общего количества заказов."""
        return self.orders.count()

    @property
    def total_profit(self) -> Decimal:
        """Возвращает общую прибыль от заказов в статусе PAID."""
        from order.models import (
            Order,
        )  # Импорт здесь во избежание циклических импортов

        status_codes = get_status_codes(Order)
        return self.orders.filter(status__code=status_codes["paid"]).aggregate(
            total=Sum("profit")
        )["total"] or Decimal("0.00")

    def clean(self):
        """Валидация модели."""
        if self.organizer_fee_percentage < 0 or self.organizer_fee_percentage > 100:
            raise ValidationError(
                {"organizer_fee_percentage": "Процент комиссии должен быть между 0 100"}
            )

    def save(self, *args, **kwargs):
        """Сохранение модели."""
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        """Строковое представление модели."""
        return self.name

    def delete(self, *args, **kwargs):
        """
        Удаление сайта с проверкой на наличие связанных заказов.

        Raises:
            ValidationError: Если есть связанные заказы
        """
        if self.orders.exists():
            raise ValidationError(
                "Невозможно удалить сайт, пока с ним связаны заказы. "
                f"Количество связанных заказов: {self.orders.count()}"
            )
        return super().delete(*args, **kwargs)


class Order(models.Model):
    """Модель заказа."""

    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.PROTECT,
        verbose_name="Пользователь",
        related_name="orders",
    )
    site = models.ForeignKey(
        Site, on_delete=models.PROTECT, related_name="orders", verbose_name="Сайт"
    )
    status = models.ForeignKey(
        "status.Status",
        on_delete=models.PROTECT,
        verbose_name="Статус заказа",
        limit_choices_to={"group__code": "ORDER_STATUS_CONFIG"},
        related_name="orders_with_status",
    )
    internal_number = models.CharField(
        max_length=50, unique=True, verbose_name="Внутренний номер заказа"
    )
    external_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        verbose_name="Номер заказа на сайте",
    )
    amount_euro = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Сумма в евро"
    )
    amount_rub = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Сумма в рублях"
    )
    created_at = models.DateField(default=timezone.now, verbose_name="Дата создания")
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата оплаты")
    expense = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=False,
        blank=True,
        verbose_name="Расходы в рублях",
        default=Decimal("0.00"),
    )
    profit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=False,
        blank=True,
        verbose_name="Прибыль в рублях",
        default=Decimal("0.00"),
    )
    comment = models.TextField(blank=True, null=True, verbose_name="Комментарий")

    class Meta:
        """Метаданные модели."""

        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["internal_number"]),
            models.Index(fields=["external_number"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        """Строковое представление модели."""
        return f"Заказ №{self.internal_number} ({self.status})"

    def clean(self):
        """Валидация модели."""
        if not self.status_id:
            raise ValidationError({"status": "Статус заказа обязателен"})

        if self.amount_euro <= 0:
            raise ValidationError({"amount_euro": "Цена в евро должна быть больше 0"})
        if self.amount_rub <= 0:
            raise ValidationError({"amount_rub": "Цена в рублях должна быть больше 0"})

        # Проверка изменения пользователя
        if self.pk:
            old_order = Order.objects.get(pk=self.pk)
            if self.user != old_order.user:
                raise ValidationError(
                    {"user": "Невозможно изменить пользователя после создания заказа"}
                )

            # Проверка изменения сумм и статусов после оплаты
            if old_order.status.code == "paid":
                # Проверка изменения сумм
                if (
                    self.amount_euro != old_order.amount_euro
                    or self.amount_rub != old_order.amount_rub
                ):
                    raise ValidationError(
                        {
                            "amount_euro": "Невозможно изменить сумму после оплаты",
                            "amount_rub": "Невозможно изменить сумму после оплаты",
                        }
                    )

                # Проверка допустимости перехода статуса
                if self.status != old_order.status:
                    allowed_transitions = (
                        old_order.status.group.allowed_status_transitions.get(
                            old_order.status.code, []
                        )
                    )
                    if self.status.code not in allowed_transitions:
                        raise ValidationError(
                            {
                                "status": f"Недопустимый переход из статуса '{old_order.status.name}' в '{self.status.name}'"
                            }
                        )

    def save(self, *args, **kwargs):
        """Сохранение модели."""
        skip_status_processing = kwargs.pop("skip_status_processing", False)

        status_service = OrderStatusService()

        # Обработка статуса
        status_service.process_status_change(self, skip_status_processing)

        self.clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        Удаление заказа с проверкой статуса.

        Raises:
            ValidationError: Если заказ оплачен
        """
        if self.status.code == "paid":
            raise ValidationError("Невозможно удалить оплаченный заказ")
        return super().delete(*args, **kwargs)
