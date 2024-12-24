"""Модели приложения packages."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.forms import ValidationError
from django.utils import timezone

from .services.delivery_status_service import DeliveryStatusService


class Package(models.Model):
    """Модель посылки."""

    user = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, verbose_name="Пользователь"
    )
    number = models.CharField("Номер посылки в сервисе у посредника", max_length=255)
    shipping_cost_eur = models.DecimalField(
        "Стоимость отправки в евро",
        max_digits=10,
        decimal_places=2,
    )
    fee_cost_eur = models.DecimalField(
        "Комиссия организатора за заказы в посылке",
        max_digits=10,
        decimal_places=2,
    )
    created_at = models.DateField("Дата создания", auto_now_add=True)
    updated_at = models.DateField("Дата обновления", auto_now=True)
    comment = models.TextField("Комментарий", blank=True)
    orders = models.ManyToManyField(
        "order.Order",
        through="PackageOrder",
        verbose_name="Заказы",
        related_name="packages",
    )

    class Meta:
        """Мета класс модели."""

        verbose_name = "Посылка"
        verbose_name_plural = "Посылки"
        unique_together = ("user", "number")

    def __str__(self):
        """Строковое представление модели."""
        return f"Посылка {self.number}"

    @property
    def total_cost_eur(self) -> Decimal:
        """Общая стоимость в евро (доставка + комиссия)."""
        return self.shipping_cost_eur + self.fee_cost_eur

    def clean(self):
        """Валидация полей модели."""
        errors = {}

        # Проверка number (не пустой и без пробелов в начале/конце)
        if self.number:
            self.number = self.number.strip()
            if not self.number:
                errors["number"] = "Номер посылки не может быть пустым"
        else:
            errors["number"] = "Номер посылки обязателен"

        # Проверка финансовых полей (не отрицательные)
        if self.shipping_cost_eur < Decimal("0.00"):
            errors["shipping_cost_eur"] = (
                "Стоимость отправки не может быть отрицательной"
            )

        if self.fee_cost_eur < Decimal("0.00"):
            errors["fee_cost_eur"] = "Комиссия не может быть отрицательной"

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Сохранение с валидацией."""
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs) -> tuple[int, dict[str, int]]:
        """
        Удаление посылки с проверкой статуса доставки.

        Raises:
            ValidationError: Если посылка имеет оплаченную доставку

        Returns:
            tuple[int, dict[str, int]]: Результат удаления (количество удаленных объектов, детали)
        """
        try:
            # Проверяем статус доставки
            delivery = self.packagedelivery
            if delivery.status.code == "paid":
                raise ValidationError(
                    {"package": "Невозможно удалить посылку с оплаченной доставкой"}
                )
        except Package.packagedelivery.RelatedObjectDoesNotExist:
            # Если у посылки нет доставки, можно удалять
            pass

        # Если проверки пройдены, выполняем удаление
        return super().delete(*args, **kwargs)


# Вопрос Идея А нужно ли мне это? Возможно вынести в отдельное дополнение функционала
class PackageOrder(models.Model):
    """Связь с заказами."""

    package = models.ForeignKey(
        Package, on_delete=models.CASCADE, verbose_name="Посылка"
    )
    order = models.ForeignKey(
        "order.Order", on_delete=models.CASCADE, verbose_name="Заказ"
    )
    created_at = models.DateTimeField("Дата добавления", auto_now_add=True)

    class Meta:
        """Мета класс модели."""

        verbose_name = "Связь с заказами"
        verbose_name_plural = "Связи с заказами"
        unique_together = ("package", "order")

    def __str__(self):
        """Строковое представление модели."""
        return f"Связь с заказом {self.order.id}"


class TransportCompany(models.Model):
    """Модель транспортной компании."""

    name = models.CharField("Название", max_length=255)
    description = models.TextField("Описание", blank=True)
    is_active = models.BooleanField("Активна", default=True)
    is_default = models.BooleanField(default=False, verbose_name="ТК по умолчанию")
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)

    class Meta:
        """Мета класс модели."""

        verbose_name = "Транспортная компания"
        verbose_name_plural = "Транспортные компании"
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=["is_default"],
                condition=models.Q(is_default=True),
                name="unique_default_transport_company",
            )
        ]

    def __str__(self):
        """Строковое представление модели."""
        return self.name


class PackageDelivery(models.Model):
    """Модель доставки посылки."""

    # FIXME Добавить выбор по умолчанию транспортной компании
    # Сейчас ошибка при миграции для этого способа
    # def get_default_transport_company():
    #     """Получение транспортной компании по умолчанию."""
    #     return TransportCompany.objects.filter(is_default=True).first()

    package = models.OneToOneField(
        Package, on_delete=models.CASCADE, verbose_name="Посылка"
    )
    transport_company = models.ForeignKey(
        TransportCompany,
        on_delete=models.CASCADE,
        verbose_name="Транспортная компания",
        # default=get_default_transport_company,
    )
    status = models.ForeignKey(
        "status.Status",
        on_delete=models.CASCADE,
        verbose_name="Статус",
        limit_choices_to={"group__code": "delivery_status"},
        related_name="packages_with_status",
        # FIXME Добавить выбор по умолчанию статуса Новая
    )
    tracking_number = models.CharField("Трек номер для отслеживания", max_length=255)
    weight = models.DecimalField(
        "Общий вес в кг",
        max_digits=10,
        decimal_places=2,
        null=False,
    )
    shipping_cost_rub = models.DecimalField(
        "Стоимость отправки в рублях",
        max_digits=10,
        decimal_places=2,
        null=False,
        blank=True,
        default=Decimal("0.00"),
    )
    price_rub_for_kg = models.DecimalField(
        "Стоимость за кг в рублях",
        max_digits=10,
        decimal_places=2,
        null=False,
        blank=True,
        default=Decimal("0.00"),
    )
    created_at = models.DateField(default=timezone.now, verbose_name="Дата создания")
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата оплаты")
    delivery_address = models.TextField("Адрес доставки", blank=True)

    class Meta:
        """Мета класс модели."""

        verbose_name = "Доставка посылки"
        verbose_name_plural = "Доставки посылок"
        # Добавляем ограничение уникальности на уровне базы данных
        constraints = [
            models.UniqueConstraint(fields=["package"], name="unique_package_delivery")
        ]

    def __str__(self):
        """Строковое представление модели."""
        return f"Доставка посылки {self.package.number}"

    def clean(self):
        """Валидация модели."""
        super().clean()

        # Проверка уникальности доставки для посылки
        if not self.pk:  # Только для новых объектов
            existing_delivery = PackageDelivery.objects.filter(
                package=self.package
            ).exists()
            if existing_delivery:
                raise ValidationError(
                    {"package": "Для этой посылки уже существует доставка"}
                )

        # Очищаем трек-номер от пробелов
        if self.tracking_number:
            self.tracking_number = self.tracking_number.strip()

        if not self.tracking_number:
            raise ValidationError(
                {"tracking_number": "Трек номер не может быть пустым"}
            )

        if self.shipping_cost_rub and self.shipping_cost_rub < Decimal("0"):
            raise ValidationError(
                {
                    "shipping_cost_rub": "Стоимость отправки в рублях не может быть отрицательной"
                }
            )

        if self.price_rub_for_kg and self.price_rub_for_kg < Decimal("0"):
            raise ValidationError(
                {"price_rub_for_kg": "Стоимость за кг не может быть отрицательной"}
            )

        if self.weight and self.weight < Decimal("0"):
            raise ValidationError({"weight": "Вес не может быть отрицательным"})

    def save(self, *args, **kwargs):
        """Сохранение с обработкой изменения статуса."""
        skip_status_processing = kwargs.pop("skip_status_processing", False)

        # Создаем сервис для обработки статусов
        status_service = DeliveryStatusService()

        # Обрабатываем изменение статуса
        status_service.process_status_change(self, skip_status_processing)

        # Сохраняем объект
        super().save(*args, **kwargs)
