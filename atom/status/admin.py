from django.contrib import admin
from django.utils.html import format_html

from .models import Status, StatusGroup


@admin.register(StatusGroup)
class StatusGroupAdmin(admin.ModelAdmin):
    """Административный интерфейс для модели StatusGroup."""

    list_display = (
        "name",
        "code",
        "content_type",
        "display_status_count",
        "display_transitions",
    )
    list_filter = ("content_type",)
    search_fields = ("name", "code")
    readonly_fields = ("content_type",)

    def display_status_count(self, obj):
        """Отображение количества статусов в группе."""
        return obj.status.count()

    display_status_count.short_description = "Кол-во статусов"

    def display_transitions(self, obj):
        """Отображение разрешенных переходов."""
        transitions = []
        for from_status, to_statuses in obj.allowed_status_transitions.items():
            transitions.append(
                format_html(
                    "{} → {}",
                    from_status,
                    ", ".join(to_statuses),
                )
            )
        return format_html("<br>".join(transitions)) if transitions else "-"

    display_transitions.short_description = "Разрешенные переходы"

    def has_delete_permission(self, request, obj=None):
        """Запрет на удаление групп статусов."""
        return False


@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    """Административный интерфейс для модели Status."""

    list_display = (
        "name",
        "code",
        "group",
        "is_default",
        "order",
        "display_transaction_type",
    )
    list_filter = ("group", "is_default")
    search_fields = ("name", "code", "description")
    ordering = ("group", "order")
    readonly_fields = ("group",)
    fieldsets = (
        (
            "Основная информация",
            {
                "fields": (
                    "group",
                    "name",
                    "code",
                    "description",
                )
            },
        ),
        (
            "Настройки",
            {
                "fields": (
                    "is_default",
                    "order",
                )
            },
        ),
    )

    def display_transaction_type(self, obj):
        """Отображение типа транзакции для статуса."""
        transaction_type = obj.group.transaction_type_by_status.get(obj.code)
        return transaction_type if transaction_type else "-"

    display_transaction_type.short_description = "Тип транзакции"

    def has_delete_permission(self, request, obj=None):
        """Запрет на удаление статусов."""
        return False

    def get_readonly_fields(self, request, obj=None):
        """Делаем поля только для чтения если объект уже создан."""
        if obj:  # если объект уже существует
            return self.readonly_fields + ("code",)
        return self.readonly_fields
