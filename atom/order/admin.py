from django.contrib import admin
from django.db.models import Count, Sum
from django.utils.html import format_html

from .models import Order, Site


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    """Административный интерфейс для модели Site."""

    list_display = (
        "name",
        "url",
        "display_organizer_fee",
        "display_total_orders",
        "display_total_profit",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = ("name", "url")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "Основная информация",
            {"fields": ("name", "url", "organizer_fee_percentage", "description")},
        ),
        ("Служебная информация", {"fields": ("created_at", "updated_at")}),
    )

    def display_organizer_fee(self, obj):
        """Отображение комиссии организатора."""
        return format_html("{}&nbsp;%", obj.organizer_fee_percentage)

    display_organizer_fee.short_description = "Комиссия"

    def display_total_orders(self, obj):
        """Отображение количества заказов."""
        return getattr(obj, "total_orders", 0)

    display_total_orders.short_description = "Кол-во заказов"

    def display_total_profit(self, obj):
        """Отображение общей прибыли."""
        total_profit = getattr(obj, "total_profit", 0)
        return format_html("₽{}", "{:.2f}".format(float(total_profit)))

    display_total_profit.short_description = "Общая прибыль"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Административный интерфейс для модели Order."""

    autocomplete_fields = ["user"]
    list_display = (
        "internal_number",
        "external_number",
        "site",
        "user",
        "status",
        "display_amount_euro",
        "display_amount_rub",
        "display_profit",
        "created_at",
        "paid_at",
    )
    list_filter = ("status", "site", "created_at", "paid_at")
    search_fields = (
        "internal_number",
        "external_number",
        "user__username",
        "user__email",
        "comment",
    )
    readonly_fields = ("profit", "expense", "paid_at")
    date_hierarchy = "created_at"
    raw_id_fields = ("user",)

    fieldsets = (
        (
            "Основная информация",
            {
                "fields": (
                    "user",
                    "site",
                    "status",
                    "internal_number",
                    "external_number",
                )
            },
        ),
        (
            "Финансовая информация",
            {
                "fields": (
                    "amount_euro",
                    "amount_rub",
                    "expense",
                    "profit",
                )
            },
        ),
        (
            "Временные метки",
            {
                "fields": (
                    "created_at",
                    "paid_at",
                )
            },
        ),
        ("Дополнительно", {"fields": ("comment",)}),
    )

    def display_amount_euro(self, obj):
        """Отображение суммы в евро."""
        return format_html("€{}", "{:,.2f}".format(obj.amount_euro))

    display_amount_euro.short_description = "Сумма (EUR)"

    def display_amount_rub(self, obj):
        """Отображение суммы в рублях."""
        return format_html("₽{}", "{:,.2f}".format(obj.amount_rub))

    display_amount_rub.short_description = "Сумма (RUB)"

    def display_profit(self, obj):
        """Отображение прибыли."""
        return format_html("₽{}", "{:,.2f}".format(obj.profit))

    display_profit.short_description = "Прибыль"

    def get_queryset(self, request):
        """Оптимизация запросов."""
        return super().get_queryset(request).select_related("user", "site", "status")
