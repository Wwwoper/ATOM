"""Модуль для обработки доставок."""

from status.services.strategy_factory import DeliveryStatusStrategyFactory


class DeliveryProcessor:
    """Процессор для обработки доставки."""

    def __init__(self):
        """Инициализация сервиса."""
        self.strategy_factory = DeliveryStatusStrategyFactory

    def execute_status_strategy(self, delivery) -> None:
        """
        Выполнить стратегию обработки для текущего статуса доставки.

        Args:
            delivery: Доставка для обработки
        """
        strategy = self.strategy_factory.get_strategy(delivery.status)
        strategy.process_delivery(delivery)
