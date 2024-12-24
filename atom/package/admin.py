from django.contrib import admin
from django.db.models import Count, Sum
from django.utils.html import format_html

from .models import Package, PackageDelivery, PackageOrder, TransportCompany


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    """Административный интерфейс для модели Package."""

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

    def display_shipping_cost_eur(self, obj):
        """Отображение стоимости доставки."""
        return format_html("€{:.2f}", obj.shipping_cost_eur)

    display_shipping_cost_eur.short_description = "Стоимость доставки"

    def display_fee_cost_eur(self, obj):
        """Отображение комиссии."""
        return format_html("€{:.2f}", obj.fee_cost_eur)

    display_fee_cost_eur.short_description = "Комиссия"

    def display_total_cost_eur(self, obj):
        """Отображение общей стоимости."""
        return format_html("€{:.2f}", obj.total_cost_eur)

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
    raw_id_fields = ("package",)
    readonly_fields = ("paid_at",)
    date_hierarchy = "created_at"

    def display_shipping_cost_rub(self, obj):
        """Отображение стоимости доставки в рублях."""
        return format_html("₽{:.2f}", obj.shipping_cost_rub)

    display_shipping_cost_rub.short_description = "Стоимость доставки"

    def display_price_rub_for_kg(self, obj):
        """Отображение стоимости за кг."""
        return format_html("₽{:.2f}", obj.price_rub_for_kg)

    display_price_rub_for_kg.short_description = "Цена за кг"


@admin.register(TransportCompany)
class TransportCompanyAdmin(admin.ModelAdmin):
    """Административный интерфейс для модели TransportCompany."""

    list_display = (
        "name",
        "is_active",
        "is_default",
        "display_deliveries_count",
        "created_at",
    )
    list_filter = ("is_active", "is_default", "created_at")
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")

    def display_deliveries_count(self, obj):
        """Отображение количества доставок."""
        return obj.packagedelivery_set.count()

    display_deliveries_count.short_description = "Кол-во доставок"


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
