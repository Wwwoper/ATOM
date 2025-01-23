"""Модели для работы с сайтами.

Этот модуль содержит модели для:
- Сайтов
- Настроек сайтов
- Статистики по сайтам
"""

from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Sum, Count, Q, Case, When, Value, IntegerField
from status.constants import OrderStatusCode


class Site(models.Model):
    """Модель сайта."""

    name = models.CharField(max_length=100, unique=True, verbose_name="Название сайта")
    url = models.URLField(unique=True, verbose_name="URL сайта")
    organizer_fee_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, verbose_name="Ставка организатора (%)"
    )
    description = models.TextField(blank=True, null=True, verbose_name="Описание сайта")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        """Метаданные модели."""

        verbose_name = "Сайт"
        verbose_name_plural = "Сайты"
        ordering = ["name"]
        indexes = [models.Index(fields=["name"]), models.Index(fields=["url"])]

    def get_orders_aggregated_data(self) -> dict:
        """Получает агрегированные данные по заказам одним запросом."""
        return self.orders.aggregate(
            total_orders=Count("id"),
            paid_orders=Count(
                Case(
                    When(status__code=OrderStatusCode.PAID, then=Value(1)),
                    output_field=IntegerField(),
                )
            ),
            total_profit=Sum(
                Case(
                    When(status__code=OrderStatusCode.PAID, then="profit"),
                    default=Value(0),
                    output_field=models.DecimalField(),
                )
            ),
            unpaid_euro_sum=Sum(
                Case(
                    When(~Q(status__code=OrderStatusCode.PAID), then="amount_euro"),
                    default=Value(0),
                    output_field=models.DecimalField(),
                )
            ),
        )

    @property
    def orders_statistics(self) -> dict:
        """Получение статистики по заказам.

        Returns:
            dict: Словарь со статистикой:
                - total_orders: общее количество заказов
                - paid_orders: количество оплаченных заказов
                - unpaid_orders: количество неоплаченных заказов
                - total_profit: общая прибыль
                - unpaid_euro_sum: сумма в евро неоплаченных заказов
        """
        stats = self.get_orders_aggregated_data()
        return {
            "total_orders": stats["total_orders"] or 0,
            "paid_orders": stats["paid_orders"] or 0,
            "unpaid_orders": (stats["total_orders"] or 0) - (stats["paid_orders"] or 0),
            "total_profit": stats["total_profit"] or Decimal("0.00"),
            "unpaid_euro_sum": stats["unpaid_euro_sum"] or Decimal("0.00"),
        }

    @property
    def total_orders(self):
        """Получение общего количества заказов."""
        return self.orders_statistics["total_orders"]

    @property
    def total_profit(self) -> Decimal:
        """Возвращает общую прибыль от заказов в статусе PAID."""
        return self.orders_statistics["total_profit"]

    @property
    def paid_orders_count(self) -> int:
        """Получение количества оплаченных заказов."""
        return self.orders_statistics["paid_orders"]

    @property
    def unpaid_orders_count(self) -> int:
        """Получение количества неоплаченных заказов."""
        return self.orders_statistics["unpaid_orders"]

    @property
    def unpaid_orders_euro_sum(self) -> Decimal:
        """Возвращает сумму в евро для неоплаченных заказов."""
        return self.orders_statistics["unpaid_euro_sum"]

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
