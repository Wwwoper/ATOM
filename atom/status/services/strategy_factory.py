"""Стратегии для работы со статусами."""

from django.apps import apps

from .constants import get_status_codes


class OrderStatusStrategyFactory:
    """Фабрика для создания стратегий статусов заказов."""

    @classmethod
    def _get_strategies(cls):
        """Получить словарь стратегий с кодами статусов."""
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
        """Получить стратегию по статусу заказа."""
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
        """Получить словарь стратегий с кодами статусов."""
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
        """Получить стратегию по статусу доставки."""
        status_code = status.code if hasattr(status, "code") else status
        strategy_class = cls._get_strategies().get(status_code)
        if not strategy_class:
            raise ValueError(
                f"Стратегия для статуса {status} (код: {status_code}) не найдена"
            )
        return strategy_class()
