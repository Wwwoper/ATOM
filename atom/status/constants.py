"""Константы для работы со статусами."""

from enum import Enum
from .services.initial_data import ORDER_STATUS_CONFIG, DELIVERY_STATUS_CONFIG


class OrderStatusCode(str, Enum):
    """Коды статусов заказов."""

    # Получаем коды из конфигурации
    NEW = next(
        s["code"]
        for s in ORDER_STATUS_CONFIG["ORDER_STATUS_CONFIG"]["status"]
        if s.get("is_default")
    )
    PAID = next(
        s["code"]
        for s in ORDER_STATUS_CONFIG["ORDER_STATUS_CONFIG"]["status"]
        if s["code"] == "paid"
    )
    REFUNDED = next(
        s["code"]
        for s in ORDER_STATUS_CONFIG["ORDER_STATUS_CONFIG"]["status"]
        if s["code"] == "refunded"
    )


class DeliveryStatusCode(str, Enum):
    """Коды статусов доставки."""

    # Получаем коды из конфигурации
    NEW = next(
        s["code"]
        for s in DELIVERY_STATUS_CONFIG["DELIVERY_STATUS_CONFIG"]["status"]
        if s.get("is_default")
    )
    PAID = next(
        s["code"]
        for s in DELIVERY_STATUS_CONFIG["DELIVERY_STATUS_CONFIG"]["status"]
        if s["code"] == "paid"
    )
    REEXPORT = next(
        s["code"]
        for s in DELIVERY_STATUS_CONFIG["DELIVERY_STATUS_CONFIG"]["status"]
        if s["code"] == "reexport"
    )
    CANCELLED = next(
        s["code"]
        for s in DELIVERY_STATUS_CONFIG["DELIVERY_STATUS_CONFIG"]["status"]
        if s["code"] == "cancelled"
    )


class StatusGroupCode(str, Enum):
    """Коды групп статусов."""

    # Получаем коды групп из конфигурации
    ORDER = "ORDER_STATUS_CONFIG"
    DELIVERY = "DELIVERY_STATUS_CONFIG"
    PACKAGE = "PACKAGE_STATUS_CONFIG"


# Получаем переходы из конфигурации
ORDER_STATUS_TRANSITIONS = ORDER_STATUS_CONFIG["ORDER_STATUS_CONFIG"][
    "allowed_status_transitions"
]
DELIVERY_STATUS_TRANSITIONS = DELIVERY_STATUS_CONFIG["DELIVERY_STATUS_CONFIG"][
    "allowed_status_transitions"
]
