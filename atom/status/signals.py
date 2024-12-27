"""
Сигналы для создания статусов и групп статусов по умолчанию.

Этот модуль отвечает за автоматическое создание необходимых статусов и групп статусов
при миграции базы данных. Реализует инициализацию начальных данных для системы статусов.

Основные компоненты:
    - initialize_status_group: Функция инициализации группы статусов
    - create_default_status: Обработчик сигнала post_migrate
    - Конфигурация статусов для заказов и доставок

Процесс инициализации:
    1. Получение модели и типа контента
    2. Создание группы статусов с настройками
    3. Создание статусов внутри группы
    4. Настройка правил переходов между статусами

Группы статусов:
    - ORDER_STATUS_CONFIG: Статусы для заказов
    - DELIVERY_STATUS_CONFIG: Статусы для доставок

Примеры конфигурации:
        "DELIVERY_STATUS_CONFIG": {
            "model": "package.Delivery",
            "name": "Статусы доставки",
            "status": [
                {"code": "new", "name": "Новая", "is_default": True},
                {"code": "paid", "name": "Оплачена"},
                ...
            ]
        }
    }

Примечания:
    - Выполняется только при миграции приложения status
    - Не перезаписывает существующие статусы
    - Поддерживает настройку переходов между статусами
    - Позволяет задавать статусы по умолчанию
"""

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from .services.initial_data import (
    ORDER_STATUS_CONFIG,
    DELIVERY_STATUS_CONFIG,
)


def initialize_status_group(group_code, group_data, StatusGroup, Status):
    """
    Вспомогательная функция для инициализации группы статусов.

    Args:
        group_code: Код группы статусов
        group_data: Данные для создания группы и статусов
        StatusGroup: Модель группы статусов
        Status: Модель статуса

    Создает группу статусов и все статусы внутри этой группы
    согласно предоставленной конфигурации.
    """
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
    """
    Создание статусов по умолчанию при миграции.

    Args:
        sender: Приложение, отправившее сигнал
        **kwargs: Дополнительные аргументы

    Создает все настроенные статусы и группы статусов
    при выполнении миграций приложения status.
    """
    if sender.name == "status":
        StatusGroup = apps.get_model("status", "StatusGroup")
        Status = apps.get_model("status", "Status")

        # Объединяем все конфигурации статусов
        all_status = {
            **ORDER_STATUS_CONFIG,
            **DELIVERY_STATUS_CONFIG,
        }

        # Единый цикл для всех групп статусов
        for group_code, group_data in all_status.items():
            initialize_status_group(group_code, group_data, StatusGroup, Status)
