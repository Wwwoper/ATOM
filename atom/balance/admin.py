from django.contrib import admin
from django.utils.html import format_html

from .models import Balance, BalanceHistoryRecord, Transaction


@admin.register(Balance)
class BalanceAdmin(admin.ModelAdmin):
    """Административный интерфейс для модели Balance."""

    list_display = (
        "user",
        "display_balance_euro",
        "display_balance_rub",
        "display_average_exchange_rate",
    )
    list_select_related = ("user",)
    search_fields = ("user__username", "user__email")
    readonly_fields = ("balance_euro", "balance_rub", "average_exchange_rate")

    def display_balance_euro(self, obj):
        """Отображение баланса в евро."""
        return format_html("€{}", "{:.2f}".format(obj.balance_euro))

    display_balance_euro.short_description = "Баланс в евро"

    def display_balance_rub(self, obj):
        """Отображение баланса в рублях."""
        return format_html("₽{}", "{:.2f}".format(obj.balance_rub))

    display_balance_rub.short_description = "Баланс в рублях"

    def display_average_exchange_rate(self, obj):
        """Отображение среднего курса обмена."""
        return format_html("{} ₽/€", "{:.2f}".format(obj.average_exchange_rate))

    display_average_exchange_rate.short_description = "Средний курс"

    def has_delete_permission(self, request, obj=None):
        """Запрет на удаление баланса."""
        return False


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Административный интерфейс для модели Transaction."""

    list_display = (
        "transaction_date",
        "balance",
        "transaction_type",
        "display_amount_euro",
        "display_amount_rub",
    )
    list_filter = ("transaction_type", "transaction_date")
    search_fields = (
        "balance__user__username",
        "balance__user__email",
        "comment",
    )
    date_hierarchy = "transaction_date"
    ordering = ("-transaction_date",)

    def display_amount_euro(self, obj):
        """Отображение суммы в евро."""
        return format_html("€{}", "{:.2f}".format(obj.amount_euro))

    display_amount_euro.short_description = "Сумма в евро"

    def display_amount_rub(self, obj):
        """Отображение суммы в рублях."""
        return format_html("₽{}", "{:.2f}".format(obj.amount_rub))

    display_amount_rub.short_description = "Сумма в рублях"


@admin.register(BalanceHistoryRecord)
class BalanceHistoryRecordAdmin(admin.ModelAdmin):
    """Административный интерфейс для модели BalanceHistoryRecord."""

    list_display = (
        "transaction_date",
        "balance",
        "transaction_type",
        "display_amounts",
        "display_amounts_after",
    )
    list_filter = ("transaction_type", "transaction_date")
    search_fields = (
        "balance__user__username",
        "balance__user__email",
        "comment",
    )
    date_hierarchy = "transaction_date"
    ordering = ("-transaction_date",)
    readonly_fields = (
        "balance",
        "transaction_type",
        "amount_euro",
        "amount_rub",
        "amount_euro_after",
        "amount_rub_after",
        "transaction_date",
    )

    def display_amounts(self, obj):
        """Отображение сумм транзакции."""
        return format_html(
            "€{} / ₽{}",
            "{:.2f}".format(obj.amount_euro),
            "{:.2f}".format(obj.amount_rub),
        )

    display_amounts.short_description = "Суммы (EUR/RUB)"

    def display_amounts_after(self, obj):
        """Отображение сумм после транзакции."""
        return format_html(
            "€{} / ₽{}",
            "{:.2f}".format(obj.amount_euro_after),
            "{:.2f}".format(obj.amount_rub_after),
        )

    display_amounts_after.short_description = "Баланс после (EUR/RUB)"

    def has_add_permission(self, request):
        """Запрет на добавление записей истории вручную."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Запрет на удаление записей истории."""
        return False
