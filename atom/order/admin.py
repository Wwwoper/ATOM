"""Административный интерфейс для приложения orders."""

from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.utils import timezone
from django.contrib.admin import helpers
from django.template.response import TemplateResponse

from .models import Order, Site
from status.models import Status
from status.constants import OrderStatusCode


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    """Административный интерфейс для модели Site."""

    list_display = (
        "name",
        "get_orders_statistics",
        "url",
        "display_organizer_fee",
        "display_total_orders",
        "display_total_profit",
        "created_at",
        "updated_at",
    )
    list_filter = ("created_at", "updated_at")
    search_fields = ("name", "url")
    readonly_fields = ("created_at", "updated_at", "get_orders_statistics")
    fieldsets = (
        (
            "Основная информация",
            {
                "fields": (
                    "name",
                    "get_orders_statistics",
                    "url",
                    "organizer_fee_percentage",
                    "description",
                )
            },
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
        return format_html("₽{}", f"{float(total_profit):.2f}")

    display_total_profit.short_description = "Общая прибыль"

    @admin.display(description=_("Статистика заказов"))
    def get_orders_statistics(self, obj):
        """Отображение статистики заказов в админке."""
        stats = obj.orders_statistics
        return format_html(
            """
            <div style="line-height: 1.5;">
                <div>
                    <strong>Всего заказов:</strong> 
                    <span style="color: #666;">{total}</span>
                </div>
                <div>
                    <strong>Оплачено:</strong> 
                    <span style="color: #28a745;">{paid}</span>
                </div>
                <div>
                    <strong>Не оплачено:</strong> 
                    <span style="color: #dc3545;">{unpaid}</span>
                    <span style="color: #dc3545;"> (€{unpaid_euro})</span>
                </div>
                <div>
                    <strong>Общая прибыль:</strong> 
                    <span style="color: #17a2b8;">{profit}</span>
                </div>
            </div>
            """,
            total=stats["total_orders"],
            paid=stats["paid_orders"],
            unpaid=stats["unpaid_orders"],
            profit="{:.2f} ₽".format(stats["total_profit"]),
            unpaid_euro="{:.2f}".format(stats["unpaid_euro_sum"]),
        )

    def delete_queryset(self, request, queryset):
        """Запрет на массовое удаление сайтов."""
        raise PermissionDenied("Массовое удаление сайтов запрещено")

    def get_queryset(self, request):
        """Оптимизация запросов для списка."""
        qs = super().get_queryset(request)
        return qs.prefetch_related("orders", "orders__status")

    class Media:
        """Дополнительные медиа-файлы для админки."""

        css = {"all": ("admin/css/site_admin.css",)}


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
        "display_expense",
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

    actions = ["mark_as_paid"]

    def display_amount_euro(self, obj):
        """Отображение суммы в евро."""
        return format_html("€{}", f"{obj.amount_euro:,.2f}")

    display_amount_euro.short_description = "Сумма (EUR)"

    def display_amount_rub(self, obj):
        """Отображение суммы в рублях."""
        return format_html("₽{}", f"{obj.amount_rub:,.2f}")

    display_amount_rub.short_description = "Сумма (RUB)"

    def display_expense(self, obj):
        """Отображение расхода в рублях."""
        return format_html("₽{}", f"{obj.expense:,.2f}")

    display_expense.short_description = "Расход (RUB)"

    def display_profit(self, obj):
        """Отображение прибыли."""
        return format_html("₽{}", f"{obj.profit:,.2f}")

    display_profit.short_description = "Прибыль"

    def get_queryset(self, request):
        """Оптимизация запросов."""
        return super().get_queryset(request).select_related("user", "site", "status")

    def has_change_order_permission(self, request):
        """Проверка прав на изменение заказа."""
        return request.user.has_perm("order.change_order")

    @admin.action(
        description="Отметить выбранные заказы как оплаченные",
        permissions=["change_order"],
    )
    def mark_as_paid(self, request, queryset):
        """Массовая оплата заказов."""
        if request.POST.get("post"):  # Пользователь подтвердил действие
            # Получаем статус "Оплачен"
            try:
                paid_status = Status.objects.get(
                    code=OrderStatusCode.PAID,
                    group__code="ORDER_STATUS_CONFIG",  # Добавляем фильтр по группе
                )
            except Status.DoesNotExist:
                messages.error(request, "Статус 'Оплачен' не найден в системе")
                return
            except Status.MultipleObjectsReturned:
                messages.error(
                    request,
                    "Найдено несколько статусов 'Оплачен'. Обратитесь к администратору.",
                )
                return

            # Считаем количество успешно обработанных заказов
            success_count = 0
            error_count = 0

            for order in queryset:
                try:
                    # Пропускаем уже оплаченные заказы
                    if order.status.code == OrderStatusCode.PAID:
                        continue

                    # Меняем статус и сохраняем
                    order.status = paid_status
                    order.save()
                    success_count += 1

                except Exception as e:
                    error_count += 1
                    messages.error(
                        request,
                        f"Ошибка при обработке заказа {order.internal_number}: {str(e)}",
                    )

            # Выводим сообщение о результатах
            if success_count:
                messages.success(
                    request, f"Успешно обработано заказов: {success_count}"
                )
            if error_count:
                messages.warning(
                    request, f"Не удалось обработать заказов: {error_count}"
                )
            return

        # Подготавливаем контекст для страницы подтверждения
        context = {
            **self.admin_site.each_context(request),
            "title": "Подтвердите оплату заказов",
            "queryset": queryset,
            "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
            "opts": self.model._meta,
            "media": self.media,
            "action": "mark_as_paid",
            "orders_count": queryset.count(),
        }

        # Показываем страницу подтверждения
        return TemplateResponse(
            request,
            "admin/order/order/mark_as_paid_confirmation.html",
            context,
        )
