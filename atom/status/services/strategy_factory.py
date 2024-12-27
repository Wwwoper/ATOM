"""
Фабрики для создания стратегий обработки статусов.

Этот модуль реализует паттерн "Фабричный метод" для создания стратегий обработки
различных типов статусов (заказы, доставки). Обеспечивает выбор правильной стратегии
в зависимости от текущего статуса объекта.

Основные компоненты:
    - OrderStatusStrategyFactory: Фабрика стратегий для заказов
    - DeliveryStatusStrategyFactory: Фабрика стратегий для доставок
    - get_strategy: Метод получения конкретной стратегии
    - _get_strategies: Метод получения словаря доступных стратегий

Процесс создания стратегии:
    1. Определение типа объекта (заказ/доставка)
    2. Получение кода текущего статуса
    3. Поиск соответствующей стратегии в словаре стратегий
    4. Создание и возврат экземпляра стратегии

Доступные стратегии:
    Для заказов:
        - new: NewOrderStrategy
        - paid: PaidOrderStrategy
        - refunded: RefundedOrderStrategy

    Для доставок:
        - new: NewPackageDeliveryStrategy
        - paid: PaidPackageDeliveryStrategy
        - cancelled: CancelledPackageDeliveryStrategy
        - reexport: ReexportPackageDeliveryStrategy

Примеры использования:
    # Получение стратегии для заказа
    strategy = OrderStatusStrategyFactory.get_strategy(order.status)
    strategy.handle_order_status(order)

    # Получение стратегии для доставки
    strategy = DeliveryStatusStrategyFactory.get_strategy(delivery.status)
    strategy.process_delivery(delivery)

Примечания:
    - Каждая фабрика работает только со своим типом объектов
    - При отсутствии стратегии вызывается ValidationError
    - Стратегии создаются только при необходимости
    - Поддерживается добавление новых стратегий
"""

from django.apps import apps

from .constants import get_status_codes


class OrderStatusStrategyFactory:
    """Фабрика для создания стратегий статусов заказов."""

    @classmethod
    def _get_strategies(cls):
        """
        Получить словарь стратегий с кодами статусов.

        Returns:
            dict: Словарь {код_статуса: класс_стратегии}
        """
        Order = apps.get_model("order", "Order")
        status_codes = get_status_codes(Order)
        from order.services.order_strategies import (
            NewOrderStrategy,
            PaidOrderStrategy,
            RefundedOrderStrategy,
        )

        return {
            status_codes["new"]: NewOrderStrategy,
            status_codes["paid"]: PaidOrderStrategy,
            status_codes["refunded"]: RefundedOrderStrategy,
        }

    @classmethod
    def get_strategy(cls, status):
        """
        Получить стратегию по статусу заказа.

        Args:
            status: Статус заказа или его код

        Returns:
            BaseOrderStrategy: Экземпляр стратегии для обработки статуса

        Raises:
            ValidationError: Если стратегия для статуса не найдена
        """
        status_code = status.code if hasattr(status, "code") else status
        strategy_class = cls._get_strategies().get(status_code)
        if not strategy_class:
            raise ValueError(
                f"Стратегия для статуса {status} (код: {status_code}) не найдена"
            )
        return strategy_class()


class DeliveryStatusStrategyFactory:
    """Фабрика для создания стратегий статусов доставки."""

    @classmethod
    def _get_strategies(cls):
        """
        Получить словарь стратегий с кодами статусов.

        Returns:
            dict: Словарь {код_статуса: класс_стратегии}
        """
        PackageDelivery = apps.get_model("package", "PackageDelivery")
        status_codes = get_status_codes(PackageDelivery)
        from package.services.delivery_strategies import (
            CancelledPackageDeliveryStrategy,
            NewPackageDeliveryStrategy,
            PaidPackageDeliveryStrategy,
            ReexportPackageDeliveryStrategy,
        )

        return {
            status_codes["new"]: NewPackageDeliveryStrategy,
            status_codes["paid"]: PaidPackageDeliveryStrategy,
            status_codes["cancelled"]: CancelledPackageDeliveryStrategy,
            status_codes["reexport"]: ReexportPackageDeliveryStrategy,
        }

    @classmethod
    def get_strategy(cls, status):
        """
        Получить стратегию по статусу доставки.

        Args:
            status: Статус доставки или его код

        Returns:
            PackageDeliveryStrategy: Экземпляр стратегии для обработки статуса

        Raises:
            ValidationError: Если стратегия для статуса не найдена
        """
        status_code = status.code if hasattr(status, "code") else status
        strategy_class = cls._get_strategies().get(status_code)
        if not strategy_class:
            raise ValueError(
                f"Стратегия для статуса {status} (код: {status_code}) не найдена"
            )
        return strategy_class()
