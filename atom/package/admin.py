"""Административный интерфейс для модели Package."""

from django.contrib import admin
from django.utils.html import format_html
from django.db import models, transaction

from .models import Package, PackageDelivery, PackageOrder, TransportCompany


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    """Административный интерфейс для модели Package."""

    autocomplete_fields = ["user"]
    list_display = (
        "number",
        "user",
        "display_shipping_cost_eur",
        "display_fee_cost_eur",
        "display_total_cost_eur",
        "display_orders_count",
        "created_at",
    )
    list_filter = ("created_at", "user")
    search_fields = ("number", "user__username", "user__email", "comment")
    raw_id_fields = ("user",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    def display_shipping_cost_eur(self, obj):
        """Отображение стоимости доставки."""
        return format_html("€{}", f"{obj.shipping_cost_eur:.2f}")

    display_shipping_cost_eur.short_description = "Стоимость доставки"

    def display_fee_cost_eur(self, obj):
        """Отображение комиссии."""
        return format_html("€{}", f"{obj.fee_cost_eur:.2f}")

    display_fee_cost_eur.short_description = "Комиссия"

    def display_total_cost_eur(self, obj):
        """Отображение общей стоимости."""
        return format_html("€{}", f"{obj.total_cost_eur:.2f}")

    display_total_cost_eur.short_description = "Общая стоимость"

    def display_orders_count(self, obj):
        """Отображение количества заказов."""
        return obj.orders.count()

    display_orders_count.short_description = "Кол-во заказов"


@admin.register(PackageDelivery)
class PackageDeliveryAdmin(admin.ModelAdmin):
    """Административный интерфейс для модели PackageDelivery."""

    list_display = (
        "package",
        "transport_company",
        "status",
        "tracking_number",
        "weight",
        "display_shipping_cost_rub",
        "display_price_rub_for_kg",
        "paid_at",
    )
    list_filter = ("status", "transport_company", "created_at", "paid_at")
    search_fields = (
        "tracking_number",
        "package__number",
        "package__user__username",
        "delivery_address",
    )
    readonly_fields = (
        "paid_at",
        "shipping_cost_rub",
        "price_rub_for_kg",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    def display_shipping_cost_rub(self, obj):
        """Отображение стоимости доставки в рублях."""
        return format_html("₽{}", "{:.2f}".format(obj.shipping_cost_rub))

    display_shipping_cost_rub.short_description = "Стоимость доставки"

    def display_price_rub_for_kg(self, obj):
        """Отображение стоимости за кг."""
        return format_html("₽{}", "{:.2f}".format(obj.price_rub_for_kg))

    display_price_rub_for_kg.short_description = "Цена за кг"

    fieldsets = (
        (
            "Основная информация",
            {
                "fields": (
                    "package",
                    "transport_company",
                    "status",
                    "tracking_number",
                    "weight",
                )
            },
        ),
        (
            "Стоимость",
            {
                "fields": (
                    "shipping_cost_rub",
                    "price_rub_for_kg",
                )
            },
        ),
        (
            "Дополнительная информация",
            {
                "fields": (
                    "delivery_address",
                    "paid_at",
                )
            },
        ),
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Переопределяем выбор посылок."""
        if db_field.name == "package":
            if object_id := request.resolver_match.kwargs.get("object_id"):
                # Редактирование существующей доставки
                try:
                    current_delivery = self.get_object(request, object_id)
                    kwargs["queryset"] = Package.objects.filter(
                        models.Q(id=current_delivery.package_id)
                        | models.Q(packagedelivery__isnull=True)
                    ).distinct()
                except (PackageDelivery.DoesNotExist, AttributeError):
                    kwargs["queryset"] = Package.objects.filter(
                        packagedelivery__isnull=True
                    )
            else:
                # Создание новой доставки
                kwargs["queryset"] = Package.objects.filter(
                    packagedelivery__isnull=True
                )

            # Для отладки
            print(
                f"Available packages: {list(kwargs['queryset'].values_list('id', 'number'))}"
            )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(TransportCompany)
class TransportCompanyAdmin(admin.ModelAdmin):
    """Админка для транспортной компании."""

    list_display = ("name", "is_active", "is_default", "created_at", "updated_at")
    list_filter = ("is_active", "is_default")
    search_fields = ("name",)

    def save_model(self, request, obj, form, change):
        """
        Переопределяем сохранение модели в админке.
        Используем транзакцию для атомарного обновления флага is_default.
        """
        with transaction.atomic():
            if obj.is_default:  # Если компания помечена как default
                # Снимаем флаг у всех компаний
                TransportCompany.objects.filter(is_default=True).update(
                    is_default=False
                )

            # Сохраняем новую/измененную компанию
            super().save_model(request, obj, form, change)


@admin.register(PackageOrder)
class PackageOrderAdmin(admin.ModelAdmin):
    """Административный интерфейс для модели PackageOrder."""

    list_display = ("package", "order", "created_at")
    list_filter = ("created_at",)
    search_fields = (
        "package__number",
        "order__internal_number",
        "order__external_number",
    )
    raw_id_fields = ("package", "order")
    date_hierarchy = "created_at"
