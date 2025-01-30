"""Административный интерфейс для приложения orders.

Этот модуль содержит классы для:
- Управления заказами
- Управления сайтами
- Импорта/экспорта данных
- Массовых операций
"""

import logging
import traceback
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.contrib.admin import helpers
from django.template.response import TemplateResponse
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.shortcuts import redirect
import pandas as pd
from django.db import transaction
from decimal import Decimal
from django.http import HttpResponse, HttpResponseRedirect
from django.db import models

from .models import Order, Site
from status.models import Status
from status.constants import OrderStatusCode

# Настраиваем логгер
logger = logging.getLogger(__name__)


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
                <div><strong>Всего заказов:</strong> <span style="color: #666;">{total}</span></div>
                <div><strong>Оплачено:</strong> <span style="color: #28a745;">{paid}</span></div>
                <div>
                    <strong>Не оплачено:</strong> 
                    <span style="color: #dc3545;">{unpaid}</span>
                    <span style="color: #dc3545;"> (€{unpaid_euro})</span>
                </div>
                <div><strong>Общая прибыль:</strong> <span style="color: #17a2b8;">{profit}</span></div>
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
        return (
            super().get_queryset(request).prefetch_related("orders", "orders__status")
        )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Административный интерфейс для модели Order."""

    list_display = (
        "site",
        "internal_number",
        "external_number",
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
    autocomplete_fields = ["user"]
    change_list_template = "admin/order/order/change_list.html"

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
            {"fields": ("amount_euro", "amount_rub", "expense", "profit")},
        ),
        ("Временные метки", {"fields": ("created_at", "paid_at")}),
        ("Дополнительно", {"fields": ("comment",)}),
    )

    actions = ["mark_as_paid", "export_to_xlsx", "import_from_xlsx"]

    def display_amount_euro(self, obj):
        """Отображение суммы в евро."""
        return format_html("€{}", f"{obj.amount_euro:.2f}")

    display_amount_euro.short_description = "Сумма (EUR)"

    def display_amount_rub(self, obj):
        """Отображение суммы в рублях."""
        return format_html("₽{}", f"{obj.amount_rub:.2f}")

    display_amount_rub.short_description = "Сумма (RUB)"

    def display_expense(self, obj):
        """Отображение расхода в рублях."""
        return format_html("₽{}", f"{obj.expense:.2f}")

    display_expense.short_description = "Расход (RUB)"

    def display_profit(self, obj):
        """Отображение прибыли."""
        return format_html("₽{}", f"{obj.profit:.2f}")

    display_profit.short_description = "Прибыль"

    def get_queryset(self, request):
        """Оптимизация запросов."""
        return super().get_queryset(request).select_related("user", "site", "status")

    def get_actions(self, request):
        """Получение списка доступных действий."""
        actions = super().get_actions(request)

        def import_action(modeladmin, request, queryset=None):
            return self.import_from_xlsx(request)

        import_action.short_description = "Импорт заказов из XLSX"
        import_action.allowed_permissions = ()
        import_action.acts_on_all = True

        actions["import_from_xlsx"] = (
            import_action,
            "import_from_xlsx",
            import_action.short_description,
        )

        return actions

    @admin.action(description="Импорт заказов из XLSX")
    def import_from_xlsx(self, request, queryset=None):
        """Импорт заказов из Excel."""
        logger.info("=" * 50)
        logger.info(f"Метод запроса: {request.method}")
        logger.info(f"POST данные: {request.POST.dict()}")
        logger.info(f"Файлы: {list(request.FILES.keys())}")
        logger.info(f"Content Type: {request.content_type}")
        logger.info(f"Path: {request.path}")

        if request.method == "GET" or not request.POST.get("do_import"):
            return self.get_import_form(request)

        if request.FILES.get("xlsx_file"):
            try:
                file = request.FILES["xlsx_file"]
                logger.info(f"Начинаем обработку файла: {file.name}")

                if not file.name.endswith(".xlsx"):
                    raise ValueError("Пожалуйста, загрузите файл Excel (.xlsx)")

                df = pd.read_excel(file)
                logger.info(
                    f"Прочитано строк: {len(df)}, Колонки: {', '.join(df.columns)}"
                )

                if df.empty:
                    raise ValueError("Файл не содержит данных")

                required_columns = [
                    "Внутренний номер",
                    "Внешний номер",
                    "Сайт",
                    "Пользователь",
                    "Статус",
                    "Сумма (EUR)",
                    "Сумма (RUB)",
                ]
                missing_columns = [
                    col for col in required_columns if col not in df.columns
                ]
                if missing_columns:
                    raise ValueError(
                        f"В файле отсутствуют обязательные колонки: {', '.join(missing_columns)}"
                    )

                success_count = error_count = created_count = updated_count = 0

                for index, row in df.iterrows():
                    try:
                        internal_number = str(row["Внутренний номер"]).strip()
                        external_number = str(row["Внешний номер"]).strip()
                        site_name = str(row["Сайт"]).strip()
                        user_email = str(row["Пользователь"]).strip()
                        status_name = str(row["Статус"]).strip()
                        amount_euro = float(row["Сумма (EUR)"])
                        amount_rub = float(row["Сумма (RUB)"])

                        site = Site.objects.get(name=site_name)
                        user = get_user_model().objects.get(email=user_email)
                        status = Status.objects.get(name=status_name)

                        order, created = Order.objects.update_or_create(
                            internal_number=internal_number,
                            defaults={
                                "external_number": external_number,
                                "site": site,
                                "user": user,
                                "status": status,
                                "amount_euro": amount_euro,
                                "amount_rub": amount_rub,
                                "comment": str(row.get("Комментарий", "")).strip(),
                            },
                        )

                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                        success_count += 1

                    except Exception as e:
                        error_count += 1
                        logger.error(f"Ошибка в строке {index + 2}: {str(e)}")

                if success_count:
                    messages.success(
                        request,
                        f"Успешно обработано заказов: {success_count} "
                        f"(создано: {created_count}, обновлено: {updated_count})",
                    )
                if error_count:
                    messages.warning(request, f"Ошибок при импорте: {error_count}")

                return redirect("admin:order_order_changelist")

            except Exception as e:
                logger.error(f"Ошибка при обработке файла: {e}")
                logger.error(traceback.format_exc())
                messages.error(request, f"Ошибка: {str(e)}")
                return self.get_import_form(request)

        messages.error(request, "Файл не был загружен")
        return self.get_import_form(request)

    def get_import_form(self, request):
        """Возвращает форму импорта."""
        logger.info("Отображение формы импорта")
        logger.info(f"Request path: {request.path}")
        logger.info(f"Changelist URL: {reverse('admin:order_order_changelist')}")

        context = {
            **self.admin_site.each_context(request),
            "title": "Импорт заказов из XLSX",
            "opts": self.model._meta,
            "media": self.media,
            "is_popup": False,
            "save_as": False,
            "has_delete_permission": False,
            "has_add_permission": False,
            "has_change_permission": False,
            "form_url": reverse("admin:order_order_changelist"),
        }
        return TemplateResponse(
            request,
            "admin/order/order/import_xlsx.html",
            context,
        )

    def has_change_order_permission(self, request, obj=None):
        """Проверка разрешения на изменение заказа."""
        return request.user.has_perm("order.change_order")

    @admin.action(
        description="Отметить выбранные заказы как оплаченные",
        permissions=["change_order"],
    )
    def mark_as_paid(self, request, queryset):
        """Массовая оплата заказов."""
        logger.info(
            f"Запущена массовая оплата заказов пользователем {request.user.email}"
        )
        logger.info(f"Количество выбранных заказов: {queryset.count()}")

        if request.POST.get("post"):
            try:
                paid_status = Status.objects.get(
                    code=OrderStatusCode.PAID,
                    group__code="ORDER_STATUS_CONFIG",
                )
            except Status.DoesNotExist:
                logger.error("Статус 'Оплачен' не найден в системе")
                messages.error(request, "Статус 'Оплачен' не найден в системе")
                return
            except Status.MultipleObjectsReturned:
                logger.error("Найдено несколько статусов 'Оплачен'")
                messages.error(
                    request,
                    "Найдено несколько статусов 'Оплачен'. Обратитесь к администратору.",
                )
                return

            ordered_queryset = queryset.order_by("created_at")
            logger.info("Начинаем проверку возможности оплаты заказов")

            total_euro = Decimal("0")
            total_rub = Decimal("0")
            orders_to_process = []

            for order in ordered_queryset:
                if order.status.code == OrderStatusCode.PAID:
                    logger.info(
                        f"Заказ {order.internal_number} уже оплачен, пропускаем"
                    )
                    continue
                total_euro += order.amount_euro
                total_rub += order.amount_rub
                orders_to_process.append(order)

            if orders_to_process:
                first_order = orders_to_process[0]
                balance = first_order.user.balance

                logger.info(
                    "Текущий баланс пользователя %s: %.2f€, %.2f₽",
                    first_order.user.email,
                    balance.balance_euro,
                    balance.balance_rub,
                )
                logger.info(
                    "Требуется для оплаты всех заказов: %.2f€, %.2f₽",
                    total_euro,
                    total_rub,
                )

                if balance.balance_euro < total_euro or balance.balance_rub < total_rub:
                    error_msg = (
                        f"Недостаточно средств для оплаты всех заказов. "
                        f"Требуется: {total_euro}€, {total_rub}₽. "
                        f"Доступно: {balance.balance_euro}€, {balance.balance_rub}₽"
                    )
                    logger.error(error_msg)
                    messages.error(request, error_msg)
                    return

                success_count = 0
                logger.info("Начинаем обработку заказов")

                try:
                    with transaction.atomic():
                        for order in orders_to_process:
                            logger.info(f"Оплата заказа {order.internal_number}")
                            order.status = paid_status
                            order.save()
                            success_count += 1
                            logger.info(
                                f"Заказ {order.internal_number} успешно оплачен"
                            )

                        # Обновляем баланс из БД после всех операций
                        balance.refresh_from_db()
                        logger.info(
                            "Баланс после оплаты заказов: %.2f€, %.2f₽",
                            balance.balance_euro,
                            balance.balance_rub,
                        )

                        success_msg = (
                            f"Успешно оплачено заказов: {success_count} "
                            "(обработка выполнена от старых к новым)"
                        )
                        logger.info(success_msg)
                        messages.success(request, success_msg)

                except Exception as e:
                    error_msg = f"Ошибка при массовой оплате заказов: {str(e)}"
                    logger.error(error_msg)
                    logger.error(traceback.format_exc())
                    messages.error(request, error_msg)

            return

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

        return TemplateResponse(
            request,
            "admin/order/order/mark_as_paid_confirmation.html",
            context,
        )

    @admin.action(description="Экспорт выбранных заказов в Excel")
    def export_to_xlsx(self, request, queryset):
        """Экспорт выбранных заказов в Excel."""
        logger.info(f"Starting export for {queryset.count()} orders")
        try:
            # Создаем DataFrame из queryset
            data = []
            for order in queryset:
                logger.debug(f"Processing order {order.id}")
                data.append(
                    {
                        "ID": order.id,
                        "Внутренний номер": order.internal_number,
                        "Внешний номер": order.external_number,
                        "Сайт": str(order.site),
                        "Пользователь": str(order.user),
                        "Статус": str(order.status),
                        "Сумма (EUR)": order.amount_euro,
                        "Сумма (RUB)": order.amount_rub,
                        "Расходы (RUB)": order.expense,
                        "Прибыль (RUB)": order.profit,
                        "Комментарий": order.comment,
                        "Создан": order.created_at,
                        "Дата оплаты": order.paid_at,
                    }
                )

            logger.info("Creating DataFrame")
            df = pd.DataFrame(data)

            logger.info("Creating response")
            response = HttpResponse(
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            response["Content-Disposition"] = 'attachment; filename="orders.xlsx"'

            logger.info("Saving to Excel")
            df.to_excel(response, index=False, engine="openpyxl")

            logger.info("Export completed successfully")
            return response

        except Exception as e:
            logger.error(f"Error in export_to_xlsx: {str(e)}", exc_info=True)
            self.message_user(
                request,
                f"Произошла ошибка при экспорте: {str(e)}",
                level=messages.ERROR,
            )
            return HttpResponseRedirect(request.get_full_path())

    export_to_xlsx.short_description = "Экспортировать выбранные заказы в Excel"

    def save_model(self, request, obj, form, change):
        """Логирование сохранения модели."""
        action = "обновлен" if change else "создан"
        logger.info(
            f"Заказ {obj.internal_number} {action} пользователем {request.user.email}"
        )
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        """Логирование удаления модели."""
        logger.info(
            f"Заказ {obj.internal_number} удален пользователем {request.user.email}"
        )
        super().delete_model(request, obj)

    def changelist_view(self, request, extra_context=None):
        """Добавляем сумму в евро для отображения над списком заказов."""
        response = super().changelist_view(request, extra_context=extra_context)

        try:
            qs = response.context_data["cl"].queryset
        except (AttributeError, KeyError):
            return response

        # Получаем сумму в евро только для новых заказов
        total_euro = (
            qs.filter(status__code=OrderStatusCode.NEW).aggregate(
                total=models.Sum("amount_euro")
            )["total"]
            or 0
        )

        response.context_data["total_euro"] = total_euro

        return response
