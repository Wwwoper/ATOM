"""Модели для работы с заказами.

Этот модуль содержит модели для:
- Заказов
- Статусов заказов
- Связанных сущностей
"""

from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from status.constants import OrderStatusCode
import logging

from ..services.order_status_service import OrderStatusService
from ..services.order_validation_service import OrderValidationService
from .querysets import OrderQuerySet
from .site import Site

logger = logging.getLogger(__name__)


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
        "Внутренний номер заказа",
        max_length=255,
        unique=True,
        db_index=True,
    )
    external_number = models.CharField(
        "Внешний номер заказа",
        max_length=255,
        unique=True,
    )
    amount_euro = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Сумма в евро"
    )
    amount_rub = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Сумма в рублях"
    )
    created_at = models.DateField(
        default=timezone.localdate, verbose_name="Дата создания"
    )
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

    objects = OrderQuerySet.as_manager()

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
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount_euro__gt=0), name="amount_euro_positive"
            ),
            models.CheckConstraint(
                check=models.Q(amount_rub__gt=0), name="amount_rub_positive"
            ),
        ]

    def __str__(self):
        """Строковое представление модели."""
        return f"Заказ №{self.internal_number} ({self.status})"

    def clean(self):
        """Валидация заказа."""
        validator = OrderValidationService()
        validator.validate_amounts(self.amount_euro, self.amount_rub)

        if self.pk:
            old_instance = Order.objects.get(pk=self.pk)
            validator.validate_user_immutability(old_instance.user_id, self.user_id)
            self.amount_euro, self.amount_rub = validator.validate_paid_order_amounts(
                self, old_instance
            )

    def save(self, *args, skip_status_processing: bool = False, **kwargs) -> None:
        """Сохранение заказа."""
        is_new = not self.pk

        if is_new:
            logger.info(
                "Создание нового заказа: %s (пользователь: %s, сайт: %s)",
                self.internal_number,
                self.user.email,
                self.site.name,
            )
        else:
            logger.info(
                "Обновление заказа %s (статус: %s)",
                self.internal_number,
                self.status.name,
            )

        try:
            OrderValidationService.validate_internal_number(
                self.internal_number, self.pk
            )
            self.full_clean()

            if not skip_status_processing:
                OrderStatusService().process_status_change(self)

            result = super().save(*args, **kwargs)
            if is_new:
                logger.info(
                    "Заказ %s успешно создан (ID: %d)",
                    self.internal_number,
                    self.pk,
                )
            return result
        except Exception as e:
            logger.error(
                "Ошибка при сохранении заказа %s: %s",
                self.internal_number,
                str(e),
                exc_info=True,
            )
            raise

    def delete(self, *args, **kwargs):
        """Удаление заказа с проверкой статуса."""
        logger.info(
            "Попытка удаления заказа %s (статус: %s)",
            self.internal_number,
            self.status.name,
        )
        if self.status.code == OrderStatusCode.PAID:
            raise ValidationError("Невозможно удалить оплаченный заказ")
        try:
            result = super().delete(*args, **kwargs)
            logger.info("Заказ %s успешно удален", self.internal_number)
            return result
        except Exception as e:
            logger.error(
                "Ошибка при удалении заказа %s: %s",
                self.internal_number,
                str(e),
                exc_info=True,
            )
            raise
