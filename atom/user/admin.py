"""Модуль для админки пользователей."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from balance.models import Balance
from .models import User
from .services import UserService


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Административный интерфейс для модели User."""

    list_display = (
        "username",
        "email",
        "company_name",
        "phone",
        "is_active",
        "display_balance",
        "created_at",
    )
    list_filter = ("is_active", "is_staff", "groups", "created_at")
    search_fields = (
        "username",
        "email",
        "company_name",
        "phone",
        "address",
    )
    ordering = ("-created_at",)

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            "Персональная информация",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                    "company_name",
                    "phone",
                    "address",
                )
            },
        ),
        (
            "Права доступа",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            "Важные даты",
            {"fields": ("last_login", "date_joined", "created_at")},
        ),
    )
    readonly_fields = ("last_login", "date_joined", "created_at")
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "password1",
                    "password2",
                    "company_name",
                    "phone",
                    "address",
                ),
            },
        ),
    )

    def display_balance(self, obj):
        """Отображение баланса пользователя."""
        try:
            balance = Balance.objects.get(user=obj)
            return format_html(
                "€{} / ₽{}",
                "{:.2f}".format(balance.balance_euro),
                "{:.2f}".format(balance.balance_rub),
            )
        except Balance.DoesNotExist:
            return "-"

    display_balance.short_description = "Баланс (EUR/RUB)"

    def get_queryset(self, request):
        """Оптимизация запросов."""
        return super().get_queryset(request).select_related()

    def save_model(self, request, obj, form, change):
        """Сохранение модели пользователя."""
        if not change:  # Если это создание нового пользователя
            # Используем сервис для создания пользователя
            user = UserService.create_user(
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password1"],
                **{
                    k: v
                    for k, v in form.cleaned_data.items()
                    if k not in ["password1", "password2", "username"]
                }
            )
            obj = user  # Обновляем obj новым пользователем
        else:
            # Для существующего пользователя используем стандартное сохранение
            super().save_model(request, obj, form, change)
