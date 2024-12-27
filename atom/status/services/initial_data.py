"""
Структура конфигурации статусов.

Этот модуль содержит конфигурацию начальных данных для статусов различных сущностей
(заказы, доставки). Определяет структуру статусов, правила переходов и типы транзакций.

Формат конфигурации:
{
    "group_code": {                    # Код группы статусов (например "order_status")
        "name": str,                   # Название группы статусов
        "model": str,                  # Путь к модели в формате "app.Model"
        "allowed_status_transitions": {# Словарь разрешенных переходов
            "status_code": [           # Код начального статуса
                "allowed_status",      # Список разрешенных статусов для перехода
                ...
            ],
            ...
        },
        "transaction_type_by_status": {  # Словарь типов транзакций
            "status_code": str,         # Код статуса: тип транзакции
            ...
        },
        "status": [                 # Список статусов
            {
                "code": str,          # Код статуса
                "name": str,          # Название статуса
                "description": str,    # Описание статуса
                "is_default": bool,    # Флаг статуса по умолчанию
                "order": int,         # Порядок сортировки
            },
            ...
        ]
    }
}

Примеры конфигурации:
    ORDER_STATUS = {
        "order_status": {
            "name": "Статусы заказа",
            "model": "order.Order",
            "allowed_status_transitions": {
                "new": ["paid"],
                "paid": ["refunded"]
            },
            "status": [
                {
                    "code": "new",
                    "name": "Новый",
                    "is_default": True,
                    "order": 10
                },
                ...
            ]
        }
    }

Примечания:
    - Каждая группа статусов должна иметь уникальный код
    - Все статусы должны иметь уникальные коды внутри группы
    - Обязательно должен быть указан статус по умолчанию
    - Порядок статусов влияет на их отображение в интерфейсе
    - Правила переходов определяют возможные изменения статусов
    - Типы транзакций связывают статусы с финансовыми операциями
"""

from balance.services.constants import TransactionTypeChoices

ORDER_status = {
    "order_status": {
        "name": "Статусы заказа",
        "model": "order.Order",
        "allowed_status_transitions": {
            "new": ["paid"],
            "paid": ["refunded"],
            "refunded": ["new"],
        },
        "transaction_type_by_status": {
            "paid": TransactionTypeChoices.EXPENSE.value,
            "refunded": TransactionTypeChoices.PAYBACK.value,
        },
        "status": [
            {
                "code": "new",
                "name": "Новый",
                "description": "Новый заказ",
                "is_default": True,
                "order": 10,
            },
            {
                "code": "paid",
                "name": "Оплачен",
                "description": "Заказ оплачен",
                "order": 20,
            },
            {
                "code": "refunded",
                "name": "Возврат",
                "description": "Возврат средств по заказу",
                "order": 30,
            },
        ],
    }
}

DELIVERY_STATUS_CONFIG = {
    "delivery_status": {
        "name": "Статусы доставки",
        "model": "package.PackageDelivery",
        "allowed_status_transitions": {
            "new": ["paid"],
            "paid": ["cancelled"],
            "cancelled": ["new"],
        },
        "transaction_type_by_status": {
            "paid": TransactionTypeChoices.EXPENSE.value,
            "cancelled": TransactionTypeChoices.PAYBACK.value,
            # TODO: добавить тип транзакции для реэкспорта и отмены доставки
        },
        "status": [
            {
                "code": "new",
                "name": "Новая",
                "description": "Новая доставка",
                "is_default": True,
                "order": 10,
            },
            {
                "code": "paid",
                "name": "Оплачена",
                "description": "Доставка оплачена",
                "order": 20,
            },
            {
                "code": "reexport",
                "name": "Реэкспорт",
                "description": "Доставка отправлена на реэкспорт",
                "order": 40,
            },
            {
                "code": "cancelled",
                "name": "Отменена",
                "description": "Доставка отменена",
                "order": 90,
            },
        ],
    }
}
