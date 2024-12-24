"""Сервис для обработки заказов."""

from status.services.strategy_factory import OrderStatusStrategyFactory


class OrderProcessor:
    """Процессор для обработки заказов."""

    def __init__(self):
        """Инициализация сервиса."""
        self.strategy_factory = OrderStatusStrategyFactory

    def execute_status_strategy(self, order) -> None:
        """
        Выполнить стратегию обработки для текущего статуса заказа.

        Args:
            order: Заказ для обработки
        """
        strategy = self.strategy_factory.get_strategy(order.status)
        strategy.handle_order_status(order)
