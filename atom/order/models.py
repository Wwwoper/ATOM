"""Модели приложения orders."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone
from status.services.constants import get_status_codes
from django.db.models.query import QuerySet
from status.constants import OrderStatusCode, StatusGroupCode


from .services.order_status_service import OrderStatusService


class OrderQuerySet(models.QuerySet):
    """QuerySet для модели Order с поддержкой массовых операций."""

    def bulk_update_status(self, new_status, comment=None):
        """
        Массовое обновление статуса и комментария для заказов.

        Args:
            new_status: Новый статус
            comment: Опциональный комментарий

        Raises:
            ValidationError: Если хотя бы один заказ не может быть обновлен
            ValueError: Если не передан статус или передан некорректный статус
        """
        from django.db import transaction
        from status.models import Status

        # Проверяем корректность входных данных
        if not new_status:
            raise ValueError("Не указан новый статус")
        if not isinstance(new_status, Status):
            raise ValueError("Некорректный тип статуса")
        if new_status.group.code != StatusGroupCode.ORDER:
            raise ValueError("Статус не принадлежит группе статусов заказа")

        # Проверяем что есть заказы для обновления
        if not self.exists():
            return 0  # Возвращаем 0, если нет заказов для обновления

        with transaction.atomic():
            # Блокируем заказы для обновления
            orders = list(
                self.select_for_update()
                .select_related("status", "status__group")
                .order_by("id")
            )

            errors = []
            # Проверяем возможность обновления каждого заказа
            for order in orders:
                try:
                    # Проверяем что заказ не оплачен
                    if order.status.code == OrderStatusCode.PAID:
                        raise ValidationError(
                            f"Заказ {order.internal_number} уже оплачен"
                        )

                    # Проверяем допустимость перехода
                    if not order.status.group.is_transition_allowed(
                        order.status.code, new_status.code
                    ):
                        raise ValidationError(
                            f"Недопустимый переход из статуса '{order.status.name}' "
                            f"в '{new_status.name}' для заказа {order.internal_number}"
                        )
                except ValidationError as e:
                    errors.append(str(e))

            # Если есть ошибки, прерываем обновление
            if errors:
                raise ValidationError(
                    "Невозможно обновить статусы:\n" + "\n".join(errors)
                )

            # Если все проверки прошли, обновляем заказы
            update_fields = {"status": new_status}
            if comment is not None:
                update_fields["comment"] = comment

            # Обновляем и возвращаем количество обновленных заказов
            updated_count = self.update(**update_fields)
            return updated_count


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

    # Подключаем OrderQuerySet
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

    def __str__(self):
        """Строковое представление модели."""
        return f"Заказ №{self.internal_number} ({self.status})"

    def clean(self):
        """Валидация полей заказа."""
        super().clean()

        # Базовые проверки
        if not self.status_id:
            raise ValidationError({"status": "Статус заказа обязателен"})

        if self.amount_euro <= 0:
            raise ValidationError({"amount_euro": "Цена в евро должна быть больше 0"})
        if self.amount_rub <= 0:
            raise ValidationError({"amount_rub": "Цена в рублях должна быть больше 0"})

        if self.pk:  # Если заказ уже существует
            old_instance = Order.objects.get(pk=self.pk)

            # Проверка изменения пользователя
            if self.user != old_instance.user:
                raise ValidationError(
                    {"user": "Невозможно изменить пользователя после создания заказа"}
                )

            # Проверка изменения сумм для оплаченного заказа
            if old_instance.status.code == "paid":
                if (
                    self.amount_euro != old_instance.amount_euro
                    or self.amount_rub != old_instance.amount_rub
                ):
                    raise ValidationError(
                        {
                            "amount_euro": "Невозможно изменить сумму после оплаты",
                            "amount_rub": "Невозможно изменить сумму после оплаты",
                        }
                    )

            # Проверка допустимости перехода статуса
            if self.status_id != old_instance.status_id:
                # Проверка допустимости перехода
                allowed_transitions = (
                    old_instance.status.group.allowed_status_transitions.get(
                        old_instance.status.code, []
                    )
                )
                if self.status.code not in allowed_transitions:
                    raise ValidationError(
                        {
                            "status": f"Недопустимый переход из статуса '{old_instance.status.name}' в '{self.status.name}'"
                        }
                    )

                # Проверка повторной оплаты
                if old_instance.status.code == "paid" and self.status.code == "paid":
                    raise ValidationError({"status": "Заказ уже оплачен"})

    def save(self, *args, **kwargs):
        """Сохранение заказа с валидацией."""
        skip_status_processing = kwargs.pop("skip_status_processing", False)

        # Если заказ оплачен, восстанавливаем оригинальные суммы
        if self.pk:
            old_instance = Order.objects.get(pk=self.pk)
            if old_instance.status.code == "paid":
                self.amount_euro = old_instance.amount_euro
                self.amount_rub = old_instance.amount_rub

        if self.pk is None:  # Только для новых объектов
            # Проверяем уникальность internal_number
            if Order.objects.filter(internal_number=self.internal_number).exists():
                print(
                    f"Order with internal_number {self.internal_number} already exists!"
                )
                print(
                    "Existing orders:",
                    list(Order.objects.values_list("internal_number", "id")),
                )
                raise ValidationError(
                    {
                        "internal_number": [
                            "Заказ с таким Внутренний номер заказа уже существует."
                        ]
                    }
                )

        self.full_clean()

        status_service = OrderStatusService()
        status_service.process_status_change(self, skip_status_processing)

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        Удаление заказа с проверкой статуса.

        Raises:
            ValidationError: Если заказ оплачен
        """
        if self.status.code == OrderStatusCode.PAID:
            raise ValidationError("Невозможно удалить оплаченный заказ")
        return super().delete(*args, **kwargs)
