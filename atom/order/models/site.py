"""Модель сайта."""

from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Sum
from status.constants import OrderStatusCode


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
        return self.orders.filter(status__code=OrderStatusCode.PAID).aggregate(
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
        """Удаление сайта с проверкой на наличие связанных заказов."""
        if self.orders.exists():
            raise ValidationError(
                "Невозможно удалить сайт, пока с ним связаны заказы. "
                f"Количество связанных заказов: {self.orders.count()}"
            )
        return super().delete(*args, **kwargs)
