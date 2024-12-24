"""Сигналы для создания статусов и групп статусов по умолчанию при миграции."""

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from .services.initial_data import DELIVERY_STATUS_CONFIG, ORDER_status


def initialize_status_group(group_code, group_data, StatusGroup, Status):
    """Вспомогательная функция для инициализации группы статусов."""
    app_label, model_name = group_data["model"].split(".")
    model = apps.get_model(app_label, model_name)
    content_type = ContentType.objects.get_for_model(model)

    status_group, _ = StatusGroup.objects.get_or_create(
        code=group_code,
        defaults={
            "name": group_data["name"],
            "content_type": content_type,
            "allowed_status_transitions": group_data.get(
                "allowed_status_transitions", {}
            ),
            "transaction_type_by_status": group_data.get(
                "transaction_type_by_status", {}
            ),
        },
    )

    for status_data in group_data["status"]:
        Status.objects.get_or_create(
            group=status_group,
            code=status_data["code"],
            defaults={
                "name": status_data["name"],
                "description": status_data.get("description", ""),
                "is_default": status_data.get("is_default", False),
                "order": status_data.get("order", 0),
            },
        )


@receiver(post_migrate)
def create_default_status(sender, **kwargs):
    """Создание статусов по умолчанию."""
    if sender.name == "status":
        StatusGroup = apps.get_model("status", "StatusGroup")
        Status = apps.get_model("status", "Status")

        # Объединяем все конфигурации статусов
        all_status = {**ORDER_status, **DELIVERY_STATUS_CONFIG}

        # Единый цикл для всех групп статусов
        for group_code, group_data in all_status.items():
            initialize_status_group(group_code, group_data, StatusGroup, Status)
